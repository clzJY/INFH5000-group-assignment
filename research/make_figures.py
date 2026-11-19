"""Publication figures drawn only from recorded images, geometry and results."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,Polygon as PlotPolygon
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/results/figures';OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
LABELS={'rpp':'RPP-inspired','forecast':'Speed forecast','dwa':'DWA-style','mppi':'MPPI-style','lattice':'Rule local planner','vlm':'Frozen VLM','lora':'Adapted VLM','lora_s1':'Adapted seed 1','lora_s2':'Adapted seed 2','lora_no_rgb':'No RGB','lora_no_image':'No visual input','lora_no_language':'Minimal instruction'}

def atlas():
    fig,ax=plt.subplots(2,3,figsize=(9,5.5),gridspec_kw={'height_ratios':[1,1.1]})
    for j,map_id in enumerate(['X','S','SC']):
        r=ROOT/'research/runs/main_classical_v1'/f'{map_id}_wide_p5_s1600_lattice'
        scene=json.loads((r/'scene.json').read_text());image=Image.open(r/'first_frame.png');ax[0,j].imshow(image);ax[0,j].axis('off');ax[0,j].set_title({'X':'Intersection','S':'Straight sidewalk','SC':'Curved street'}[map_id])
        from shapely.geometry import shape
        region=shape(scene['region'])
        for poly in region.geoms if hasattr(region,'geoms') else [region]:
            if poly.geom_type=='Polygon':
                points=np.asarray(poly.exterior.coords);ax[1,j].fill(points[:,0],points[:,1],color='#ededed',zorder=0)
                for hole in poly.interiors:
                    ring=np.asarray(hole.coords);ax[1,j].fill(ring[:,0],ring[:,1],color='white',zorder=.1)
        for body in scene['statics']:
            x,y,h,length,width=body[:5]
            corners=np.array([[-length/2,-width/2],[-length/2,width/2],[length/2,width/2],[length/2,-width/2]])
            rotation=np.array([[np.cos(h),np.sin(h)],[-np.sin(h),np.cos(h)]])
            ax[1,j].add_patch(PlotPolygon(corners@rotation+np.array([x,y]),facecolor='#555555',edgecolor='none',alpha=.8,zorder=1))
        route=np.asarray(scene['route']);ax[1,j].plot(route[:,0],route[:,1],color='#277ca8',lw=1.4,label='Shared reference')
        trace=[json.loads(x) for x in (r/'steps.jsonl').read_text().splitlines()];xy=np.array([x['post_position'] for x in trace]);ax[1,j].plot(xy[:,0],xy[:,1],color='#cb5e3e',lw=1,label='Executed rule planner')
        ax[1,j].scatter(*route[0],c='green',s=15);ax[1,j].scatter(*route[-1],c='red',marker='*',s=35);ax[1,j].set_aspect('equal');ax[1,j].set_xlabel('Local x (m)');ax[1,j].set_ylabel('Local y (m)')
    ax[1,0].legend(fontsize=9.5,loc='best');fig.tight_layout();fig.savefig(OUT/'scene_atlas.png');plt.close(fig)

def pipeline():
    fig,ax=plt.subplots(figsize=(10,2.6));ax.set_xlim(0,10);ax.set_ylim(0,2.6);ax.axis('off')
    nodes=[(.05,1.25,1.7,.85,'Native RGB +\nlocal map + instruction'),(2.15,1.25,1.7,.85,'SmolVLM2\nvision + text LoRA'),(4.3,1.25,1.4,.85,'A–F\nlocal action token'),(6.1,1.25,1.65,.85,'Footprint + motion\nconstraint checks'),(8.15,1.25,1.7,.85,'Native steering\nand wheel physics')]
    for x,y,w,h,t in nodes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.05',facecolor='#edf3f5',edgecolor='#466574'));ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=10.5)
    for a,b in zip(nodes[:-1],nodes[1:]):ax.annotate('',(b[0]-.05,1.67),(a[0]+a[2]+.05,1.67),arrowprops={'arrowstyle':'->','color':'#466574'})
    ax.text(2.99,.7,'Shared geometry + route: five paths + stop\nOffline labels: geometric rollout ranking',ha='center',va='center',fontsize=10)
    ax.text(6.95,.7,'Unsafe proposal → rule fallback\nNo candidate feasible → physical stop',ha='center',va='center',fontsize=10)
    ax.text(5,.13,'High-level choice: 1 Hz   |   Candidate revalidation and actuation: 10 Hz',ha='center',fontsize=11)
    fig.tight_layout();fig.savefig(OUT/'pipeline.png');plt.close(fig)

def main_results():
    rows=json.loads((ROOT/'research/results/core/summary.json').read_text());methods=['rpp','forecast','dwa','mppi','lattice','vlm','lora']
    fig,ax=plt.subplots(1,2,figsize=(9,3.8));allrows={r['method']:r for r in rows if r['map']=='all'};x=np.arange(len(methods))
    ax[0].bar(x-.17,[100*allrows[m]['strict']/allrows[m]['n'] for m in methods],.34,color='#a9bbc2',label='Strict arrival')
    ax[0].bar(x+.17,[100*allrows[m]['clean']/allrows[m]['n'] for m in methods],.34,color='#287f8e',label='Contact-free arrival')
    ax[0].set_xticks(x,[LABELS[m] for m in methods],rotation=35,ha='right');ax[0].set_ylabel('Episodes (%)');ax[0].set_ylim(0,105);ax[0].legend(fontsize=9.5)
    for m,c in [('lattice','#cb5e3e'),('vlm','#8c8c8c'),('lora','#287f8e')]:
        rr=[next(r for r in rows if r['method']==m and r['map']==mapp) for mapp in ['X','S','SC']]
        ax[1].plot(['Intersection','Straight','Curve'],[100*r['clean']/r['n'] for r in rr],'-o',label=LABELS[m],color=c)
    ax[1].set_ylabel('Contact-free arrival (%)');ax[1].set_ylim(0,105);ax[1].legend(fontsize=9.5);fig.tight_layout();fig.savefig(OUT/'main_results.png');plt.close(fig)

if __name__=='__main__':
    atlas();pipeline();main_results()
