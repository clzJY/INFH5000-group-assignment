"""Independent rollout audit, paired condition summaries and cluster intervals."""
import argparse,csv,json,math,statistics
from collections import defaultdict
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('campaigns',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rows=[];audits=[]
    for campaign in a.campaigns:
        plan=json.loads((campaign/'plan.json').read_text())
        assert len(plan)==len({tuple(sorted(r.items())) for r in plan})
        for case in plan:
            name='{map}_{width}_p{pedestrians}_s{seed}_{method}'.format(**case);r=campaign/name
            s=json.loads((r/'summary.json').read_text());assert s['status'] in ('complete','invalid_task'),name
            if s['status']=='invalid_task':
                rows.append(dict(**case,campaign=campaign.name,valid=False,strict_goal=False,contact_free=False,any_contact=False,duration_s=None));continue
            trace=[json.loads(x) for x in (r/'steps.jsonl').read_text().splitlines()];dt=.1
            contacts=any(x['contact'] for x in trace);strict=any(x['strict_arrival'] for x in trace)
            assert all(x['strict_arrival']==bool(x['native_arrival'] and x['goal_distance_m']<=2) for x in trace)
            assert contacts==s['any_contact'] and strict==s['strict_goal'] and bool(strict and not contacts)==s['contact_free']
            wait=sum(x['decision']['speed_cap_m_s']<=1e-6 for x in trace)*dt
            assert math.isclose(wait,s['waiting_s'],abs_tol=1e-7)
            assert math.isclose(len(trace)*dt,s['duration_s'],abs_tol=1e-7)
            assert math.isclose(sum(x['post_speed']<.1 for x in trace)*dt,s['physical_standstill_s'],abs_tol=1e-7)
            assert all(abs(x['action'][0])<=1 and abs(x['action'][1])<=1 for x in trace)
            assert math.isclose(sum(x['outside_walkable'] for x in trace)/len(trace),s['outside_walkable_fraction'],abs_tol=1e-7)
            queries=json.loads((r/'vlm_queries.json').read_text());overrides=0
            qindex=0
            for x in trace:
                while qindex+1<len(queries) and queries[qindex+1]['step']<=x['step']:qindex+=1
                if queries and 'selected' in x['decision']:overrides+=int(queries[qindex]['choice']!=x['decision']['selected'])
            rows.append(dict(**case,campaign=campaign.name,valid=True,strict_goal=strict,contact_free=strict and not contacts,any_contact=contacts,
                             pedestrian_contact=s['pedestrian_contact'],duration_s=s['duration_s'],waiting_s=wait,standstill_s=s['physical_standstill_s'],
                             near_fraction=s['near_fraction'],outside_walkable_fraction=s['outside_walkable_fraction'],travel_m=s['travel_m'],
                             p95_controller_wall_s=s['p95_controller_wall_s'],initial_fingerprint=s['initial_fingerprint'],queries=len(queries),
                             query_override_fraction=overrides/len(trace) if queries else None))
            audits.append(dict(name=name,steps=len(trace),metrics_recomputed=True))
    grouped=defaultdict(list)
    for r in rows:grouped[r['method']].append(r)
    summaries=[]
    for method,rs in grouped.items():
        valid=[r for r in rs if r['valid']]
        for map_id in ['all','X','S','SC']:
            selected=[r for r in valid if map_id=='all' or r['map']==map_id]
            if not selected:continue
            summaries.append(dict(method=method,map=map_id,n=len(selected),strict=sum(r['strict_goal'] for r in selected),clean=sum(r['contact_free'] for r in selected),
                                  contacts=sum(r['any_contact'] for r in selected),waiting_s=statistics.mean(r['waiting_s'] for r in selected),
                                  standstill_s=statistics.mean(r['standstill_s'] for r in selected),outside_fraction=statistics.mean(r['outside_walkable_fraction'] for r in selected),
                                  p95_wall_ms=1000*statistics.mean(r['p95_controller_wall_s'] for r in selected)))
    lookup={(r['map'],r['width'],r['pedestrians'],r['seed'],r['method']):r for r in rows};paired=[];rng=np.random.default_rng(20261119)
    for control in ('rpp','forecast','dwa','mppi','lattice','vlm'):
        keys=[k[:-1] for k in lookup if k[-1]=='lora' and (*k[:-1],control) in lookup]
        if not keys:continue
        clusters=sorted({(k[0],k[3]) for k in keys});deltas=[]
        for cluster in clusters:
            subset=[k for k in keys if (k[0],k[3])==cluster]
            deltas.append(statistics.mean(int(lookup[(*k,'lora')]['contact_free'])-int(lookup[(*k,control)]['contact_free']) for k in subset))
        bootstrap=np.asarray(deltas)[rng.integers(0,len(deltas),size=(10000,len(deltas)))].mean(axis=1)
        joint=[k for k in keys if lookup[(*k,'lora')]['strict_goal'] and lookup[(*k,control)]['strict_goal']]
        paired.append(dict(control=control,method='lora',conditions=len(keys),clusters=len(clusters),clean_delta_pp=100*statistics.mean(deltas),
                           interval_95_pp=(100*np.percentile(bootstrap,[2.5,97.5])).tolist(),joint_successes=len(joint),
                           joint_delay_s=statistics.mean(lookup[(*k,'lora')]['duration_s']-lookup[(*k,control)]['duration_s'] for k in joint) if joint else None))
    # Initial physical conditions must match across all methods of the same campaign.
    conditions=defaultdict(set)
    for r in rows:
        if r['valid']:conditions[(r['map'],r['width'],r['pedestrians'],r['seed'])].add(r['initial_fingerprint'])
    assert all(len(s)==1 for s in conditions.values()),'Unmatched initial scenes'
    for name,data in (('episodes',rows),('summary',summaries),('paired',paired)):
        (a.output/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
        fields=list(dict.fromkeys(k for r in data for k in r))
        with (a.output/(name+'.csv')).open('w') as f:
            writer=csv.DictWriter(f,fields,lineterminator="\n");writer.writeheader();writer.writerows(data)
    (a.output/'audit.json').write_text(json.dumps(dict(passed=True,episodes=len(rows),decision_steps=sum(r['steps'] for r in audits),matched_conditions=len(conditions),all_initial_fingerprints_match=True),indent=2)+'\n')
    print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
