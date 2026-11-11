"""Small route-consistency correction, using the simulator's supplied route.

This accesses the full planned polyline, an explicit privileged-state assumption.
The policy remains frozen. Corrections and their triggers are logged per step.
"""
import math
import bisect
from .controller import Body


class RouteGovernor:
    def __init__(self, route, config):
        self.route = route
        self.c = config
        self.index = 0
        self.lengths = [0.]
        for a,b in zip(route,route[1:]):
            self.lengths.append(self.lengths[-1]+math.dist(a,b))

    def action(self, position, heading, speed, raw, wheelbase, max_steer):
        # The route is densely sampled at approximately 0.1 m. Restrict the
        # nearest-point search to the local forward segment to avoid branch jumps.
        begin=max(0,self.index-10);end=min(len(self.route),self.index+101)
        nearest=min(range(begin,end),key=lambda i:math.dist(position,self.route[i]))
        self.index=max(self.index,nearest)
        lookahead=max(self.c['lookahead_m'],self.c['lookahead_time_s']*speed)
        target=self.index
        while target+1<len(self.route) and self.lengths[target]-self.lengths[self.index]<lookahead:
            target+=1
        delta=tuple(x-y for x,y in zip(self.route[target],position))
        distance=max(.1,math.hypot(*delta))
        angle=math.atan2(math.sin(math.atan2(delta[1],delta[0])-heading),math.cos(math.atan2(delta[1],delta[0])-heading))
        steering=max(-1.,min(1.,self.c['steering_gain']*math.atan(2*wheelbase*math.sin(angle)/distance)/max_steer))
        remaining=self.lengths[-1]-self.lengths[self.index]
        cross_track=math.dist(position,self.route[self.index])
        reasons=[]
        if abs(angle)>self.c['heading_error_rad']:reasons.append('heading_to_route')
        if abs(steering-raw[0])>self.c['steering_disagreement']:reasons.append('steering_disagreement')
        if cross_track>self.c['corridor_m']:reasons.append('route_corridor')
        if raw[1]<0 and remaining>self.c['negative_override_min_remaining_m']:reasons.append('brake_stall_risk')
        # Steering is corrected only while the gate is active. The shared speed
        # governor and (in the full method) pedestrian shield run afterwards.
        action=[steering,1.] if reasons else list(raw)
        return action,dict(active=bool(reasons),reasons=reasons,route_index=self.index,target_index=target,
                           remaining_m=remaining,cross_track_m=cross_track,heading_error_rad=angle,
                           proposed_steering=steering)

    def predict(self, body, speed, target_speed, settings, wheelbase, max_steer):
        """Recompute pursuit along the supplied route at each future sample.

        This replaces a fixed-heading/constant-curvature extrapolation. It does
        not read future pedestrian states or advance the real simulator.
        """
        x,y=body.position;theta=body.heading;s=self.lengths[self.index]
        dt=settings['prediction_step_s'];rows=[(0.,body)]
        for i in range(round(settings['horizon_s']/dt)):
            rate=settings['prediction_brake_m_s2'] if speed>target_speed else settings['prediction_accel_m_s2']
            v=max(target_speed,speed-rate*dt) if speed>target_speed else min(target_speed,speed+rate*dt)
            ds=(v+speed)*dt/2
            aim=min(self.lengths[-1],s+max(self.c['lookahead_m'],self.c['lookahead_time_s']*speed))
            k=min(len(self.route)-1,bisect.bisect_left(self.lengths,aim))
            dx,dy=self.route[k][0]-x,self.route[k][1]-y
            alpha=math.atan2(math.sin(math.atan2(dy,dx)-theta),math.cos(math.atan2(dy,dx)-theta))
            steering=max(-max_steer,min(max_steer,self.c['steering_gain']*math.atan(2*wheelbase*math.sin(alpha)/max(.1,math.hypot(dx,dy)))))
            curvature=math.tan(steering)/wheelbase
            x+=ds*math.cos(theta+curvature*ds/2);y+=ds*math.sin(theta+curvature*ds/2)
            theta+=curvature*ds;s=min(self.lengths[-1],s+max(0.,ds*math.cos(alpha)))
            speed=v
            rows.append(((i+1)*dt,Body((x,y),theta,body.length,body.width)))
        return rows
