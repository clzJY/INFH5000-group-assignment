"""RPP-inspired and DWA-style adaptations, not official ROS/Nav2 reproductions.

All methods share route/state inputs, native footprint geometry and actuator
limits. Forecast-static is an ablation of forecast using zero pedestrian velocity.
"""
import math
import numpy as np
from .geometry import gaps,reachable_bodies
from .tracking import Tracker

METHODS=('pp','rpp','distance','forecast_static','forecast','dwa')


class Controller:
    def __init__(self,route,config,length=1.5,width=1.,wheelbase=2.81,max_steer=math.pi/3):
        self.config=config;self.length=length;self.width=width
        self.tracker=Tracker(route,config['tracking'],wheelbase,max_steer)
        self.last_steering=0.;self.waiting=False;self.clear_elapsed=0.

    def _roll(self,position,heading,speed,targets,steers,horizon,follow):
        c=self.config['prediction']
        return self.tracker.predict(position,heading,speed,targets,steers,horizon,c['dt_s'],c['accel_m_s2'],c['brake_m_s2'],follow)

    def _risks(self,position,speed,poses,times,people,statics,moving):
        c=self.config['prediction'];horizon=float(times[-1])
        people=reachable_bodies(position,max(speed,self.config['tracking']['max_speed_m_s']),horizon,c['accel_m_s2'],self.length,self.width,people,c['buffer_m'])
        statics=reachable_bodies(position,max(speed,self.config['tracking']['max_speed_m_s']),horizon,c['accel_m_s2'],self.length,self.width,statics,c['buffer_m'])
        gp=gaps(poses,self.length,self.width,people,times,moving)
        gs=gaps(poses,self.length,self.width,statics,times,False)
        pmin=np.min(gp,axis=(1,2)) if gp.shape[-1] else np.full(len(poses),np.inf)
        smin=np.min(gs,axis=(1,2)) if gs.shape[-1] else np.full(len(poses),np.inf)
        exposure=np.sum(np.any(gp<c['soft_clearance_m'],axis=2),axis=1)*c['dt_s'] if gp.shape[-1] else np.zeros(len(poses))
        return pmin,smin,exposure

    def update(self,method,ego,people,statics,dt):
        if method not in METHODS:raise ValueError(method)
        c=self.config;pred=c['prediction']
        position=np.asarray(ego['position'],dtype=float);heading=ego['heading'];speed=ego['speed']
        route=self.tracker.command(position,heading,speed)
        max_delta=c['dwa']['steering_rate_per_s']*dt
        steering=float(np.clip(route['steering'],self.last_steering-max_delta,self.last_steering+max_delta))
        cap=route['cruise_speed_m_s'] if method=='pp' else route['regulated_speed_m_s']
        p0=gaps(np.array([[[*position,heading]]]),self.length,self.width,people,[0.],False)
        s0=gaps(np.array([[[*position,heading]]]),self.length,self.width,statics,[0.],False)
        current_p=float(np.min(p0)) if p0.size else math.inf
        current_s=float(np.min(s0)) if s0.size else math.inf
        candidates=[];reason='path_tracking';no_safe=False;escape=False

        if method=='distance':
            stop=pred['buffer_m'];slow=c['distance']['slow_gap_m']
            cap*=float(np.clip((current_p-stop)/(slow-stop),0,1));reason='current_distance'
        elif method=='rpp':
            near=min(current_p,current_s);prox=c['rpp']['proximity_distance_m']
            cap=max(min(cap,c['rpp']['minimum_progress_speed_m_s']),cap*min(1.,max(0.,near)/prox))
            horizon=min(c['rpp']['ttc_s'],max(c['tracking']['lookahead_m'],speed*c['tracking']['lookahead_time_s'])/max(cap,.1))
            poses,times=self._roll(position,heading,speed,[cap],[steering],horizon,False)
            pmin,smin,exposure=self._risks(position,speed,poses,times,people,statics,False)
            candidates=[dict(speed=cap,steering=steering,ped_gap=float(pmin[0]) if math.isfinite(pmin[0]) else None)]
            if pmin[0]<pred['buffer_m']:cap=0.;reason='rpp_projected_collision'
            else:reason='rpp_regulation'
        elif method in ('forecast','forecast_static'):
            targets=np.array(sorted(set(min(cap,v) for v in pred['candidate_speeds_m_s']),reverse=True))
            poses,times=self._roll(position,heading,speed,targets,np.full(len(targets),steering),pred['horizon_s'],True)
            pmin,smin,exposure=self._risks(position,speed,poses,times,people,statics,method=='forecast')
            feasible=(pmin>=pred['buffer_m']) & (smin>=c['static_guard']['buffer_m'])
            for v,g,s,e in zip(targets,pmin,smin,exposure):
                candidates.append(dict(speed=float(v),ped_gap=float(g) if math.isfinite(g) else None,
                    static_gap=float(s) if math.isfinite(s) else None,near_time_s=float(e)))
            if np.any(feasible):index=int(np.flatnonzero(feasible)[0]);cap=float(targets[index])
            else:
                no_safe=True;cap=0.;stop=int(np.argmin(targets));eligible=smin>=c['static_guard']['buffer_m']
                score=np.where(eligible,pmin,-np.inf);best=int(np.argmax(score))
                if pmin[stop]<0 and score[best]>pmin[stop]+pred['escape_improvement_m']:
                    cap=float(targets[best]);escape=cap>0
            reason='least_predicted_overlap' if escape else 'route_forecast'
            if cap<=1e-9:self.waiting=True;self.clear_elapsed=0.
            elif self.waiting and not escape:
                self.clear_elapsed+=dt
                if self.clear_elapsed+1e-9>=pred['release_hold_s']:self.waiting=False
                else:cap=0.
            else:self.waiting=False
        elif method=='dwa':
            d=c['dwa'];window=d['command_window_s']
            lo=max(0.,speed-pred['brake_m_s2']*window);hi=min(cap,speed+pred['accel_m_s2']*window)
            if lo>hi:lo=hi
            speeds=sorted(set([lo,hi,(lo+hi)/2,*[v for v in pred['candidate_speeds_m_s'] if lo<=v<=hi]]))
            angles=sorted(set(float(np.clip(steering+delta,max(-1,self.last_steering-max_delta),min(1,self.last_steering+max_delta))) for delta in d['steering_offsets']))
            pairs=[(v,a) for v in speeds for a in angles]
            targets=np.array([p[0] for p in pairs]);steers=np.array([p[1] for p in pairs])
            poses,times=self._roll(position,heading,speed,targets,steers,d['horizon_s'],False)
            pmin,smin,exposure=self._risks(position,speed,poses,times,people,statics,True)
            feasible=(pmin>=pred['buffer_m'])&(smin>=c['static_guard']['buffer_m'])
            window_route=self.tracker.route[max(0,self.tracker.index-10):min(len(self.tracker.route),self.tracker.index+151)]
            terminal=poses[:,-1,:2]
            cross=np.min(np.linalg.norm(terminal[:,None,:]-window_route[None,:,:],axis=2),axis=1)
            goal=np.linalg.norm(terminal-self.tracker.route[-1],axis=1)
            progress=route['goal_distance_m']-goal
            clearance=np.minimum(pmin,3.)
            scores=d['progress_weight']*progress-d['route_weight']*cross+d['clearance_weight']*clearance-d['control_change_weight']*np.abs(steers-self.last_steering)
            scores=np.where(feasible,scores,-np.inf)
            for (v,a),g,s,score in zip(pairs,pmin,smin,scores):
                candidates.append(dict(speed=v,steering=a,ped_gap=float(g) if math.isfinite(g) else None,
                    static_gap=float(s) if math.isfinite(s) else None,score=float(score) if math.isfinite(score) else None))
            if np.any(feasible):index=int(np.argmax(scores));cap=float(targets[index]);steering=float(steers[index])
            else:cap=0.;no_safe=True
            reason='dwa_velocity_search'

        # Identical final static-body guard for every method, including PP.
        # It uses the selected immediate steering command, not future pedestrians.
        static_block=False
        if c['static_guard']['enabled'] and len(statics):
            poses,times=self._roll(position,heading,speed,[cap],[steering],c['static_guard']['horizon_s'],False)
            _,smin,_=self._risks(position,speed,poses,times,[],statics,False)
            if smin[0]<c['static_guard']['buffer_m']:
                cap=0.;static_block=True;reason='common_static_guard'
        self.last_steering=steering
        return dict(state='WAIT' if cap<=1e-9 else 'SLOW',speed_cap_m_s=cap,steering=steering,
                    reason=reason,current_pedestrian_box_gap_m=current_p if math.isfinite(current_p) else None,
                    current_static_box_gap_m=current_s if math.isfinite(current_s) else None,
                    no_buffer_feasible=no_safe,static_guard_active=static_block,route=route,candidates=candidates)
