#!/usr/bin/env python3
"""Publication figures from accepted fresh-test tables and actual RGB frames."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/route_refinement'
LABELS={'baseline':'PPO','predictive':'CV yield','route':'Route governor','route_intent':'Route + footprint'}


def build():
    evidence=json.loads((OUT/'test/summary.json').read_text())
    rows=[r for r in evidence['summary'] if r['density']=='all']
    fig,ax=plt.subplots(figsize=(9.3,3.25),layout='constrained')
    x=np.arange(len(rows));w=.23
    for i,(field,label,color) in enumerate([('strict_goals','Within 2 m + native flag','#267589'),
                                          ('contact_free_goals','Contact-free strict goals','#58a08a'),
                                          ('pedestrian_contacts','Pedestrian-contact episodes','#c96a53')]):
        vals=[r[field] for r in rows];bars=ax.bar(x+(i-1)*w,vals,w,label=label,color=color)
        ax.bar_label(bars,padding=2,fontsize=9)
    ax.set_xticks(x,[LABELS[r['method']] for r in rows]);ax.set_ylabel('Episodes')
    ax.set_ylim(0,max(r['requested'] for r in rows)+2)
    ax.set_title(f"Fresh matched test: {rows[0]['requested']} requested / {rows[0]['valid']} valid tasks per method",loc='left',fontsize=11)
    ax.legend(ncol=3,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.15),fontsize=8)
    ax.spines[['top','right']].set_visible(False);ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True));ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    directory=OUT/'figures';directory.mkdir(parents=True,exist_ok=True)
    for ext in ('png','pdf','svg'):fig.savefig(directory/f'fresh_outcomes.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    # These are native RGB observations, not generated images or map renderings.
    run=ROOT/'runs/route_inspection_high902_20261102'
    first=Image.open(run/'first_frame.png').convert('RGB');last=Image.open(run/'inspection.png').convert('RGB')
    panel=Image.new('RGB',(1920,590),'#163f50');panel.paste(first,(0,50));panel.paste(last,(960,50))
    draw=ImageDraw.Draw(panel);draw.text((15,15),'Native 3D: start of inspection mission (development seed 902, 15 people)',fill='white')
    draw.text((975,15),'Within 2 m, physical stop, camera pan and recorded streetscape',fill='white')
    panel.save(directory/'mission_scene_pair.png')
    # Every requested condition is shown, including invalid tasks and failures.
    episodes=json.loads((OUT/'test/episodes.json').read_text())
    conditions=sorted({(r['density'],r['seed']) for r in episodes})
    methods=[r['method'] for r in rows]
    matrix=np.zeros((len(conditions),len(methods)))
    for r in episodes:
        matrix[conditions.index((r['density'],r['seed'])),methods.index(r['method'])]=(-1 if not r['valid_task'] else 3 if r['contact_free_goal'] else 2 if r['strict_goal'] else 1 if r['pedestrian_contact'] else 0)
    from matplotlib.colors import ListedColormap,BoundaryNorm
    fig,ax=plt.subplots(figsize=(7,7),layout='constrained')
    cmap=ListedColormap(['#c8c8c8','#f1efe5','#cc705b','#d8b74d','#48978c']);norm=BoundaryNorm([-1.5,-.5,.5,1.5,2.5,3.5],5)
    ax.imshow(matrix,cmap=cmap,norm=norm,aspect='auto');ax.set_xticks(range(len(methods)),[LABELS[m] for m in methods],rotation=15)
    ax.set_yticks(range(len(conditions)),[f'{d} / {s}' for d,s in conditions]);ax.set_title('All matched conditions (no discarded failures)')
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=color,label=label) for color,label in zip(cmap.colors,['Invalid generated task','No strict goal','Pedestrian contact, no goal','Goal with contact','Contact-free strict goal'])],bbox_to_anchor=(.5,-.13),loc='upper center',ncol=2,frameon=False,fontsize=8)
    fig.savefig(directory/'all_conditions.png',dpi=160,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':build()
