#!/usr/bin/env python3
"""Publication figures and videos drawn exclusively from actual simulator logs."""
import argparse,csv,json,math,statistics
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import imageio.v2 as imageio

ROOT=Path(__file__).resolve().parents[1]
METHODS=['baseline','fixed_margin','adaptive_margin']
NAMES={'baseline':'Original ORCA','fixed_margin':'Fixed buffer','adaptive_margin':'Predictive buffer'}
COLORS={'baseline':'#52677a','fixed_margin':'#168573','adaptive_margin':'#bd7b19'}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def load_episode(campaign,scenario,case,method):
    p=campaign/f'{scenario}_{case}_{method}'
    return json.loads((p/'initial_state.json').read_text()),[json.loads(s) for s in (p/'steps.jsonl').read_text().splitlines()],json.loads((p/'summary.json').read_text())

def analysis(campaign):
    rows=json.loads((campaign/'results.json').read_text())
    fields=['scenario','method','case_id','success','native_collision','timeout','min_clearance_m','near_exposure_s','near_time_fraction','duration_s','path_length_m','wait_time_s','swept_overlap','wall_seconds']
    with (ROOT/'outputs/tables/test_episodes.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    groups=[]
    for scenario in ['circle_crossing','square_crossing','all']:
        for method in METHODS:
            a=[r for r in rows if r['method']==method and (scenario=='all' or r['scenario']==scenario)]
            paired=[]
            for r in a:
                b=next(x for x in rows if x['scenario']==r['scenario'] and x['case_id']==r['case_id'] and x['method']=='baseline')
                if r['success'] and b['success']:paired.append(r['duration_s']-b['duration_s'])
            groups.append(dict(scenario=scenario,method=method,n=len(a),successes=sum(x['success'] for x in a),collisions=sum(x['native_collision'] for x in a),
                mean_min_clearance_m=statistics.mean(x['min_clearance_m'] for x in a),mean_exposure_s=statistics.mean(x['near_exposure_s'] for x in a),
                mean_near_fraction=statistics.mean(x['near_time_fraction'] for x in a),paired_n=len(paired),paired_mean_delay_s=statistics.mean(paired),paired_median_delay_s=statistics.median(paired)))
    (ROOT/'outputs/tables/summary.json').write_text(json.dumps(groups,indent=2)+'\n')
    with (ROOT/'outputs/tables/summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(groups[0]));w.writeheader();w.writerows(groups)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(7.2,2.5),constrained_layout=True)
    allg=[x for x in groups if x['scenario']=='all']
    values=[[x['successes'] for x in allg],[100*x['mean_near_fraction'] for x in allg],[x['paired_mean_delay_s'] for x in allg]]
    titles=['Goal completion\n(20 cases per method)','Close-proximity\nexposure','Paired completion\ndelay']
    units=['Successful episodes','Mean time fraction (%)','Mean extra time (s), n=12']
    for ax,vs,title,unit in zip(axes,values,titles,units):
        ax.bar(range(3),vs,color=[COLORS[m] for m in METHODS],width=.6)
        ax.set_xticks(range(3),['Original','Fixed','Predictive']);ax.set_title(title,fontsize=9);ax.set_ylabel(unit,fontsize=8)
        for i,v in enumerate(vs):ax.text(i,v+max(max(vs)*.025,.01),f'{v:.2f}' if max(vs)<2 else f'{v:.1f}' if unit.endswith('(%)') else str(int(v)),ha='center',fontsize=9)
        ax.set_ylim(0,max(vs)*1.23 if max(vs) else 1)
    for ext in ['png','pdf','svg']:fig.savefig(ROOT/f'outputs/figures/outcomes.{ext}',dpi=220)
    plt.close(fig)
    # Fixed before viewing results: lowest test case ID in the circle family.
    fig,axes=plt.subplots(1,3,figsize=(7.2,2.65),constrained_layout=True)
    for ax,m in zip(axes,METHODS):
        initial,steps,summary=load_episode(campaign,'circle_crossing',100,m)
        a=[initial['ego']['position']]+[r['ego']['position'] for r in steps]
        for j in range(5):
            h=[initial['people'][j]['position']]+[r['people'][j]['position'] for r in steps]
            ax.plot(*np.array(h).T,color='#c7bdb2',linewidth=.8,zorder=1)
            ax.scatter(*h[0],color='#c7bdb2',s=10)
        ax.plot(*np.array(a).T,color=COLORS[m],lw=2,label='Robot')
        ax.plot(0,-4,'o',color=COLORS[m],ms=5);ax.plot(0,4,'*',color='#bf9100',ms=11)
        ax.plot(*a[-1],'x' if not summary['success'] else 'o',color='#a23030' if not summary['success'] else COLORS[m],ms=7)
        short={'baseline':'Original','fixed_margin':'Fixed','adaptive_margin':'Predictive'}[m]
        ax.set_title(f"{short}: {'goal' if summary['success'] else 'collision'}\n{summary['duration_s']:.2f} s",fontsize=9)
        ax.set(xlim=(-5.2,5.2),ylim=(-5.2,5.2),xlabel='x (m)',ylabel='y (m)');ax.set_aspect('equal');ax.grid(alpha=.12)
    for ext in ['png','pdf','svg']:fig.savefig(ROOT/f'outputs/figures/paired_paths.{ext}',dpi=220)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,1.7));ax.axis('off')
    labels=['Official CrowdNav\nscenario + coordinates','ORCA baseline\nproposed velocity','Fixed / predictive\nclearance buffer','ORCA velocity\noptimization','Native step\nmetrics + video']
    for i,label in enumerate(labels):
        x=.015+i*.2
        ax.text(x+.085,.5,label,transform=ax.transAxes,ha='center',va='center',fontsize=9,bbox=dict(boxstyle='round,pad=.6',fc='#eaf0f4' if i!=2 else '#e1f2ec',ec='#677e8b'))
        if i<4:ax.annotate('',xy=(x+.2,.5),xytext=(x+.172,.5),xycoords='axes fraction',arrowprops=dict(arrowstyle='->',color='#677e8b'))
    fig.tight_layout()
    for ext in ['png','pdf','svg']:fig.savefig(ROOT/f'outputs/figures/workflow.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    return groups

def draw_panel(initial,steps,summary,t,width=640,height=690):
    image=Image.new('RGB',(width,height),'#f5f7f9');d=ImageDraw.Draw(image)
    font=ImageFont.truetype(FONT,17);small=ImageFont.truetype(FONT,14);bold=ImageFont.truetype(BOLD,23)
    method=summary['method'];color=COLORS[method]
    d.rectangle((0,0,width,6),fill=color);d.text((25,20),NAMES[method],font=bold,fill='#1b2d3a')
    duration=summary['duration_s'];u=min(t,duration);dt=summary['dt_s']
    k=min(int(u/dt),len(steps));alpha=(u-k*dt)/dt if k<len(steps) else 0
    previous={'ego':initial['ego'],'people':initial['people']} if k==0 else steps[k-1]
    following=steps[min(k,len(steps)-1)]
    def interp(a,b):return [a[i]+alpha*(b[i]-a[i]) for i in range(2)]
    ego=interp(previous['ego']['position'],following['ego']['position'])
    people=[interp(a['position'],b['position']) for a,b in zip(previous['people'],following['people'])]
    def xy(p):return (width/2+p[0]*48,365-p[1]*48)
    for v in range(-5,6):
        x,y=xy((v,0))[0],xy((0,v))[1]
        d.line((x,110,x,620),fill='#e1e7eb');d.line((65,y,575,y),fill='#e1e7eb')
        d.text((x-4,623),str(v),font=small,fill='#7a8790')
    d.text((270,650),'Simulator x (m)',font=small,fill='#52616e')
    for j in range(5):
        trail=[initial['people'][j]['position']]+[r['people'][j]['position'] for r in steps[:k]]+[people[j]]
        d.line([xy(p) for p in trail],fill='#d9c5ac',width=2)
        x,y=xy(people[j]);rr=14.4
        d.ellipse((x-rr,y-rr,x+rr,y+rr),fill='#d49a59',outline='#865b32',width=1)
        d.text((x+17,y-8),f'P{j+1}',font=small,fill='#865b32')
    trail=[initial['ego']['position']]+[r['ego']['position'] for r in steps[:k]]+[ego]
    d.line([xy(p) for p in trail],fill=color,width=4)
    gx,gy=xy((0,4));d.ellipse((gx-16,gy-16,gx+16,gy+16),outline='#b38900',width=2);d.text((gx+21,gy-9),'Goal',font=small,fill='#9a7800')
    x,y=xy(ego);radius=14.4;d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color,outline='#ffffff',width=2)
    if t>=duration:
        status='GOAL REACHED' if summary['success'] else 'COLLISION'
        d.text((25,65),f'{status} at {duration:.2f} s — final frame held',font=font,fill='#168573' if summary['success'] else '#b33e3e')
    else:
        row=steps[min(k,len(steps)-1)];margin=row['decision'].get('margin_m',0)
        d.text((25,65),f'Running  |  margin per agent: {margin:.3f} m',font=font,fill='#52616e')
    return image

def video(campaign,scenario,case,filename):
    records=[load_episode(campaign,scenario,case,m) for m in METHODS]
    assert len({r[2]['initial_fingerprint'] for r in records})==1
    duration=max(r[2]['duration_s'] for r in records)+1
    fps=12;last=None
    with imageio.get_writer(str(filename),fps=fps,codec='libx264',quality=7,macro_block_size=1) as writer:
        for frame in range(math.ceil(duration*fps)):
            t=frame/fps
            canvas=Image.new('RGB',(1920,790),'white');d=ImageDraw.Draw(canvas)
            d.text((24,12),f'Urban service navigation | {scenario.replace("_"," ")} | official test case {case} | t={t:.2f} s',font=ImageFont.truetype(BOLD,25),fill='#1b2d3a')
            for j,(initial,steps,summary) in enumerate(records):canvas.paste(draw_panel(initial,steps,summary,t),(640*j,55))
            d.text((24,755),'Actual closed-loop logs; 5 pedestrians; coordinate sensing; native dt=0.25 s. Display interpolates linear motion; no physical walls are modeled.',font=ImageFont.truetype(FONT,16),fill='#52616e')
            writer.append_data(np.asarray(canvas));last=canvas
            if frame==int(2.5*fps):canvas.save(filename.with_suffix('.png'))
    return filename

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,default=ROOT/'runs/crowd_test_20261102');a=p.parse_args()
    analysis(a.campaign)
    for scenario,case,name in [('circle_crossing',100,'comparison_circle_100'),('square_crossing',100,'comparison_square_100'),('circle_crossing',105,'failure_circle_105')]:
        print(video(a.campaign,scenario,case,ROOT/f'outputs/videos/{name}.mp4'),flush=True)
