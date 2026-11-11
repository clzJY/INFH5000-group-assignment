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
    """Exact Euclidean gap for disjoint boxes; signed SAT depth when overlapping."""
    axes = [(math.cos(x), math.sin(x)) for x in
            (a.heading, a.heading + math.pi/2, b.heading, b.heading + math.pi/2)]
    delta = tuple(y-x for x, y in zip(a.position, b.position))
    def radius(body, axis):
        c, s = math.cos(body.heading), math.sin(body.heading)
        return (body.length/2 * abs(axis[0]*c + axis[1]*s) +
                body.width/2 * abs(-axis[0]*s + axis[1]*c))
    sat = max(abs(sum(x*y for x, y in zip(delta, axis))) - radius(a, axis) - radius(b, axis)
              for axis in axes)
    if sat <= 0:
        return sat
    def corners(body):
        c,s=math.cos(body.heading),math.sin(body.heading)
        return [(body.position[0]+u*c-v*s,body.position[1]+u*s+v*c)
                for u in (-body.length/2,body.length/2) for v in (-body.width/2,body.width/2)]
    def point_distance(point,body):
        dx,dy=point[0]-body.position[0],point[1]-body.position[1]
        c,s=math.cos(body.heading),math.sin(body.heading)
        return math.hypot(max(0.,abs(dx*c+dy*s)-body.length/2),
                          max(0.,abs(-dx*s+dy*c)-body.width/2))
    return min(*[point_distance(p,b) for p in corners(a)],*[point_distance(p,a) for p in corners(b)])


def predict_path(body, speed, target, curvature, horizon, step, accel, brake):
    """Midpoint bicycle integration with bounded acceleration and braking."""
    x, y = body.position
    theta = body.heading
    result = [(0., Body((x,y), theta, body.length, body.width))]
    for i in range(round(horizon/step)):
        new_speed = max(target, speed-brake*step) if speed > target else min(target, speed+accel*step)
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

    def update(self, ego, people, raw, speed, curvature, dt, path_predictor=None):
        c = self.c
        # The same navigation governor is used in the ablation and full method.
        cruise = min(c['cruise_speed_m_s'], math.sqrt(c['lateral_accel_m_s2']/max(abs(curvature),1e-6)))
        cruise = max(c['min_turn_speed_m_s'], cruise)
        chosen = cruise
        risks = []
        escape = False
        current = min((box_separation(ego, p) for p in people), default=math.inf)
        # Only discard actors beyond a conservative reachable-distance bound.
        people = [p for p in people if math.dist(ego.position,p.position) <=
                  c['horizon_s']*(max(speed,cruise)+c['prediction_accel_m_s2']*c['horizon_s']+math.hypot(*p.velocity))+
                  math.hypot(ego.length,ego.width)/2+math.hypot(p.length,p.width)/2+c['buffer_m']]
        if self.pedestrian_aware and people:
            for target in sorted(set([cruise, *[min(cruise,v) for v in c['candidate_speeds_m_s']]]), reverse=True):
                # Respect PPO's braking intention; do not hallucinate forward
                # motion at 2 m/s when the requested command is to brake.
                intended = target if raw[1] > 0 else 0.
                path = (path_predictor(ego, speed, intended, c) if path_predictor else
                        predict_path(ego, speed, intended, curvature, c['horizon_s'], c['prediction_step_s'],
                                     c['prediction_accel_m_s2'], c['prediction_brake_m_s2']))
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
                # Parking can itself put the robot in an approaching person's
                # path. If no candidate clears the buffer, compare all predicted
                # outcomes rather than treating a stop as automatically safe.
                stopped = next(r for r in risks if r['target_m_s'] == 0.)
                best = max(risks, key=lambda r:(r['min_box_gap_m'],r['target_m_s']))
                if stopped['min_box_gap_m'] < 0 and best['min_box_gap_m'] > stopped['min_box_gap_m'] + c['escape_improvement_m']:
                    chosen = best['target_m_s']
                    escape = chosen > 0
            if chosen <= 1e-9:
                self.waiting = True; self.clear_elapsed = 0.
            elif self.waiting and not escape:
                self.clear_elapsed += dt
                if self.clear_elapsed + 1e-9 >= c['release_hold_s']:
                    self.waiting = False
                else:
                    chosen = 0.
            else:
                self.waiting = False
            # Physical acceleration is bounded by the actuator and included in
            # prediction. An extra post-selection cap ramp would invalidate the
            # trajectory that was just checked, especially when clearing a crossing.
        self.previous_cap = chosen
        return dict(state='WAIT' if chosen <= 1e-9 else 'SLOW', speed_cap_m_s=chosen,
                    clearance_m=current if math.isfinite(current) else None,
                    risk_clearance_m=risks[0]['min_box_gap_m'] if risks else None,
                    reason='least_predicted_overlap' if escape else 'footprint_intent' if chosen < cruise-1e-6 else 'navigation_governor',
                    no_buffer_feasible=bool(risks and max(r['min_box_gap_m'] for r in risks)<c['buffer_m']),
                    cruise_cap_m_s=cruise, curvature_m_inv=curvature, candidate_risks=risks)
