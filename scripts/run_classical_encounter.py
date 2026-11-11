#!/usr/bin/env python3
"""Native 3D controlled pedestrian encounters; controller sees current states only.

One native pedestrian follows a prescribed kinematic path, analogous to native
preplanned position updates. The ego remains under Bullet wheel dynamics.
This diagnostic suite is reported separately from random 5/15-person streets.
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from streetscape_baselines import runtime


def install():
    original_make=runtime._make_env
    def make(config,count,record):
        if count!=1:raise ValueError('Controlled suite requires exactly one native pedestrian')
        env=original_make(config,count,record);original_reset=env.reset
        def reset(*args,**kwargs):
            observation,info=original_reset(*args,**kwargs)
            from metaurban.component.agents.pedestrian.base_pedestrian import BasePedestrian
            people=list(env.engine.get_objects(lambda obj:isinstance(obj,BasePedestrian)).values())
            assert len(people)==1
            person=people[0];recipe=config['encounter'];route=np.asarray(env.agent.navigation.position_list,dtype=float)
            arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(route,axis=0),axis=1))]
            distance=recipe.get('route_distance_m',12.)
            index=min(len(route)-2,int(np.searchsorted(arc,distance)))
            anchor=route[index];tangent=route[min(len(route)-1,index+5)]-route[max(0,index-5)]
            tangent=tangent/max(1e-9,np.linalg.norm(tangent));normal=np.array([-tangent[1],tangent[0]])
            kind=recipe['kind']
            if kind=='crossing':
                velocity=-normal*recipe.get('speed_m_s',1.2)
                initial=anchor-velocity*recipe.get('cross_time_s',4.6)
            elif kind=='receding':
                initial=route[0]+tangent*recipe.get('initial_ahead_m',2.5)
                velocity=tangent*recipe.get('speed_m_s',3.)
            elif kind=='approaching':
                initial=anchor+normal*recipe.get('lateral_m',.8)
                velocity=-tangent*recipe.get('speed_m_s',1.)
            elif kind=='stationary':initial=anchor.copy();velocity=np.zeros(2)
            else:raise ValueError(kind)
            heading=math.atan2(velocity[1],velocity[0]) if np.linalg.norm(velocity)>1e-6 else math.atan2(tangent[1],tangent[0])
            person.set_position(initial);person.set_heading_theta(heading)
            manager=env.engine.humanoid_manager;original_after=manager.after_step;ticks=0
            dt=float(env.config['physics_world_step_size'])*int(env.config['decision_repeat'])
            def after_step(*a,**kw):
                nonlocal ticks
                result=original_after(*a,**kw);ticks+=1
                person.set_position(initial+ticks*dt*velocity);person.set_heading_theta(heading)
                if person.render:person.set_anim_by_speed(float(np.linalg.norm(velocity)))
                return result
            manager.after_step=after_step
            Path('encounter_recipe.json').write_text(json.dumps(dict(kind=kind,initial_position=initial.tolist(),
                velocity=velocity.tolist(),heading=heading,anchor=anchor.tolist(),tangent=tangent.tolist(),
                dt_s=dt,rule='After native humanoid manager update, scripted pedestrian follows x0+t*v; ego motion is never overwritten.'),indent=2)+'\n')
            return observation,info
        env.reset=reset
        return env
    runtime._make_env=make


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--method',required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--pedestrians',type=int,default=1)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--record',action='store_true');a=p.parse_args()
    if os.environ.get('PYTHONHASHSEED')!=str(a.seed):
        os.execve(sys.executable,[sys.executable,*sys.argv],dict(os.environ,PYTHONHASHSEED=str(a.seed),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2'))
    install();result=runtime.run_episode(json.loads(a.config.read_text()),a.method,a.seed,a.pedestrians,a.output,a.record)
    print(json.dumps({k:v for k,v in result.items() if k not in ('planned_route','initial_static_bodies','core_source_sha256')},indent=2))
