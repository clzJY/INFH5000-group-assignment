#!/usr/bin/env python3
"""Additional exact physical-input pairing audit, independent of scene hash."""
import argparse,json
from pathlib import Path

def audit(campaign):
 plan=json.loads((campaign/'conditions.json').read_text());groups={}
 for r in plan:
  d=campaign/f"{r['density']}_seed{r['seed']}_{r['method']}";s=json.loads((d/'summary.json').read_text());i=json.loads((d/'initial_state.json').read_text())
  clean=lambda actor:{k:v for k,v in actor.items() if k!='actor_id'}
  physical=dict(ego=clean(i['ego']),people=sorted((clean(p) for p in i['pedestrians']),key=lambda x:json.dumps(x,sort_keys=True)),
    people_boxes=sorted(i['pedestrian_boxes']),static_boxes=sorted(s['initial_static_bodies']),ego_geometry=s['ego_geometry'],route=s['planned_route'],dt=s['dt_s'])
  condition=(r['density'],r['seed'])
  if condition in groups:assert physical==groups[condition],(condition,r['method'])
  else:groups[condition]=physical
 return dict(campaign=str(campaign),episodes=len(plan),conditions=len(groups),exact_initial_physical_inputs=True,random_UUIDs_excluded=True,static_geometry_order_canonicalized=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('campaigns',type=Path,nargs='+');p.add_argument('--record',type=Path,required=True);a=p.parse_args();rows=[audit(c) for c in a.campaigns];a.record.write_text(json.dumps(dict(passed=True,checks=rows),indent=2)+'\n');print(json.dumps(rows,indent=2))
