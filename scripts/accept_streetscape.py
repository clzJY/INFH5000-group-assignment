#!/usr/bin/env python3
"""Independently recompute decision-level metrics and paired-scene integrity."""
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from summarize import collect
from urban_service.provenance import sha256

def main():
 p=argparse.ArgumentParser();p.add_argument('campaign',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 rows=collect(a.campaign);assert len(rows)==60
 protocol=json.loads((a.campaign/'protocol.json').read_text())
 for path,expected in protocol['frozen_source_sha256'].items():assert sha256(ROOT/path)==expected,path
 assert not set(protocol['development_seeds'])&set(protocol['test_seeds'])
 steps_checked=0;traces={};bounds=0;motion_max_delta=0
 for r in rows:
  folder=a.campaign/f"{r['density']}_seed{r['seed']}_{r['method']}"
  initial=json.loads((folder/'initial_state.json').read_text())
  states=[json.loads(s) for s in (folder/'steps.jsonl').read_text().splitlines()]
  assert len(states)==r['steps'] and len(initial['pedestrians'])==r['requested_pedestrians']
  assert abs(r['duration_s']-.1*len(states))<1e-7
  prior=initial['ego']['position'];length=0;minimum=math.inf;near=wait=0
  for s in states:
   pos=s['ego']['position'];assert all(math.isfinite(v) for v in pos)
   length+=math.dist(prior,pos);prior=pos
   d=min(math.dist(pos,h['position'])-s['ego']['radius']-h['radius'] for h in s['pedestrians'])
   minimum=min(minimum,d);near+=d<protocol['near_clearance_m'];wait+=s['controller']['state']=='WAIT'
   raw=s['raw_action'];executed=s['executed_action'];assert all(math.isfinite(v) and -1<=v<=1 for v in executed)
   assert executed[0]==max(-1,min(1,raw[0]))
   if r['method']=='baseline' or s['controller']['state']=='PASS':assert executed==raw
   else:assert executed[1]<=raw[1]+1e-12
   assert s['pedestrian_contact']==bool(s['info']['crash_human'] or s['info']['crash_vehicle'])
   if s['hold_brake_requested']:assert r['method']!='baseline' and s['controller']['state']=='WAIT'
  assert abs(length-r['path_length_m'])<1e-7
  assert abs(minimum-r['min_clearance_m'])<1e-8
  assert abs(near/len(states)-r['near_time_fraction'])<1e-8
  assert abs(wait*.1-r['wait_time_s'])<1e-7
  assert r['pedestrian_collision']==any(s['pedestrian_contact'] for s in states)
  assert r['navigation_success']==any(s['info']['arrive_dest'] for s in states)
  assert r['collision_free_success']==(r['navigation_success'] and not r['any_collision'])
  assert not any(any(s['info'][k] for k in ['crash_human','crash_vehicle','crash_object','crash_building']) for s in states) or r['any_collision']
  traces[(r['density'],r['seed'],r['method'])]=states;steps_checked+=len(states)
 for density,seed in sorted({(r['density'],r['seed']) for r in rows}):
  group=[traces[(density,seed,m)] for m in ['baseline','distance','predictive']]
  for idx in range(min(map(len,group))):
   for sample in group[1:]:
    for x,y in zip(group[0][idx]['pedestrians'],sample[idx]['pedestrians']):motion_max_delta=max(motion_max_delta,math.dist(x['position'],y['position']))
  bounds+=1
 report=dict(status='PASS',episodes=60,matched_conditions=bounds,decision_steps_checked=steps_checked,
  metrics_recomputed=['path length','sampled minimum proxy gap','sampled near-time fraction','waiting','native pedestrian contact attribution','goal flags'],
  source_hashes_unchanged=True,max_common_prefix_pedestrian_position_difference_m=motion_max_delta,
  note='Any-contact summary also includes native boundary contacts; boundary flags are accumulated by the runtime but absent from the per-step raw flag subset. No continuous-contact or real-world safety guarantee is inferred.')
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
