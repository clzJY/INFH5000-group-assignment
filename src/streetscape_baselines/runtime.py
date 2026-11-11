"""Actual MetaUrban runs with common route/state input and no neural inference."""
from dataclasses import asdict
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import traceback
import numpy as np

from urban_service.action_adapter import apply_speed_cap
from urban_service.controller import PoseTracker
from urban_service.metrics import EpisodeMetrics
from urban_service.provenance import dump_json,fingerprint,sha256,UPSTREAM_COMMIT
from streetscape_route.runtime import _make_env,_scene_fingerprint,snapshot,pedestrian_contact,input_errors
from .controller import Controller,METHODS
from .geometry import gaps

ROOT=Path(__file__).resolve().parents[2]


def people_bodies(env,people):
    from metaurban.component.agents.pedestrian.base_pedestrian import BasePedestrian
    native={str(o.id):o for o in env.engine.get_objects(lambda o:isinstance(o,BasePedestrian)).values()}
    return [[*p.position,float(native[p.actor_id].heading_theta),float(native[p.actor_id].LENGTH),
             float(native[p.actor_id].WIDTH),*p.velocity] for p in people]


def static_bodies(env):
    from metaurban.component.static_object.test_new_object import TestObject
    bodies=[]
    for obj in env.engine.get_objects(lambda o:isinstance(o,TestObject)).values():
        # TestObject uses local X=LENGTH, Y=WIDTH, unlike vehicle local axes.
        bodies.append([float(obj.position[0]),float(obj.position[1]),float(obj.heading_theta),
                       float(obj.LENGTH),float(obj.WIDTH),0.,0.])
    return bodies


def run_episode(config,method,seed,pedestrian_count,output,record=False):
    if method not in METHODS:raise ValueError(method)
    if config['env_config']['vehicle_config']['enable_reverse']:raise ValueError('Shared forward-only contract required')
    errors=input_errors(ROOT,config)
    if errors:raise RuntimeError('; '.join(errors))
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    dump_json(out/'config.json',config)
    source=ROOT/'third_party/metaurban';sys.path[:0]=[str(source/'metaurban/orca_algo/build'),str(source)]
    (out/'metaurban').symlink_to(source/'metaurban',target_is_directory=True)
    started=time.monotonic();oldcwd=Path.cwd();env=writer=None
    result=dict(status='error',source='actual_native_3d_simulator',study='common_input_classical',method=method,
        seed=seed,requested_pedestrians=pedestrian_count,config_sha256=fingerprint(config),upstream_commit=UPSTREAM_COMMIT,
        neural_inference=False,checkpoint_used=False)
    try:
        os.chdir(out);random.seed(seed);np.random.seed(seed)
        env=_make_env(config,pedestrian_count,record);observation,info=env.reset(seed=seed)
        dt=float(env.config['physics_world_step_size'])*int(env.config['decision_repeat'])
        tracker=PoseTracker();ego,people=snapshot(env,tracker,dt)
        route=[[float(v) for v in xy] for xy in env.agent.navigation.position_list]
        route_length=float(env.agent.navigation.reference_trajectory.length);goal=route[-1]
        statics=static_bodies(env)
        geometry=dict(length=float(env.agent.LENGTH),width=float(env.agent.WIDTH),
            wheelbase=float(env.agent.FRONT_WHEELBASE+env.agent.REAR_WHEELBASE),max_steer=math.radians(float(env.agent.max_steering)))
        result.update(initial_scene_fingerprint=_scene_fingerprint(env,ego,people),actual_initial_pedestrians=len(people),
            dt_s=dt,planned_route=route,goal_position=goal,initial_route_length_m=route_length,
            start_goal_distance_m=math.dist(ego.position,goal),ego_geometry=geometry,initial_static_bodies=statics,
            versions={p:importlib.metadata.version(p) for p in ('numpy','panda3d','gymnasium')},
            core_source_sha256={str(f.relative_to(ROOT)):sha256(f) for package in ('urban_service','streetscape_route','streetscape_baselines') for f in (ROOT/'src'/package).glob('*.py')})
        receipt=(source/'metaurban/assets').resolve().parents[1]/'import_receipt.json'
        result['asset_import_receipt_sha256']=sha256(receipt)
        initial=dict(ego=asdict(ego),pedestrians=[asdict(p) for p in people],pedestrian_boxes=people_bodies(env,people),static_bodies=statics)
        dump_json(out/'initial_state.json',initial)
        result['valid_task']=route_length>=config['route_min_length_m'] and result['start_goal_distance_m']>=config['route_min_length_m']
        if not result['valid_task']:
            result.update(status='invalid_task',invalid_reason='Predeclared route/start-goal length gate; no control steps');return result
        controller=Controller(route,config,**geometry)
        metrics=EpisodeMetrics(ego.position,config['near_clearance_m'])
        reached=False;native_ever=False;first_native=None;anomaly=False;box_near_s=0.;minimum_box=None
        stopped_s=inspection_s=0.;inspection_complete=False;inspection_contact=False;nav_result=None
        decisions_s=[]
        if record:
            import imageio.v2 as imageio
            writer=imageio.get_writer(str(out/'rollout.mp4'),fps=1/dt,codec='libx264',macro_block_size=1)
        with (out/'steps.jsonl').open('w') as log:
            for step in range(config['env_config']['horizon']):
                heading=float(env.agent.heading_theta);speed=math.hypot(*ego.velocity)
                pb=people_bodies(env,people);statics=static_bodies(env)
                state=dict(position=list(ego.position),heading=heading,speed=speed)
                # Static geometry is stored once in summary.json. Retain a full
                # context only if a native object actually changes its pose.
                context=dict(ego=state,people=pb,last_steering=controller.last_steering)
                if statics!=result['initial_static_bodies']:context['statics']=statics
                tick=time.perf_counter();decision=controller.update(method,state,pb,statics,dt);decisions_s.append(time.perf_counter()-tick)
                phase='inspection' if reached else 'navigation'
                proposed=[decision['steering'],1.]
                executed=apply_speed_cap(proposed,decision,speed,reverse_enabled=False)
                if reached:executed=(0.,-1. if speed>.05 else 0.)
                env.agent._urban_yield_hold=bool(decision['state']=='WAIT' or reached)
                observation,reward,terminated,truncated,info=env.step(list(executed))
                ego,people=snapshot(env,tracker,dt);post=people_bodies(env,people)
                g=gaps(np.array([[[*ego.position,float(env.agent.heading_theta)]]]),geometry['length'],geometry['width'],post,[0.],False)
                box_gap=float(g.min()) if g.size else None
                anomaly|=math.hypot(*ego.velocity)>config['physical_anomaly_speed_m_s']
                native=bool(info['native_arrive_dest'])
                if native and not native_ever:first_native=(step+1)*dt
                native_ever|=native
                ped_contact=pedestrian_contact(info,config['pedestrian_only_collision_attribution'])
                if not reached:
                    metrics.update(ego,people,dt,dict(info,crash_human=ped_contact),decision['state'])
                    if box_gap is not None:
                        minimum_box=box_gap if minimum_box is None else min(minimum_box,box_gap)
                        box_near_s+=dt if box_gap<config['near_clearance_m'] else 0.
                    if info['arrive_dest']:
                        reached=True;nav_result=metrics.summary(True,bool(truncated))
                else:
                    inspection_s+=dt
                    inspection_contact|=any(info.get(k,False) for k in ('crash_human','crash_vehicle','crash_object','crash_building','crash_sidewalk'))
                    stopped_s=stopped_s+dt if info['arrive_dest'] and math.hypot(*ego.velocity)<config['stop_speed_m_s'] else 0.
                    inspection_complete=stopped_s+1e-9>=config['inspection_hold_s'] and not inspection_contact
                row=dict(step=step,sim_time_s=(step+1)*dt,phase=phase,ego=asdict(ego),pedestrians=[asdict(p) for p in people],
                    pedestrian_boxes=post,heading_rad=float(env.agent.heading_theta),native_speed_m_s=float(env.agent.speed),
                    model_context=context,proposed_action=proposed,executed_action=list(executed),controller=decision,
                    goal_distance_m=float(info['goal_distance_m']),native_arrive_dest=native,route_completion=float(env.agent.navigation.route_completion),
                    pedestrian_contact=ped_contact,hold_brake_requested=env.agent._urban_yield_hold,box_clearance_m=box_gap,
                    controller_wall_s=decisions_s[-1],info={k:bool(info.get(k,False)) for k in
                    ('arrive_dest','crash_human','crash_vehicle','crash_object','crash_building','crash_sidewalk','out_of_road','max_step')})
                log.write(json.dumps(row,allow_nan=False)+'\n')
                if writer or inspection_complete:
                    import cv2
                    import imageio.v2 as imageio
                    camera=env.engine.get_sensor('rgb_camera');render=config['render']
                    image=camera.perceive(to_float=False,new_parent_node=env.agent.origin,position=render['position'],hpr=render['hpr'])
                    image=np.ascontiguousarray(image[...,::-1])
                    cv2.putText(image,f'{method} seed={seed} t={(step+1)*dt:.1f}s {decision["state"]} {phase}',(12,25),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
                    if writer:
                        writer.append_data(image)
                        if step==0:imageio.imwrite(str(out/'first_frame.png'),image)
                    if inspection_complete:imageio.imwrite(str(out/'inspection.png'),image)
                if terminated or truncated or inspection_complete:break
                if reached and config['inspection_hold_s']>0 and inspection_s>=config['inspection_max_s']:break
        result.update(nav_result or metrics.summary(reached,bool(truncated) or step+1>=config['env_config']['horizon']))
        result.update(status='complete',native_arrival_ever=native_ever,first_native_arrival_s=first_native,
            final_goal_distance_m=math.dist(ego.position,goal),physical_anomaly=anomaly,
            box_near_time_fraction=box_near_s/result['duration_s'],min_box_clearance_m=minimum_box,
            mean_controller_wall_s=float(np.mean(decisions_s)),max_controller_wall_s=max(decisions_s),
            inspection_complete=bool(inspection_complete and result['collision_free_success']),inspection_collision=inspection_contact,
            inspection_elapsed_s=inspection_s,recorded_video=record)
        return result
    except Exception as exc:
        result.update(error=f'{type(exc).__name__}: {exc}');(out/'error.txt').write_text(traceback.format_exc());raise
    finally:
        try:
            if writer:writer.close()
            if env:env.close()
        finally:
            os.chdir(oldcwd);result['wall_seconds']=time.monotonic()-started;dump_json(out/'summary.json',result)
