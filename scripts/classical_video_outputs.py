#!/usr/bin/env python3
"""Native RGB evidence: verify repeated physics, compose synchronized panels."""
import json,math,os
from pathlib import Path
import cv2
import imageio.v2 as imageio
import numpy as np
ROOT=Path(__file__).resolve().parents[1];V=ROOT/'runs/classical_videos_20261102';OUT=ROOT/'outputs/classical/videos';OP=ROOT.parents[2]/'storage_management/ucmp_week3_classical_baselines_20261102-104447'

def trace(d):return [json.loads(s) for s in (d/'steps.jsonl').read_text().splitlines()]

def main():
 OUT.mkdir(parents=True,exist_ok=True);checks=[]
 for name,control in [('crossing_rpp','runs/classical_encounter_development_v1/crossing_seed902_rpp'),('crossing_forecast','runs/classical_encounter_development_v1/crossing_seed902_forecast'),('crossing_dwa','runs/classical_encounter_development_v1/crossing_seed902_dwa'),('stationary_forecast','runs/classical_encounter_development_v1/stationary_seed902_forecast'),('inspection_forecast','runs/classical_development_v1/high_seed902_forecast')]:
  a=trace(ROOT/control);b=trace(V/name);s=json.loads((V/name/'summary.json').read_text());c=json.loads((ROOT/control/'summary.json').read_text())
  nav=[r for r in b if r['phase']=='navigation'];assert len(nav)==len(a)
  pos=max(math.dist(x['ego']['position'],y['ego']['position']) for x,y in zip(a,nav));act=max(max(abs(u-v) for u,v in zip(x['executed_action'],y['executed_action'])) for x,y in zip(a,nav));people=max((math.dist(p['position'],q['position']) for x,y in zip(a,nav) for p,q in zip(x['pedestrians'],y['pedestrians'])),default=0.)
  assert pos<=1e-5 and act<=1e-5 and people<=1e-5
  assert s['initial_scene_fingerprint']==c['initial_scene_fingerprint']
  reader=imageio.get_reader(str(V/name/'rollout.mp4'));n=reader.count_frames();reader.close();assert n==len(b)
  check=dict(name=name,navigation_steps=len(a),video_frames=n,max_ego_difference_m=pos,max_action_difference=act,max_pedestrian_difference_m=people,strict_goal=s['navigation_success'],contact_free=s['collision_free_success'])
  if name=='inspection_forecast':
   hold=[r for r in b if r['phase']=='inspection'];assert s['inspection_complete'] and not s['inspection_collision'];assert all(math.hypot(*r['ego']['velocity'])<.1 and r['goal_distance_m']<=2 for r in hold[-10:])
   check.update(inspection_complete=True,last_second_max_speed_m_s=max(math.hypot(*r['ego']['velocity']) for r in hold[-10:]))
  checks.append(check)
 # One short development scene: real native rendering, synchronized simulation time.
 names=['crossing_rpp','crossing_forecast','crossing_dwa'];readers=[imageio.get_reader(str(V/n/'rollout.mp4')) for n in names];lengths=[r.count_frames() for r in readers];rows=[trace(V/n) for n in names];summaries=[json.loads((V/n/'summary.json').read_text()) for n in names];frames=[None]*3
 writer=imageio.get_writer(str(OUT/'classical_crossing_comparison.mp4'),fps=10,codec='libx264',macro_block_size=1)
 titles=['RPP-inspired','Route + velocity forecast','DWA-style']
 try:
  for i in range(max(lengths)):
   canvas=np.full((510,1920,3),(21,39,47),np.uint8)
   cv2.putText(canvas,'ACTUAL NATIVE 3D | controlled crossing | development seed 902 | same pedestrian motion',(18,30),cv2.FONT_HERSHEY_SIMPLEX,.72,(255,255,255),2)
   for j,(reader,n) in enumerate(zip(readers,lengths)):
    if i<n:frames[j]=reader.get_next_data()
    x=j*640;canvas[88:448,x:x+640]=cv2.resize(frames[j],(640,360));r=rows[j][min(i,n-1)]
    cv2.putText(canvas,titles[j],(x+14,67),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
    status='HELD after episode end' if i>=n else f'Live t={r["sim_time_s"]:.1f}s cap={r["controller"]["speed_cap_m_s"]:.2f}m/s'
    cv2.putText(canvas,status,(x+14,474),cv2.FONT_HERSHEY_SIMPLEX,.55,(230,240,240),1)
    cv2.putText(canvas,f'Goal={summaries[j]["navigation_success"]} contact={summaries[j]["any_collision"]} wait={summaries[j]["wait_time_s"]:.1f}s',(x+14,501),cv2.FONT_HERSHEY_SIMPLEX,.5,(230,240,240),1)
   writer.append_data(canvas)
   if i==40:imageio.imwrite(OUT/'crossing_comparison_t4.1.png',canvas)
 finally:
  writer.close()
  for r in readers:r.close()
 # Hard links avoid duplicating original video bytes while preserving both entries.
 for name,target in [('inspection_forecast','inspection_mission.mp4'),('stationary_forecast','stationary_limitation.mp4')]:
  dst=OUT/target
  if not dst.exists():os.link(V/name/'rollout.mp4',dst)
  src=V/name/('inspection.png' if name=='inspection_forecast' else 'first_frame.png')
  dst=OUT/('inspection_view.png' if name=='inspection_forecast' else 'stationary_first_frame.png')
  if not dst.exists():os.link(src,dst)
 # Figure uses actual start and stopped RGB, with no synthetic scene generation.
 start=imageio.imread(V/'inspection_forecast/first_frame.png');stop=imageio.imread(V/'inspection_forecast/inspection.png')
 canvas=np.full((610,1920,3),(21,39,47),np.uint8);canvas[45:585,:960]=start;canvas[45:585,960:]=stop
 for x,t in [(14,'Actual native RGB: departure'),(974,'Strict arrival, physical stop, captured street view')]:cv2.putText(canvas,t,(x,31),cv2.FONT_HERSHEY_SIMPLEX,.68,(255,255,255),2)
 fig=ROOT/'outputs/classical/figures';fig.mkdir(parents=True,exist_ok=True);imageio.imwrite(fig/'mission_scene_pair.png',canvas)
 (OP/'video_acceptance.json').write_text(json.dumps(dict(passed=True,selection='Development seed902 fixed before fresh outcomes; no fresh example chosen for appearance.',checks=checks),indent=2)+'\n');print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
