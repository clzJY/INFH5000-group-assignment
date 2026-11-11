#!/usr/bin/env python3
"""Recompute outcomes and candidate decisions from raw logs, then write tables."""
import argparse
from dataclasses import asdict
import csv
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from urban_service.controller import Actor
from urban_service.metrics import EpisodeMetrics
from urban_service.provenance import dump_json, fingerprint, sha256
from streetscape_route.controller import Body,IntentGovernor
from streetscape_route.navigation import RouteGovernor


def close(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-7)
    return a==b


def accept(campaign,record,output):
    c=json.loads((campaign/'protocol.json').read_text())
    plan=json.loads((campaign/'conditions.json').read_text())
    for rel,h in c.get('frozen_source_sha256',{}).items(): assert sha256(ROOT/rel)==h,rel
    episodes=[];results={};steps_total=0;contexts_total=0;matched={};human_traces={}
    for case in plan:
        name=f"{case['density']}_seed{case['seed']}_{case['method']}"
        directory=campaign/name;s=json.loads((directory/'summary.json').read_text())
        assert s['config_sha256']==fingerprint(c),name
        assert s['status'] in ('complete','invalid_task'),name
        for rel,h in s['core_source_sha256'].items():
            assert sha256(ROOT/rel)==h,(name,rel)
        cond=(case['density'],case['seed']);matched.setdefault(cond,[]).append(s['initial_scene_fingerprint'])
        assert s['valid_task']==(s['initial_route_length_m']>=c['route_min_length_m'] and s['start_goal_distance_m']>=c['route_min_length_m'])
        row=dict(density=case['density'],seed=case['seed'],method=case['method'],valid_task=s['valid_task'])
        if not s['valid_task']:
            assert not (directory/'steps.jsonl').exists()
            row.update(strict_goal=False,native_goal=False,pedestrian_contact=False,any_contact=False,contact_free_goal=False,
                       wait_s=0.,duration_s=None,near_fraction=None,action_intervention_fraction=None,route_correction_fraction=None,
                       pedestrian_speed_intervention_fraction=None,final_goal_distance_m=None,physical_anomaly=False)
        else:
            initial=json.loads((directory/'initial_state.json').read_text())
            metrics=EpisodeMetrics(initial['ego']['position'],c['near_clearance_m'])
            rows=[json.loads(l) for l in (directory/'steps.jsonl').read_text().splitlines()]
            shield=IntentGovernor(c['refinement'],case['method']=='route_intent')
            rg=RouteGovernor(s['planned_route'],c['route_governor'])
            human_traces[(cond,case['method'])]=[[p['position'] for p in r['pedestrians']] for r in rows]
            for r in rows:
                if r['phase']!='navigation':continue
                info=dict(r['info'],crash_human=r['pedestrian_contact'])
                metrics.update(Actor(**r['ego']),[Actor(**p) for p in r['pedestrians']],s['dt_s'],info,r['controller']['state'])
                assert r['info']['arrive_dest']==bool(r['native_arrive_dest'] and r['goal_distance_m']<=c['goal_radius_m']),name
                assert close(r['goal_distance_m'],math.dist(r['ego']['position'],s['goal_position']))
                if case['method']=='baseline': assert r['raw_action']==r['executed_action'],name
                elif case['method']=='predictive': assert r['raw_action'][0]==r['executed_action'][0],name
                else:
                    assert r['executed_action'][0]==r['governed_action'][0]
                    ctx=r['model_context'];ego=Body(**ctx['ego']);people=[Body(**p) for p in ctx['pedestrians']]
                    rg.index=r['route_governor']['route_index']
                    # Native wheelchair wheelbase and max steering are pinned
                    # in this source revision; verify against logged curvature.
                    wheelbase=2.81;maxsteer=math.pi/3
                    curvature=math.tan(maxsteer*r['governed_action'][0])/wheelbase
                    assert close(curvature,r['controller']['curvature_m_inv'])
                    predicted=shield.update(ego,people,r['governed_action'],ctx['speed_m_s'],curvature,s['dt_s'],
                        lambda b,v,target,settings:rg.predict(b,v,target,settings,wheelbase,maxsteer))
                    for key in ('state','speed_cap_m_s','risk_clearance_m','clearance_m','reason','no_buffer_feasible'):
                        assert close(predicted[key],r['controller'][key]),(name,r['step'],key,predicted[key],r['controller'][key])
                    contexts_total+=1
                steps_total+=1
            recomputed=metrics.summary(any(r['info']['arrive_dest'] for r in rows),bool(rows[-1]['info']['max_step'] or len(rows)>=c['env_config']['horizon']))
            for k,v in recomputed.items():assert close(v,s[k]),(name,k,v,s[k])
            strict=s['navigation_success']
            assert not strict or s['final_goal_distance_m']<=c['goal_radius_m']
            assert s['native_arrival_ever']==any(r['native_arrive_dest'] for r in rows)
            row.update(strict_goal=strict,native_goal=s['native_arrival_ever'],pedestrian_contact=s['pedestrian_collision'],
                       any_contact=s['any_collision'],contact_free_goal=s['collision_free_success'],wait_s=s['wait_time_s'],
                       duration_s=s['duration_s'],near_fraction=s['near_time_fraction'],final_goal_distance_m=s['final_goal_distance_m'],
                       physical_anomaly=s['physical_anomaly'],
                       action_intervention_fraction=sum(any(abs(a-b)>1e-7 for a,b in zip(r['raw_action'],r['executed_action'])) for r in rows)/len(rows),
                       route_correction_fraction=sum(bool(r.get('route_governor') and r['route_governor']['active']) for r in rows)/len(rows),
                       pedestrian_speed_intervention_fraction=sum(r['controller'].get('reason') in ('footprint_intent','least_predicted_overlap') for r in rows)/len(rows))
        episodes.append(row);results[(cond,case['method'])]=row
    assert len(episodes)==len(plan)
    assert all(len(set(v))==1 and len(v)==len(c['methods']) for v in matched.values())
    grouped=[]
    for density in ['all',*c['densities']]:
        for method in c['methods']:
            rows=[r for r in episodes if r['method']==method and (density=='all' or r['density']==density)]
            valid=[r for r in rows if r['valid_task']]
            grouped.append(dict(density=density,method=method,requested=len(rows),valid=len(valid),invalid_generated=len(rows)-len(valid),
                strict_goals=sum(r['strict_goal'] for r in valid),native_goals=sum(r['native_goal'] for r in valid),
                pedestrian_contacts=sum(r['pedestrian_contact'] for r in valid),any_contacts=sum(r['any_contact'] for r in valid),
                contact_free_goals=sum(r['contact_free_goal'] for r in valid),physical_anomalies=sum(r['physical_anomaly'] for r in valid),
                mean_wait_s=statistics.mean(r['wait_s'] for r in valid) if valid else None,
                mean_near_fraction=statistics.mean(r['near_fraction'] for r in valid) if valid else None,
                mean_action_intervention_fraction=statistics.mean(r['action_intervention_fraction'] for r in valid) if valid else None,
                mean_route_correction_fraction=statistics.mean(r['route_correction_fraction'] for r in valid) if valid else None,
                mean_pedestrian_speed_intervention_fraction=statistics.mean(r['pedestrian_speed_intervention_fraction'] for r in valid) if valid else None))
    paired=[]
    for control,method in [('baseline','predictive'),('baseline','route'),('baseline','route_intent'),('route','route_intent'),('predictive','route_intent')]:
        if control not in c['methods'] or method not in c['methods']:continue
        cases=[cond for cond in matched if results[(cond,control)]['valid_task'] and results[(cond,method)]['valid_task']]
        jointly=[cond for cond in cases if results[(cond,control)]['strict_goal'] and results[(cond,method)]['strict_goal']]
        paired.append(dict(control=control,method=method,n=len(cases),
            rescued=sum(results[(cond,method)]['strict_goal'] and not results[(cond,control)]['strict_goal'] for cond in cases),
            regressed=sum(results[(cond,control)]['strict_goal'] and not results[(cond,method)]['strict_goal'] for cond in cases),
            jointly_successful_n=len(jointly),mean_joint_delay_s=statistics.mean(results[(cond,method)]['duration_s']-results[(cond,control)]['duration_s'] for cond in jointly) if jointly else None))
    max_human_difference=0.
    for cond in matched:
        base=human_traces.get((cond,c['methods'][0]))
        if base is None: continue
        for method in c['methods'][1:]:
            other=human_traces.get((cond,method),[])
            for a,b in zip(base,other):
                # Original actor iteration order is stable under paired resets.
                assert len(a)==len(b)
                max_human_difference=max(max_human_difference,max((math.dist(x,y) for x,y in zip(a,b)),default=0.))
    output.mkdir(parents=True,exist_ok=True)
    dump_json(output/'summary.json',dict(summary=grouped,paired=paired,notes=[
        'Arrival requires native flag AND <=2 m endpoint distance; earlier frozen native-only totals use a different definition.',
        'Invalid generated tasks are listed and not silently replaced. Numerical anomalies remain in primary valid-task counts.',
        'Near fraction retains the legacy circle proxy for comparability; it is not box distance or human comfort.',
        'Seeds are paired across methods and shared across crowd sizes; counts are descriptive, not independent significance tests.']))
    dump_json(output/'episodes.json',episodes)
    for name,rows in [('episodes',episodes),('summary',grouped),('paired',paired)]:
        with (output/(name+'.csv')).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report=dict(passed=True,episodes=len(episodes),matched_conditions=len(matched),decision_steps=steps_total,
                candidate_contexts_recomputed=contexts_total,matched_initial_scenes=True,
                max_common_prefix_pedestrian_position_difference_m=max_human_difference,
                frozen_sources_verified=bool(c.get('frozen_source_sha256')),strict_goals_verified=True)
    dump_json(record,report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('campaign',type=Path);p.add_argument('--record',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();accept(a.campaign,a.record,a.output)
