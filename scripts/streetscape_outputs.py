#!/usr/bin/env python3
"""Generate tables and figures only from completed native MetaUrban rollouts."""
import argparse,csv,json,math,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from summarize import collect
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

METHODS=['baseline','distance','predictive']
NAMES=['PPO baseline','Distance yield','Predictive yield']
COLORS=['#52677a','#168573','#bd7b19']

def main():
 p=argparse.ArgumentParser();p.add_argument('campaign',type=Path);a=p.parse_args()
 rows=collect(a.campaign);assert len(rows)==60
 table=ROOT/'outputs/streetscape/tables';figdir=ROOT/'outputs/streetscape/figures'
 table.mkdir(parents=True,exist_ok=True);figdir.mkdir(parents=True,exist_ok=True)
 for r in rows:
  folder=a.campaign/f"{r['density']}_seed{r['seed']}_{r['method']}"
  steps=[json.loads(s) for s in (folder/'steps.jsonl').read_text().splitlines()]
  assert len(steps)==r['steps']
  r['action_intervention_steps']=sum(any(abs(x-y)>1e-8 for x,y in zip(s['raw_action'],s['executed_action'])) or s['hold_brake_requested'] for s in steps)
  r['action_intervention_fraction']=r['action_intervention_steps']/len(steps)
  assert r['pedestrian_collision']==any(s['pedestrian_contact'] for s in steps)
  assert r['actual_initial_pedestrians']==r['requested_pedestrians']
 joint=[];degenerate=[]
 for density,seed in sorted({(r['density'],r['seed']) for r in rows}):
  group=[r for r in rows if (r['density'],r['seed'])==(density,seed)]
  if all(r['navigation_success'] for r in group):joint.append((density,seed))
  if all(r['navigation_success'] and r['steps']==1 for r in group):
   starts=[]
   for r in group:
    folder=a.campaign/f"{r['density']}_seed{r['seed']}_{r['method']}"
    initial=json.loads((folder/'initial_state.json').read_text())
    starts.append(math.dist(initial['ego']['position'],r['goal_position'])<1e-8)
   if all(starts):degenerate.append((density,seed))
 nontrivial_joint=[x for x in joint if x not in degenerate]
 summaries=[]
 for density in ['low','high','all']:
  for method in METHODS:
   group=[r for r in rows if r['method']==method and (density=='all' or r['density']==density)]
   deltas=[];nontrivial_deltas=[]
   for r in group:
    if (r['density'],r['seed']) in joint:
     baseline=next(b for b in rows if b['density']==r['density'] and b['seed']==r['seed'] and b['method']=='baseline')
     deltas.append(r['duration_s']-baseline['duration_s'])
     if (r['density'],r['seed']) in nontrivial_joint:nontrivial_deltas.append(r['duration_s']-baseline['duration_s'])
   summaries.append(dict(density=density,method=method,n=len(group),goals=sum(r['navigation_success'] for r in group),
    pedestrian_contacts=sum(r['pedestrian_collision'] for r in group),any_contacts=sum(r['any_collision'] for r in group),
    collision_free_goals=sum(r['collision_free_success'] for r in group),timeouts=sum(r['timeout'] for r in group),
    mean_near_fraction=statistics.mean(r['near_time_fraction'] for r in group),
    median_min_clearance_m=statistics.median(r['min_clearance_m'] for r in group),
    mean_wait_s=statistics.mean(r['wait_time_s'] for r in group),
    intervention_episodes=sum(r['action_intervention_steps']>0 for r in group),
    mean_intervention_fraction=statistics.mean(r['action_intervention_fraction'] for r in group),
    jointly_successful_n=len(deltas),paired_mean_delay_s=statistics.mean(deltas) if deltas else None,
    nontrivial_joint_success_n=len(nontrivial_deltas),nontrivial_paired_mean_delay_s=statistics.mean(nontrivial_deltas) if nontrivial_deltas else None))
 fields=['density','seed','method','navigation_success','pedestrian_collision','any_collision','collision_free_success','timeout','duration_s','path_length_m','min_clearance_m','near_time_fraction','wait_time_s','action_intervention_steps','action_intervention_fraction']
 with (table/'episodes.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 with (table/'summary.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
 sensitivity=[]
 for method in METHODS:
  group=[r for r in rows if r['method']==method and (r['density'],r['seed']) not in degenerate]
  sensitivity.append(dict(method=method,n=len(group),goals=sum(r['navigation_success'] for r in group),pedestrian_contacts=sum(r['pedestrian_collision'] for r in group),collision_free_goals=sum(r['collision_free_success'] for r in group),mean_near_fraction=statistics.mean(r['near_time_fraction'] for r in group)))
 (table/'summary.json').write_text(json.dumps(dict(summary=summaries,jointly_successful_conditions=joint,
  zero_displacement_single_step_goal_conditions=degenerate,nontrivial_sensitivity=sensitivity,
  sensitivity_note='Post-hoc data-quality diagnostic, not a changed frozen outcome definition. All 60 original runs and native counts are retained.'),indent=2)+'\n')
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
 fig,axes=plt.subplots(1,3,figsize=(7.2,2.65),layout='constrained')
 allrows=[r for r in summaries if r['density']=='all']
 data=[[r['goals'] for r in allrows],[r['pedestrian_contacts'] for r in allrows],[100*r['mean_near_fraction'] for r in allrows]]
 for ax,values,title,label in zip(axes,data,['Goal completion','Pedestrian contacts','Close-proximity exposure'],['Episodes / 20','Episodes / 20','Mean episode time (%)']):
  ax.bar(range(3),values,color=COLORS,width=.62);ax.set_xticks(range(3),['PPO','Distance','Predictive']);ax.set_title(title,fontsize=9);ax.set_ylabel(label,fontsize=8)
  top=20 if label=='Episodes / 20' else max(max(values)*1.25,.5)
  ax.set_ylim(0,top+2 if label=='Episodes / 20' else top)
  for k,v in enumerate(values):ax.text(k,v+.025*top,f'{int(v)}' if label=='Episodes / 20' else f'{v:.2f}',ha='center',fontsize=9)
 for ext in ['png','pdf','svg']:fig.savefig(figdir/f'outcomes.{ext}',dpi=230)
 plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(7.2,2.6),layout='constrained')
 for ax,density in zip(axes,['low','high']):
  selected=[r for r in summaries if r['density']==density]
  ax.bar(range(3),[r['goals'] for r in selected],color=COLORS,width=.6)
  ax.set(ylim=(0,11),ylabel='Goals / 10 cases',title=f"{5 if density=='low' else 15} pedestrians")
  ax.set_xticks(range(3),NAMES,fontsize=8)
 for ext in ['png','pdf','svg']:fig.savefig(figdir/f'density_outcomes.{ext}',dpi=230)
 plt.close(fig)
 print(json.dumps(allrows,indent=2))

if __name__=='__main__':main()
