#!/usr/bin/env python3
"""Validate common-input studies, replay decisions, and recompute outcomes."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from urban_service.controller import Actor
from urban_service.metrics import EpisodeMetrics
from urban_service.action_adapter import apply_speed_cap
from urban_service.provenance import dump_json,fingerprint,sha256
from streetscape_baselines.controller import Controller
from streetscape_baselines.geometry import gaps


def close(a,b):
    if a is None or b is None:return a is b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-7)
    return a==b


def accept(campaign,record,output):
    protocol=json.loads((campaign/'protocol.json').read_text());plan=json.loads((campaign/'conditions.json').read_text())
    frozen=protocol.get('stage')=='classical_frozen'
    for rel,h in protocol.get('frozen_source_sha256',{}).items():assert sha256(ROOT/rel)==h,rel
    methods=protocol['encounter_methods'] if 'encounter' in plan[0] else protocol['methods']
    episodes=[];matched={};traces={};steps=0;contexts=0
    for case in plan:
        name=f"{case['density']}_seed{case['seed']}_{case['method']}";directory=campaign/name
        s=json.loads((directory/'summary.json').read_text());config=json.loads((directory/'config.json').read_text())
        assert s['config_sha256']==fingerprint(config)
        assert s['status'] in ('complete','invalid_task')
        assert s['neural_inference'] is False and s['checkpoint_used'] is False
        if 'encounter' in case:
            assert config['encounter']==case['encounter'];base=dict(config);base.pop('encounter');assert base==protocol
        else:assert config==protocol
        for rel,h in s['core_source_sha256'].items():
            assert sha256(ROOT/rel)==h,(name,rel)
        condition=(case['density'],case['seed']);matched.setdefault(condition,[]).append((s['initial_scene_fingerprint'],s['valid_task']))
        assert s['valid_task']==(s['initial_route_length_m']>=config['route_min_length_m'] and s['start_goal_distance_m']>=config['route_min_length_m'])
        row=dict(density=case['density'],seed=case['seed'],method=case['method'],valid_task=s['valid_task'])
        if not s['valid_task']:
            assert not (directory/'steps.jsonl').exists()
            row.update(strict_goal=False,native_goal=False,pedestrian_contact=False,any_contact=False,contact_free_goal=False,
                duration_s=None,wait_s=None,box_near_fraction=None,minimum_box_gap_m=None,circle_near_fraction=None,
                mean_controller_ms=None,physical_anomaly=False,static_wait_s=None,no_feasible_steps=None)
        else:
            initial=json.loads((directory/'initial_state.json').read_text());raw=[json.loads(l) for l in (directory/'steps.jsonl').read_text().splitlines()]
            metrics=EpisodeMetrics(initial['ego']['position'],config['near_clearance_m'])
            geometry=s['ego_geometry'];controller=Controller(s['planned_route'],config,**geometry)
            minimum=None;near=0.;static_wait=0.;no_feasible=0;seen_native=False
            traces[(condition,case['method'])]=[[p['position'] for p in r['pedestrians']] for r in raw]
            for r in raw:
                if r['phase']!='navigation':continue
                ctx=r['model_context'];statics=ctx.get('statics',s['initial_static_bodies'])
                assert close(controller.last_steering,ctx['last_steering'])
                decision=controller.update(case['method'],ctx['ego'],ctx['people'],statics,s['dt_s'])
                for key in ('state','speed_cap_m_s','steering','reason','no_buffer_feasible','static_guard_active'):
                    assert close(decision[key],r['controller'][key]),(name,r['step'],key,decision[key],r['controller'][key])
                assert len(decision['candidates'])==len(r['controller']['candidates'])
                for a,b in zip(decision['candidates'],r['controller']['candidates']):
                    assert all(close(a[k],b[k]) for k in a),(name,r['step'],'candidate')
                action=apply_speed_cap([decision['steering'],1.],decision,ctx['ego']['speed'],reverse_enabled=False)
                assert all(close(a,b) for a,b in zip(action,r['executed_action']))
                g=gaps(np.array([[[*r['ego']['position'],r['heading_rad']]]]),geometry['length'],geometry['width'],r['pedestrian_boxes'],[0.],False)
                gap=float(g.min()) if g.size else None
                assert close(gap,r['box_clearance_m'])
                if gap is not None:
                    minimum=gap if minimum is None else min(minimum,gap)
                    near+=s['dt_s'] if gap<config['near_clearance_m'] else 0.
                assert close(r['goal_distance_m'],math.dist(r['ego']['position'],s['goal_position']))
                assert r['info']['arrive_dest']==bool(r['native_arrive_dest'] and r['goal_distance_m']<=config['goal_radius_m'])
                norm_contact=bool(r['info']['crash_human'] or r['info']['crash_vehicle'])
                assert r['pedestrian_contact']==norm_contact
                metrics.update(Actor(**r['ego']),[Actor(**p) for p in r['pedestrians']],s['dt_s'],dict(r['info'],crash_human=norm_contact),r['controller']['state'])
                static_wait+=s['dt_s'] if decision['state']=='WAIT' and decision['static_guard_active'] else 0.
                no_feasible+=decision['no_buffer_feasible'];seen_native|=r['native_arrive_dest'];steps+=1;contexts+=1
            summary=metrics.summary(any(r['info']['arrive_dest'] for r in raw),bool(raw[-1]['info']['max_step'] or len(raw)>=config['env_config']['horizon']))
            for key,value in summary.items():assert close(value,s[key]),(name,key,value,s[key])
            assert close(near/s['duration_s'],s['box_near_time_fraction']) and close(minimum,s['min_box_clearance_m'])
            assert s['native_arrival_ever']==seen_native
            assert not s['navigation_success'] or s['final_goal_distance_m']<=config['goal_radius_m']
            row.update(strict_goal=s['navigation_success'],native_goal=s['native_arrival_ever'],pedestrian_contact=s['pedestrian_collision'],
                any_contact=s['any_collision'],contact_free_goal=s['collision_free_success'],duration_s=s['duration_s'],wait_s=s['wait_time_s'],
                box_near_fraction=s['box_near_time_fraction'],minimum_box_gap_m=s['min_box_clearance_m'],circle_near_fraction=s['near_time_fraction'],
                mean_controller_ms=1000*s['mean_controller_wall_s'],physical_anomaly=s['physical_anomaly'],static_wait_s=static_wait,no_feasible_steps=no_feasible)
        episodes.append(row)
    assert len(episodes)==len(plan)
    assert all(len(v)==len(methods) and len(set(v))==1 for v in matched.values())
    human_difference=0.
    for condition in matched:
        a=traces.get((condition,methods[0]))
        if a is None:continue
        for method in methods[1:]:
            b=traces[(condition,method)]
            for x,y in zip(a,b):
                assert len(x)==len(y)
                human_difference=max(human_difference,max((math.dist(u,v) for u,v in zip(x,y)),default=0.))
    grouped=[]
    densities=sorted({r['density'] for r in episodes})
    for density in ['all',*densities]:
        for method in methods:
            requested=[r for r in episodes if r['method']==method and (density=='all' or r['density']==density)]
            valid=[r for r in requested if r['valid_task']]
            mean=lambda field:statistics.mean(r[field] for r in valid) if valid else None
            grouped.append(dict(density=density,method=method,requested=len(requested),valid=len(valid),invalid=len(requested)-len(valid),
                strict_goals=sum(r['strict_goal'] for r in valid),native_goals=sum(r['native_goal'] for r in valid),
                pedestrian_contacts=sum(r['pedestrian_contact'] for r in valid),any_contacts=sum(r['any_contact'] for r in valid),
                contact_free_goals=sum(r['contact_free_goal'] for r in valid),physical_anomalies=sum(r['physical_anomaly'] for r in valid),
                mean_wait_s=mean('wait_s'),mean_box_near_fraction=mean('box_near_fraction'),mean_controller_ms=mean('mean_controller_ms'),
                mean_static_wait_s=mean('static_wait_s')))
    lookup={((r['density'],r['seed']),r['method']):r for r in episodes};paired=[]
    pairs=[('rpp','distance'),('rpp','forecast'),('distance','forecast'),('forecast_static','forecast'),('dwa','forecast')]
    for control,method in pairs:
        if control not in methods or method not in methods:continue
        conditions=[cond for cond in matched if lookup[(cond,control)]['valid_task']]
        joint=[cond for cond in conditions if lookup[(cond,control)]['strict_goal'] and lookup[(cond,method)]['strict_goal']]
        paired.append(dict(control=control,method=method,n=len(conditions),rescued=sum(lookup[(cond,method)]['strict_goal'] and not lookup[(cond,control)]['strict_goal'] for cond in conditions),
            regressed=sum(lookup[(cond,control)]['strict_goal'] and not lookup[(cond,method)]['strict_goal'] for cond in conditions),
            contact_free_goal_delta=sum(lookup[(cond,method)]['contact_free_goal']-lookup[(cond,control)]['contact_free_goal'] for cond in conditions),
            jointly_successful_n=len(joint),mean_joint_delay_s=statistics.mean(lookup[(cond,method)]['duration_s']-lookup[(cond,control)]['duration_s'] for cond in joint) if joint else None))
    output.mkdir(parents=True,exist_ok=True)
    dump_json(output/'summary.json',dict(summary=grouped,paired=paired,suite='controlled' if 'encounter' in plan[0] else 'random_streets',
        notes=['No PPO inference; common route/state/actuator information.', 'RPP-inspired and DWA-style are adaptations, not official reproductions.',
               'Near exposure is sampled native planar box gap <1m, not legacy circle distance or human comfort.','No invalid tasks replaced and no anomalies discarded.']))
    dump_json(output/'episodes.json',episodes)
    for name,rows in [('episodes',episodes),('summary',grouped),('paired',paired)]:
        with (output/(name+'.csv')).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report=dict(passed=True,episodes=len(episodes),matched_conditions=len(matched),decision_steps=steps,
        controller_contexts_replayed=contexts,matched_initial_scenes=True,max_common_prefix_pedestrian_difference_m=human_difference,
        frozen_sources_verified=frozen,strict_goal_verified=True,neural_inference=False)
    dump_json(record,report);print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('campaign',type=Path);p.add_argument('--record',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();accept(a.campaign,a.record,a.output)
