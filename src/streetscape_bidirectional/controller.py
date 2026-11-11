"""Steering-conditioned, time-aligned footprint speed selection.

Kinematic predictions are a heuristic, not a collision-free guarantee. Dimensions
come from native Bullet boxes, not visual meshes or the pedestrian RADIUS proxy.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Body:
    position: tuple
    heading: float
    length: float
    width: float
    velocity: tuple = (0., 0.)


def box_separation(a, b):
    """Maximum signed SAT axis gap: conservative lower bound on box distance."""
    axes = [(math.cos(x), math.sin(x)) for x in
            (a.heading, a.heading + math.pi/2, b.heading, b.heading + math.pi/2)]
    delta = tuple(y-x for x, y in zip(a.position, b.position))
    def radius(body, axis):
        c, s = math.cos(body.heading), math.sin(body.heading)
        return (body.length/2 * abs(axis[0]*c + axis[1]*s) +
                body.width/2 * abs(-axis[0]*s + axis[1]*c))
    return max(abs(sum(x*y for x, y in zip(delta, axis))) - radius(a, axis) - radius(b, axis)
               for axis in axes)


def predict_path(body, speed, target, curvature, horizon, step, accel, brake):
    """Midpoint bicycle integration with bounded acceleration and braking."""
    x, y = body.position
    theta = body.heading
    result = [(0., Body((x,y), theta, body.length, body.width))]
    for i in range(round(horizon/step)):
        rate = brake if speed*target < 0 or abs(speed) > abs(target) else accel
        new_speed = max(target, speed-rate*step) if speed > target else min(target, speed+rate*step)
        ds = (speed+new_speed)*step/2
        mid = theta + curvature*ds/2
        x += ds*math.cos(mid); y += ds*math.sin(mid)
        theta += curvature*ds
        speed = new_speed
        result.append(((i+1)*step, Body((x,y),theta,body.length,body.width)))
    return result


class IntentGovernor:
    def __init__(self, settings, pedestrian_aware):
        self.c = settings
        self.pedestrian_aware = pedestrian_aware
        self.previous_cap = settings['cruise_speed_m_s']
        self.clear_elapsed = 0.
        self.waiting = False

    def update(self, ego, people, raw, speed, curvature, dt):
        c = self.c
        # The same navigation governor is used in the ablation and full method.
        cruise = min(c['cruise_speed_m_s'], math.sqrt(c['lateral_accel_m_s2']/max(abs(curvature),1e-6)))
        cruise = max(c['min_turn_speed_m_s'], cruise)
        chosen = cruise
        risks = []
        current = min((box_separation(ego, p) for p in people), default=math.inf)
        if self.pedestrian_aware and people:
            for target in sorted(set([cruise, *[min(cruise,v) for v in c['candidate_speeds_m_s']]]), reverse=True):
                # Respect PPO's braking intention; do not hallucinate forward
                # motion at 2 m/s when the requested command is to brake.
                intended = math.copysign(target, raw[1]) if abs(raw[1]) > .01 else 0.
                path = predict_path(ego, speed, intended, curvature, c['horizon_s'], c['prediction_step_s'],
                                    c['prediction_accel_m_s2'], c['prediction_brake_m_s2'])
                risk = math.inf
                for t, future in path:
                    for p in people:
                        projected = Body(tuple(x+t*v for x,v in zip(p.position,p.velocity)),p.heading,p.length,p.width)
                        risk = min(risk, box_separation(future,projected))
                risks.append({'target_m_s':target,'min_box_gap_m':risk})
                if risk >= c['buffer_m']:
                    chosen = target
                    break
            else:
                chosen = 0.
            if chosen <= 1e-9:
                self.waiting = True; self.clear_elapsed = 0.
            elif self.waiting:
                self.clear_elapsed += dt
                if self.clear_elapsed + 1e-9 >= c['release_hold_s']:
                    self.waiting = False
                else:
                    chosen = 0.
            chosen = min(chosen, self.previous_cap + c['recovery_accel_m_s2']*dt)
        self.previous_cap = chosen
        return dict(state='WAIT' if chosen <= 1e-9 else 'SLOW', speed_cap_m_s=chosen,
                    clearance_m=current if math.isfinite(current) else None,
                    risk_clearance_m=risks[0]['min_box_gap_m'] if risks else None,
                    reason='footprint_intent' if chosen < cruise-1e-6 else 'navigation_governor',
                    cruise_cap_m_s=cruise, curvature_m_inv=curvature, candidate_risks=risks)
