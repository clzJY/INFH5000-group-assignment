#!/usr/bin/env python3
"""Compose actual closed-loop RGB repeats, explicitly labelling held frames."""
import json
from pathlib import Path
import cv2
import imageio.v2 as imageio
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    left=ROOT/'runs/route_rgb_baseline_high902_20261102';right=ROOT/'runs/route_inspection_high902_20261102'
    destination=ROOT/'outputs/route_refinement/videos';destination.mkdir(parents=True,exist_ok=True)
    readers=[imageio.get_reader(str(d/'rollout.mp4')) for d in (left,right)]
    summaries=[json.loads((d/'summary.json').read_text()) for d in (left,right)]
    lengths=[r.count_frames() for r in readers]
    writer=imageio.get_writer(str(destination/'development_route_comparison.mp4'),fps=10,codec='libx264',macro_block_size=1)
    frames=[None,None]
    try:
        for i in range(max(lengths)):
            canvas=np.full((720,1920,3),(20,39,47),dtype=np.uint8)
            cv2.putText(canvas,'ACTUAL NATIVE 3D | DEVELOPMENT seed 902 | 15 pedestrians | matched initial scene',(22,32),cv2.FONT_HERSHEY_SIMPLEX,.72,(255,255,255),2)
            for j,(reader,n,s) in enumerate(zip(readers,lengths,summaries)):
                if i<n:frames[j]=reader.get_next_data()
                x=j*960;canvas[95:635,x:x+960]=frames[j]
                title='Frozen PPO (forward-only)' if j==0 else 'Route governor + route-aware footprint shield'
                cv2.putText(canvas,title,(x+16,76),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2)
                state='Frame held after episode end' if i>=n else f'Live rollout t={(i+1)/10:.1f}s'
                cv2.putText(canvas,state,(x+16,666),cv2.FONT_HERSHEY_SIMPLEX,.62,(255,255,255),1)
                outcome=f"strict goal={s['navigation_success']} | any contact={s['any_collision']}"
                if j==1:outcome+=' | stop + inspection complete'
                cv2.putText(canvas,outcome,(x+16,699),cv2.FONT_HERSHEY_SIMPLEX,.55,(221,231,233),1)
            writer.append_data(canvas)
            if i==min(max(lengths)-1,lengths[1]+10):imageio.imwrite(str(destination/'development_route_comparison.png'),canvas)
    finally:
        writer.close()
        for r in readers:r.close()


if __name__=='__main__':main()
