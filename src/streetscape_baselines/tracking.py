"""Shared pure-pursuit tracker; exact same route information for every method."""
import math
import numpy as np


class Tracker:
    def __init__(self,route,settings,wheelbase,max_steer):
        self.route=np.asarray(route,dtype=float)
        self.arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(self.route,axis=0),axis=1))]
        self.c=settings;self.wheelbase=wheelbase;self.max_steer=max_steer;self.index=0

    def point(self,s):
        i=int(np.searchsorted(self.arc,min(s,self.arc[-1]),side='left'))
        return self.route[min(i,len(self.route)-1)]

    def command(self,position,heading,speed):
        begin=max(0,self.index-10);end=min(len(self.route),self.index+151)
        nearest=begin+int(np.argmin(np.linalg.norm(self.route[begin:end]-position,axis=1)))
        self.index=max(self.index,nearest)
        lookahead=max(self.c['lookahead_m'],speed*self.c['lookahead_time_s'])
        target=self.point(self.arc[self.index]+lookahead)
        delta=target-position;distance=max(.1,float(np.linalg.norm(delta)))
        alpha=math.atan2(math.sin(math.atan2(delta[1],delta[0])-heading),math.cos(math.atan2(delta[1],delta[0])-heading))
        steer=float(np.clip(self.c['steering_gain']*math.atan(2*self.wheelbase*math.sin(alpha)/distance)/self.max_steer,-1,1))
        curvature=math.tan(steer*self.max_steer)/self.wheelbase
        remaining=float(self.arc[-1]-self.arc[self.index]);goal_distance=float(np.linalg.norm(position-self.route[-1]))
        approach=min(1.,max(self.c['min_speed_m_s']/self.c['max_speed_m_s'],max(remaining,goal_distance)/self.c['approach_distance_m']))
        cruise=self.c['max_speed_m_s']*approach
        regulated=max(self.c['min_speed_m_s'],min(cruise,cruise/max(1.,abs(curvature)*self.c['curvature_min_radius_m'])))
        return dict(steering=steer,curvature=curvature,cruise_speed_m_s=cruise,regulated_speed_m_s=regulated,
            route_index=self.index,remaining_m=remaining,goal_distance_m=goal_distance,
            cross_track_m=float(np.linalg.norm(position-self.route[self.index])),target=[float(v) for v in target])

    def predict(self,position,heading,speed,targets,steerings,horizon,dt,accel,brake,follow_route):
        """Batched bounded bicycle rollouts; optionally update pursuit each sample."""
        targets=np.asarray(targets,dtype=float);steerings=np.asarray(steerings,dtype=float)
        n=len(targets);count=round(horizon/dt)+1;poses=np.empty((n,count,3))
        x=np.full(n,position[0]);y=np.full(n,position[1]);theta=np.full(n,heading);v=np.full(n,speed)
        s=np.full(n,self.arc[self.index]);poses[:,0,:]=np.c_[x,y,theta]
        for t in range(1,count):
            newv=np.where(v>targets,np.maximum(targets,v-brake*dt),np.minimum(targets,v+accel*dt));ds=(v+newv)*dt/2
            if follow_route:
                look=np.maximum(self.c['lookahead_m'],v*self.c['lookahead_time_s'])
                indices=np.minimum(len(self.route)-1,np.searchsorted(self.arc,np.minimum(self.arc[-1],s+look)))
                aim=self.route[indices];dx=aim[:,0]-x;dy=aim[:,1]-y
                alpha=np.arctan2(np.sin(np.arctan2(dy,dx)-theta),np.cos(np.arctan2(dy,dx)-theta))
                angles=np.clip(self.c['steering_gain']*np.arctan2(2*self.wheelbase*np.sin(alpha),np.maximum(.1,np.hypot(dx,dy))),-self.max_steer,self.max_steer)
                s=np.minimum(self.arc[-1],s+np.maximum(0,ds*np.cos(alpha)))
            else:angles=steerings*self.max_steer
            curvature=np.tan(angles)/self.wheelbase
            x+=ds*np.cos(theta+curvature*ds/2);y+=ds*np.sin(theta+curvature*ds/2);theta+=curvature*ds
            poses[:,t,:]=np.c_[x,y,theta];v=newv
        return poses,np.arange(count)*dt
