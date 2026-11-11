#!/usr/bin/env python3
"""Descriptive plots and paired seed-cluster intervals from accepted episodes."""
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'outputs/classical'
LABELS={'pp':'PP + static guard','rpp':'RPP-inspired','distance':'Distance yield','forecast_static':'Zero-velocity ablation','forecast':'Velocity forecast','dwa':'DWA-style'}
ORDER=list(LABELS);COLORS=['#87949b','#466e8b','#c38c4b','#a38bb3','#21877e','#506155']

def main():
 figdir=BASE/'figures';figdir.mkdir(exist_ok=True,parents=True)
 evidence=json.loads((BASE/'test/summary.json').read_text());episodes=json.loads((BASE/'test/episodes.json').read_text())
 rows={r['method']:r for r in evidence['summary'] if r['density']=='all'}
 plt.rcParams.update({'font.size':13,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
 fig,ax=plt.subplots(1,3,figsize=(10.5,3.8),constrained_layout=True)
 for a,field,title in zip(ax,['strict_goals','contact_free_goals','pedestrian_contacts'],['Strict arrival','Contact-free arrival','Pedestrian contact']):
  vals=[rows[m][field] for m in ORDER];a.barh(range(6),vals,color=COLORS);a.set_yticks(range(6),[LABELS[m] for m in ORDER] if a is ax[0] else []);a.invert_yaxis();a.set_xlim(0,max(r['valid'] for r in rows.values())+1);a.set_title(title,fontsize=13);a.set_xlabel('Episodes')
  for i,v in enumerate(vals):a.text(v+.15,i,str(v),va='center',fontsize=12)
 fig.savefig(figdir/'fresh_outcomes.png',bbox_inches='tight');plt.close(fig)
 # Every matched condition stays visible, including invalid and contact episodes.
 conditions=sorted({(r['seed'],r['density']) for r in episodes});lookup={(r['method'],r['seed'],r['density']):r for r in episodes}
 grid=np.array([[(-1 if not (r:=lookup[m,*cond])['valid_task'] else 2 if r['contact_free_goal'] else 1 if r['strict_goal'] else 0) for cond in conditions] for m in ORDER])
 from matplotlib.colors import ListedColormap,BoundaryNorm
 cmap=ListedColormap(['#e3e3e3','#aa5661','#d6b66e','#308e80']);norm=BoundaryNorm([-1.5,-.5,.5,1.5,2.5],4)
 fig,ax=plt.subplots(figsize=(11.5,3.8),constrained_layout=True);im=ax.imshow(grid,cmap=cmap,norm=norm,aspect='auto');ax.set_yticks(range(6),[LABELS[m] for m in ORDER]);ax.set_xticks(range(len(conditions)),[f'{s}\n{d}' for s,d in conditions],fontsize=8);ax.set_xlabel('Scene seed and crowd (shared scene seed is the clustering unit)');ax.set_title('All fresh random-street conditions');fig.colorbar(im,ax=ax,ticks=[-1,0,1,2],shrink=.8).ax.set_yticklabels(['Invalid','No strict goal','Goal + contact','Contact-free goal']);fig.savefig(figdir/'all_conditions.png',bbox_inches='tight');plt.close(fig)
 # Matched bootstrap uses whole scene seeds, retaining both crowd-size conditions.
 intervals=[];rng=np.random.default_rng(20261102);seeds=sorted({r['seed'] for r in episodes})
 for control,method in [('rpp','forecast'),('distance','forecast'),('forecast_static','forecast'),('dwa','forecast')]:
  for metric in ['strict_goal','contact_free_goal','pedestrian_contact','wait_s','box_near_fraction']:
   clusters=[]
   for seed in seeds:
    values=[]
    for cond in conditions:
     if cond[0]!=seed:continue
     a=lookup[control,*cond];b=lookup[method,*cond]
     if a['valid_task'] and b['valid_task']:values.append(float(b[metric])-float(a[metric]))
    clusters.append(values)
   boot=[]
   for sample in rng.integers(0,len(seeds),size=(10000,len(seeds))):
    values=[v for i in sample for v in clusters[i]]
    if values:boot.append(np.mean(values))
   actual=[v for cluster in clusters for v in cluster]
   intervals.append(dict(control=control,method=method,metric=metric,paired_conditions=len(actual),scene_clusters=len(seeds),mean_difference=float(np.mean(actual)),percentile95=[float(v) for v in np.quantile(boot,[.025,.975])]))
 (BASE/'test/paired_cluster_intervals.json').write_text(json.dumps(dict(seed=20261102,resamples=10000,method='Percentile paired bootstrap of scene seeds, keeping both densities together. Descriptive small-sample intervals, no significance claim.',contrasts=intervals),indent=2)+'\n')
 # Controlled diagnostic suite is never pooled with the random-street outcome bars.
 ce=json.loads((BASE/'encounter_test/summary.json').read_text());cs=ce['summary'];methods=[m for m in ORDER if m!='pp'];kinds=['crossing','receding','approaching','stationary']
 fig,axes=plt.subplots(1,2,figsize=(11.5,3.7),constrained_layout=True)
 for ax,field,title in zip(axes,['mean_wait_s','pedestrian_contacts'],['Mean waiting (s)','Pedestrian-contact episodes / 2']):
  width=.15
  for j,m in enumerate(methods):
   vals=[next(r[field] for r in cs if r['method']==m and r['density']==k) for k in kinds]
   ax.bar(np.arange(4)+(j-2)*width,vals,width,label=LABELS[m],color=COLORS[ORDER.index(m)])
  ax.set_xticks(range(4),kinds,rotation=12);ax.set_title(title,fontsize=11)
 axes[1].legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.2),ncol=2);fig.savefig(figdir/'controlled_encounters.png',bbox_inches='tight');plt.close(fig)
 # Retain every failure/contact case in a compact inspectable index.
 failure=[]
 for suite,campaign in [('test','classical_test_20261102'),('encounter_test','classical_encounter_test_20261102')]:
  for r in json.loads((BASE/suite/'episodes.json').read_text()):
   if r['strict_goal'] and not r['any_contact']:continue
   d=ROOT/'runs'/campaign/f"{r['density']}_seed{r['seed']}_{r['method']}"
   raw=[json.loads(l) for l in (d/'steps.jsonl').read_text().splitlines()] if (d/'steps.jsonl').exists() else []
   hit=next((x for x in raw if any(x['info'][k] for k in ['crash_human','crash_vehicle','crash_object','crash_building','crash_sidewalk'])),None)
   failure.append(dict(suite=suite,**r,first_contact_s=hit['sim_time_s'] if hit else None,first_contact_flags=hit['info'] if hit else None,last_info=raw[-1]['info'] if raw else None,trace=str((d/'steps.jsonl').relative_to(ROOT))))
 (BASE/'failure_index.json').write_text(json.dumps(failure,indent=2)+'\n')
 print(json.dumps(dict(random_conditions=len(conditions),failures_and_contacts_indexed=len(failure),figures=4),indent=2))

if __name__=='__main__':main()
