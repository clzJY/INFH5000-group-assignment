"""Native-state local trajectory library and explicit walkable-footprint checks."""
import math
import numpy as np
import shapely
from shapely.geometry import Point
from streetscape_baselines.geometry import gaps, reachable_bodies
from streetscape_baselines.tracking import Tracker

LETTERS='ABCDEF'

class LocalPlanner:
    def __init__(self,route,config,region,geometry):
        self.route=np.asarray(route);self.config=config;self.region=region
        shapely.prepare(self.region)
        self.g=geometry;self.tracker=Tracker(route,config['tracking'],geometry['wheelbase'],geometry['max_steer'])
        self.last_steering=0.;self.last_id=2;self.rng=np.random.default_rng(138)
        self.u=None

    def mppi_roll(self,ego,cap,n=96,dt=.15,horizon=3.):
        count=round(horizon/dt)
        nominal=self.tracker.command(np.asarray(ego['position']),ego['heading'],ego['speed'])['steering']
        if self.u is None:self.u=np.tile([cap,nominal],(count,1))
        else:self.u=np.r_[self.u[1:],self.u[-1:]]
        noise=self.rng.normal(size=(n,count,2))*np.array([.5,.22])
        # Temporally smooth perturbations; one stopping sequence is always included.
        for t in range(1,count):noise[:,t]=.7*noise[:,t-1]+.3*noise[:,t]
        controls=self.u[None]+noise;controls[:,:,0]=np.clip(controls[:,:,0],0,cap);controls[:,:,1]=np.clip(controls[:,:,1],-1,1)
        controls[0]=self.u;controls[-1,:,0]=0;controls[-1,:,1]=self.last_steering
        def roll(u):
            m=len(u);x=np.full(m,ego['position'][0],dtype=float);y=np.full(m,ego['position'][1],dtype=float);theta=np.full(m,ego['heading']);v=np.full(m,ego['speed']);st=np.full(m,self.last_steering);poses=[np.c_[x,y,theta]]
            for t in range(count):
                nv=np.where(v>u[:,t,0],np.maximum(u[:,t,0],v-2*dt),np.minimum(u[:,t,0],v+1.5*dt))
                st+=np.clip(u[:,t,1]-st,-1.5*dt,1.5*dt);ds=(v+nv)*dt/2;curv=np.tan(st*self.g['max_steer'])/self.g['wheelbase']
                x+=ds*np.cos(theta+curv*ds/2);y+=ds*np.sin(theta+curv*ds/2);theta+=curv*ds;v=nv;poses.append(np.c_[x,y,theta])
            return np.stack(poses,axis=1)
        return roll(controls),np.arange(count+1)*dt,controls,roll

    def simulate(self,ego,offsets,speeds,dt=.15,horizon=3.):
        n=len(offsets);count=round(horizon/dt)
        x=np.full(n,ego['position'][0],dtype=float);y=np.full(n,ego['position'][1],dtype=float);theta=np.full(n,ego['heading']);v=np.full(n,ego['speed']);steer=np.full(n,self.last_steering)
        s=np.full(n,self.tracker.arc[self.tracker.index]);poses=[np.c_[x,y,theta]];first=None
        for i in range(count):
            look=np.maximum(2.,v*.8)
            idx=np.clip(np.searchsorted(self.tracker.arc,s+look),1,len(self.route)-2)
            tangent=self.route[idx+1]-self.route[idx-1];tangent/=np.maximum(1e-6,np.linalg.norm(tangent,axis=1))[:,None]
            # Smooth lateral offset: select a nearby lane and return through receding replanning.
            aim=self.route[idx]+np.c_[-tangent[:,1],tangent[:,0]]*np.asarray(offsets)[:,None]
            dx=aim[:,0]-x;dy=aim[:,1]-y
            alpha=np.arctan2(np.sin(np.arctan2(dy,dx)-theta),np.cos(np.arctan2(dy,dx)-theta))
            desired=np.clip(np.arctan2(2*self.g['wheelbase']*np.sin(alpha),np.maximum(.2,np.hypot(dx,dy)))/self.g['max_steer'],-1,1)
            steer+=np.clip(desired-steer,-1.5*dt,1.5*dt)
            if first is None:first=steer.copy()
            newv=np.where(v>speeds,np.maximum(speeds,v-2*dt),np.minimum(speeds,v+1.5*dt));ds=(v+newv)*dt/2
            curv=np.tan(steer*self.g['max_steer'])/self.g['wheelbase']
            x+=ds*np.cos(theta+curv*ds/2);y+=ds*np.sin(theta+curv*ds/2);theta+=curv*ds
            s=np.minimum(self.tracker.arc[-1],s+np.maximum(0,ds*np.cos(alpha)));v=newv
            poses.append(np.c_[x,y,theta])
        return np.stack(poses,axis=1),np.arange(count+1)*dt,first

    def region_valid(self,poses):
        # Every sampled oriented footprint must lie within the sidewalk/crosswalk union.
        pts=[]
        for a,b in ((-1,-1),(-1,1),(1,1),(1,-1),(-1,-1)):
            xx=a*self.g['length']/2;yy=b*self.g['width']/2
            pts.append(np.stack([poses[...,0]+xx*np.cos(poses[...,2])-yy*np.sin(poses[...,2]),poses[...,1]+xx*np.sin(poses[...,2])+yy*np.cos(poses[...,2])],axis=-1))
        points=np.stack(pts,axis=2)
        footprints=shapely.polygons(points.reshape(-1,5,2))
        inside=shapely.covers(self.region,footprints).reshape(poses.shape[:2])
        valid=np.all(inside,axis=1)
        # A native transient may place the current footprint partly outside a boundary.
        # Recovery must finish inside and may not increase that existing violation.
        if not np.all(inside[:,0]):
            outside=shapely.area(shapely.difference(footprints,self.region)).reshape(poses.shape[:2])
            recovery=(outside[:,0]>0)&(outside[:,-1]<1e-6)&(outside.max(axis=1)<=outside[:,0]+.005)
            valid|=recovery
        return valid

    def evaluate(self,ego,people,statics,method='lattice'):
        cmd=self.tracker.command(np.asarray(ego['position']),ego['heading'],ego['speed'])
        cap=min(2.,cmd['regulated_speed_m_s'])
        # Five spatial options plus a physical stop. Every method uses the same caps.
        offsets=np.array([-1.5,-.75,0,.75,1.5,0.]);speeds=np.array([cap]*5+[0.])
        controls=None
        if method=='mppi':
            poses,times,controls,roll=self.mppi_roll(ego,cap)
            offsets=np.zeros(len(poses));speeds=controls[:,0,0];first=controls[:,0,1]
        else:poses,times,first=self.simulate(ego,offsets,speeds)
        nearpeople=reachable_bodies(ego['position'],3.,3.,1.5,self.g['length'],self.g['width'],people,.25)
        nearstatics=reachable_bodies(ego['position'],3.,3.,1.5,self.g['length'],self.g['width'],statics,.25)
        gp=gaps(poses,self.g['length'],self.g['width'],nearpeople,times,True)
        gs=gaps(poses,self.g['length'],self.g['width'],nearstatics,times,False)
        pg=gp.min(axis=(1,2)) if gp.size else np.full(len(poses),9.)
        sg=gs.min(axis=(1,2)) if gs.size else np.full(len(poses),9.)
        legal=self.region_valid(poses)
        feasible=(pg>=.25)&(sg>=.1)&legal
        begin=max(0,self.tracker.index-5);nearroute=self.route[begin:self.tracker.index+151]
        distances=np.linalg.norm(poses[:,-1,None,:2]-nearroute[None,:,:],axis=-1)
        nearest=distances.argmin(axis=1);cross=distances[np.arange(len(poses)),nearest]
        progress=self.tracker.arc[begin+nearest]-self.tracker.arc[self.tracker.index]
        score=2*progress-.8*cross-1.5*np.abs(offsets)+.25*np.minimum(pg,2.)+.15*np.minimum(sg,2.)
        score-=.15*(np.sign(offsets)!=np.sign(offsets[min(self.last_id,len(offsets)-1)]))
        score[-1]=-.5
        index=int(np.argmax(np.where(feasible,score,-1e9))) if np.any(feasible) else len(offsets)-1
        if controls is not None:
            if np.any(feasible):
                weight=np.exp(np.clip((score-np.max(score[feasible]))/.7,-50,0))*feasible;weight/=weight.sum()
                self.u=np.einsum('n,ntd->td',weight,controls)
            else:self.u=controls[-1]
            # Validate the weighted MPPI sequence before executing it.
            avg=roll(self.u[None]);ap=gaps(avg,self.g['length'],self.g['width'],nearpeople,times,True);ast=gaps(avg,self.g['length'],self.g['width'],nearstatics,times,False)
            if self.region_valid(avg)[0] and (not ap.size or ap.min()>=.25) and (not ast.size or ast.min()>=.1):
                first[index]=self.u[0,1];speeds[index]=self.u[0,0]
            else:self.u=controls[index].copy()
        self.last_id=index
        return dict(poses=poses,times=times,first=first,offsets=offsets,speeds=speeds,feasible=feasible,score=score,
                    ped_gap=pg,static_gap=sg,legal=legal,index=index,route=cmd)

    def decision(self,data,index=None,dt=.1):
        i=data['index'] if index is None else index
        if not data['feasible'][i]:i=data['index']
        target=float(data['first'][i]);steering=float(np.clip(target,self.last_steering-1.5*dt,self.last_steering+1.5*dt))
        self.last_steering=steering;self.last_id=i
        cap=float(data['speeds'][i]) if data['feasible'][i] else 0.
        return dict(state='WAIT' if cap==0 else 'SLOW',speed_cap_m_s=cap,steering=steering,reason='walkable_local_plan',selected=i,
                    feasible=[bool(x) for x in data['feasible']],scores=data['score'].tolist(),
                    ped_gaps=data['ped_gap'].tolist(),static_gaps=data['static_gap'].tolist())
