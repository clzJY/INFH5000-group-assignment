#!/usr/bin/env python3
"""Native RGB repeat with optional physical stop and camera-only inspection pan."""
import argparse
import json
import math
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from streetscape_route import runtime


def main():
    p=argparse.ArgumentParser();p.add_argument('--method',required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--pedestrians',type=int,default=15);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mission',action='store_true');a=p.parse_args()
    if os.environ.get('PYTHONHASHSEED')!=str(a.seed):
        os.execve(sys.executable,[sys.executable,*sys.argv],dict(os.environ,PYTHONHASHSEED=str(a.seed),PYTHONDONTWRITEBYTECODE='1'))
    c=json.loads((ROOT/'configs/route_frozen_20261102.json').read_text())
    if a.mission:
        c['inspection_hold_s']=1.;c['inspection_max_s']=5.
        native=runtime._make_env
        def make(config,count,record):
            env=native(config,count,record)
            from metaurban.component.sensors.rgb_camera import RGBCamera
            original=RGBCamera.perceive;yaw=0
            def capture(camera,*args,**kwargs):
                nonlocal yaw
                agent=next(iter(camera.engine.agent_manager.active_agents.values()),None)
                if agent is not None:
                    distance=math.dist(agent.position[:2],agent.navigation.position_list[-1])
                    if distance<=config['goal_radius_m'] and getattr(agent,'_urban_yield_hold',False) and math.hypot(*agent.velocity)<.1:
                        yaw=min(90,yaw+30)
                if yaw and kwargs.get('new_parent_node') is not None:kwargs['hpr']=[yaw,-5,0]
                return original(camera,*args,**kwargs)
            RGBCamera.perceive=capture
            return env
        runtime._make_env=make
    result=runtime.run_episode(c,a.method,a.seed,a.pedestrians,a.output,True)
    print(json.dumps({k:v for k,v in result.items() if k not in ('planned_route','core_source_sha256')},indent=2))


if __name__=='__main__':main()
