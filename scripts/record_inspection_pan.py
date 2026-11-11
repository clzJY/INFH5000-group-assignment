#!/usr/bin/env python3
"""Record a forward view, then pan the camera after the robot has stopped."""
import json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'third_party/metaurban'),str(ROOT/'third_party/metaurban/metaurban/orca_algo/build')]
# run_episode seeds/imports the simulator within the run layout. Defer the
# camera-only wrapper until its existing _make_env has imported native classes.
from urban_service import runtime
native_make_env=runtime._make_env
def env_with_pan(config,pedestrian_count,record):
 env=native_make_env(config,pedestrian_count,record)
 from metaurban.component.sensors.rgb_camera import RGBCamera
 original=RGBCamera.perceive
 yaw=0
 def capture(self,*args,**kwargs):
  nonlocal yaw
  agent=next(iter(self.engine.agent_manager.active_agents.values()),None)
  if agent is not None and getattr(agent,'_urban_yield_hold',False) and math.hypot(*agent.velocity)<.1:
   yaw=min(90,yaw+30)
  if yaw and kwargs.get('new_parent_node') is not None:kwargs['hpr']=[yaw,-5,0]
  return original(self,*args,**kwargs)
 RGBCamera.perceive=capture
 return env
runtime._make_env=env_with_pan
if __name__=='__main__':
 import os
 if os.environ.get('PYTHONHASHSEED')!='100':
  os.execve(sys.executable,[sys.executable,*sys.argv],dict(os.environ,PYTHONHASHSEED='100'))
 c=json.loads((ROOT/'configs/streetscape_inspection_demo.json').read_text())
 out=ROOT/'runs/streetscape_inspection_pan_low100_20261102'
 result=runtime.run_episode(c,'distance',100,5,out,True)
 (out/'camera_pan_metadata.json').write_text(json.dumps(dict(rule='After physical speed <0.1 m/s and terminal hold requested, camera yaw advances by 30 deg per recorded frame up to 90 deg. This camera is not policy input.',control_source='Unchanged frozen runtime; camera-only wrapper in scripts/record_inspection_pan.py'),indent=2)+'\n')
 print(json.dumps(result,indent=2))
