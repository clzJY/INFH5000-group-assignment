#!/usr/bin/env python3
"""Compose real RGB frames with truthful timing and measured status labels."""
import json,math,shutil
from pathlib import Path
import imageio.v2 as imageio
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/streetscape/videos';OUT.mkdir(parents=True,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def compare(seed,development=False,clip_failure=False):
 methods=['baseline','distance']
 folders=[ROOT/f'runs/streetscape_demo_high{seed}_{m}_20261102' for m in methods]
 summaries=[json.loads((p/'summary.json').read_text()) for p in folders]
 assert len({r['initial_scene_fingerprint'] for r in summaries})==1
 steps=[[json.loads(s) for s in (p/'steps.jsonl').read_text().splitlines()] for p in folders]
 readers=[imageio.get_reader(p/'rollout.mp4') for p in folders]
 fps=10;start=0;end=max(len(s) for s in steps)+10
 if clip_failure:
  first=next((j for j,s in enumerate(steps[0]) if s['pedestrian_contact']),0)
  start=max(0,first-30);end=min(end,first+120)
 name='development_yield_comparison' if development else 'test_contact_failure'
 path=OUT/(name+'.mp4')
 cache=[None,None];indexes=[-1,-1]
 with imageio.get_writer(path,fps=fps,codec='libx264',quality=None,macro_block_size=1,ffmpeg_params=['-crf','22','-preset','fast','-threads','2']) as writer:
  for frame in range(start,end):
   canvas=Image.new('RGB',(1920,720),'white');d=ImageDraw.Draw(canvas)
   label='Development example' if development else 'Held-out test failure example'
   d.text((20,10),f'Native MetaUrban 3D | {label} | seed {seed} | 15 pedestrians | t={(frame+1)/fps:.1f} s',font=ImageFont.truetype(BOLD,25),fill='#193847')
   for j,(method,summary,states,reader) in enumerate(zip(methods,summaries,steps,readers)):
    k=min(frame,len(states)-1)
    if k!=indexes[j]:cache[j]=Image.fromarray(reader.get_data(k));indexes[j]=k
    canvas.paste(cache[j],(960*j,82))
    title='PPO baseline' if method=='baseline' else 'Distance yielding + low-speed hold'
    d.text((960*j+18,48),title,font=ImageFont.truetype(BOLD,23),fill='#52677a' if j==0 else '#168573')
    row=states[k];speed=math.hypot(*row['ego']['velocity'])
    gap=min(math.dist(row['ego']['position'],p['position'])-row['ego']['radius']-p['radius'] for p in row['pedestrians'])
    status=f"{row['controller']['state']} | speed {speed:.2f} m/s | proxy gap {gap:.2f} m"
    if frame>=len(states):status=('GOAL' if summary['navigation_success'] else 'TIMEOUT / FAILED')+f" at {summary['duration_s']:.1f} s | final frame held"
    d.text((960*j+18,630),status,font=ImageFont.truetype(FONT,21),fill='#193847')
   footer='Actual camera frames and logged actions; fixed checkpoint and paired initial scene. Reverse disabled in both methods.'
   d.text((20,673),footer,font=ImageFont.truetype(FONT,18),fill='#52616e')
   writer.append_data(np.asarray(canvas))
   if frame==min(start+30,end-1):canvas.save(path.with_suffix('.png'))
 for r in readers:r.close()
 return path

if __name__=='__main__':
 print(compare(900,development=True),flush=True)
 print(compare(100,clip_failure=True),flush=True)
 for source,name in [
  ('runs/streetscape_first_person_900_20261102/rollout.mp4','first_person_goal_run.mp4'),
  ('runs/streetscape_demo_high900_distance_20261102/rollout.mp4','modified_goal_run.mp4'),
  ('runs/streetscape_demo_high100_predictive_20261102/rollout.mp4','predictive_test100.mp4')]:
  shutil.copy2(ROOT/source,OUT/name)
 shutil.copy2(ROOT/'runs/streetscape_first_person_900_20261102/goal_view.png',OUT/'goal_view.png')
