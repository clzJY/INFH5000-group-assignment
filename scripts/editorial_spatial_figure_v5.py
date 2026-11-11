#!/usr/bin/env python3
"""Plot only recorded local poses/footprints; never infer road/curb geometry."""
import argparse,json,math,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from matplotlib.lines import Line2D
R=Path(__file__).resolve().parents[1];OUT=R/'outputs/editorial_v5_20261111/figures'

def read(method):
 d=R/'runs/classical_encounter_development_v1'/('crossing_seed902_'+method)
 s=json.loads((d/'summary.json').read_text());initial=json.loads((d/'initial_state.json').read_text());trace=[json.loads(x) for x in (d/'steps.jsonl').read_text().splitlines()]
 return d,s,initial,trace

def corners(x,y,h,L,W):
 p=np.array([[-L/2,-W/2],[-L/2,W/2],[L/2,W/2],[L/2,-W/2]])
 c=math.cos(h);s=math.sin(h);return p@np.array([[c,s],[-s,c]])+np.array([x,y])

def main(records_dir):
 records_dir.mkdir(parents=True,exist_ok=True)
 receipt_path=records_dir/'figure_source_receipt.json'
 assert not receipt_path.exists(),'Preserve prior provenance; choose a new central records directory.'
 OUT.mkdir(parents=True,exist_ok=True);df,s,init,f=read('forecast');dr,sr,ir,r=read('rpp');assert s['initial_scene_fingerprint']==sr['initial_scene_fingerprint']
 assert all(a['pedestrians'][0]['position']==b['pedestrians'][0]['position'] for a,b in zip(f,r))
 route=np.asarray(s['planned_route']);ego=np.array([init['ego']['position'],*[x['ego']['position'] for x in f]])
 person=np.array([init['pedestrians'][0]['position'],*[x['pedestrians'][0]['position'] for x in f[:80]]])
 plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':200})
 fig,axes=plt.subplots(1,2,figsize=(9.6,3.5),gridspec_kw={'width_ratios':[1,1.45]})
 for ax in axes:
  for x,y,h,L,W,vx,vy in s['initial_static_bodies']:ax.add_patch(Polygon(corners(x,y,h,L,W),closed=True,color='#b9c0c5',alpha=.55,lw=.2))
  ax.plot(route[:,0],route[:,1],color='#7a868e',ls='--',lw=1.1,zorder=3)
  ax.set_aspect('equal',adjustable='box');ax.set_xlabel('Local x (m)');ax.set_ylabel('Local y (m)');ax.tick_params(labelsize=10);ax.grid(alpha=.13)
 axes[0].plot(ego[:,0],ego[:,1],color='#158a80',lw=1.7,zorder=4)
 axes[0].scatter(*route[0],marker='o',s=32,color='#24704c',zorder=5);axes[0].annotate('Start',route[0]+[1,1],fontsize=10)
 axes[0].scatter(*s['goal_position'],marker='*',s=90,color='#c2882d',zorder=5);axes[0].annotate('Goal',np.array(s['goal_position'])+[3,0],fontsize=10)
 axes[0].plot(person[:,0],person[:,1],color='#a14770',lw=1.4,zorder=5)
 axes[0].set_xlim(route[:,0].min()-8,route[:,0].max()+9);axes[0].set_ylim(route[:,1].min()-10,route[:,1].max()+7)
 axes[0].add_patch(Rectangle((98,-60),28,15,fill=False,ec='#485b69',ls=':',lw=1.2,zorder=6))
 axes[0].set_title('A  Recorded route and scene objects',fontsize=12,loc='left',pad=7)
 for method,trace,color,style in [('RPP',r,'#476a9c','--'),('Forecast',f,'#158a80','-')]:
  p=np.array([init['ego']['position'],*[x['ego']['position'] for x in trace[:80]]]);axes[1].plot(p[:,0],p[:,1],color=color,ls=style,lw=1.8,zorder=4)
  pose=trace[40];x,y=pose['ego']['position'];axes[1].add_patch(Polygon(corners(x,y,pose['heading_rad'],s['ego_geometry']['length'],s['ego_geometry']['width']),closed=True,fill=False,ec=color,lw=1.8,zorder=6))
 axes[1].plot(person[:,0],person[:,1],color='#a14770',lw=1.5,zorder=4)
 pb=f[40]['pedestrian_boxes'][0];axes[1].add_patch(Polygon(corners(*pb[:5]),closed=True,fill=False,ec='#a14770',lw=1.8,zorder=6))
 axes[1].scatter(*person[0],s=16,color='#a14770',zorder=5);axes[1].annotate('Person: first 8 s',person[0]+[1,.4],fontsize=10,color='#853857')
 axes[1].text(.02,.96,'Boxes at 4.1 s\nRegulated cap: 0 m/s\nForecast cap: 2 m/s',transform=axes[1].transAxes,va='top',fontsize=10,bbox=dict(facecolor='white',alpha=.88,edgecolor='none',pad=2))
 axes[1].set_xlim(98,126);axes[1].set_ylim(-60,-45);axes[1].set_title('B  Recorded crossing encounter',fontsize=12,loc='left',pad=7)
 handles=[Line2D([0],[0],color='#158a80',lw=1.8,label='Robot: forecast'),Line2D([0],[0],color='#476a9c',ls='--',lw=1.8,label='Robot: regulated'),Line2D([0],[0],color='#a14770',lw=1.8,label='Scripted pedestrian'),Line2D([0],[0],color='#7a868e',ls='--',label='Reference route'),Rectangle((0,0),1,1,facecolor='#b9c0c5',alpha=.65,label='Static footprints')]
 fig.legend(handles=handles,loc='lower center',ncol=5,fontsize=9.4,frameon=False,bbox_to_anchor=(.5,-.015),columnspacing=1.0,handlelength=1.8)
 fig.subplots_adjust(left=.07,right=.99,top=.88,bottom=.23,wspace=.35)
 for ext in ['png','svg']:fig.savefig(OUT/('recorded_scene_plan.'+ext),bbox_inches='tight',pad_inches=.08)
 plt.close(fig)
 receipt=dict(source='Existing controlled development seed902, crossing; no new simulation',source_directories=[str(df.relative_to(R)),str(dr.relative_to(R))],scene_fingerprint=s['initial_scene_fingerprint'],pose_frame_index=40,time_s=f[40]['sim_time_s'],person_trajectory_samples=len(person),road_or_curb_geometry_inferred=False,goal=s['goal_position'],figure=str((OUT/'recorded_scene_plan.png').relative_to(R)),source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for d in [df,dr] for p in [d/'summary.json',d/'steps.jsonl',d/'initial_state.json']})
 receipt_path.write_text(json.dumps(receipt,indent=2)+'\n');print(OUT/'recorded_scene_plan.png')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--records-dir',type=Path,required=True);a=p.parse_args();main(a.records_dir)
