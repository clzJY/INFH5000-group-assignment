"""Fresh multi-scene native Bullet rollouts with logged RGB-conditioned guidance."""
import argparse,json,math,os,sys,time,urllib.request,base64,io,random
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'research'),str(ROOT/'third_party/metaurban'),str(ROOT/'third_party/metaurban/metaurban/orca_algo/build')]
from streetscape_route.runtime import _make_env,snapshot,_scene_fingerprint
from streetscape_baselines.runtime import people_bodies,static_bodies
from streetscape_baselines.controller import Controller
from urban_service.controller import PoseTracker
from urban_service.action_adapter import apply_speed_cap
from urban_service.provenance import fingerprint
from local_planner import LocalPlanner
from observation import compose,PROMPT
from probe_scene import polygons
from routing import reference_route
from panda3d.core import loadPrcFileData
loadPrcFileData('', 'egl-device-index '+os.environ.get('INFH_EGL_DEVICE','3'))

def config(map_id,width):
    c=json.loads((ROOT/'configs/classical_frozen_20261102.json').read_text())
    c['tracking']['max_speed_m_s']=2.;c['env_config'].update(map=map_id,num_scenarios=20000,object_density=.15,horizon=1200)
    # Controlled clear-width factor (PGBlock doubles these dimensions).
    c['env_config']['predefined_config']={'Sidewalk':[{'Type':'Neighborhood 1'},
        {'Buffer_Lane_Furnishing_Width':[.15,.15]},{'Furnishing_Width':[.4,.4]},
        {'Clear_Width':[1.3,1.3] if width=='narrow' else [2.3,2.3]},
        {'Buffer_Frontage_Clear_Width':[.1,.1]},{'Frontage_Width':[.4,.4]}, {'Building_Width':[1.,1.]}]}
    c['render'].update(width=480,height=320)
    return c

def rgb_frame(env,c):
    r=c['render'];image=env.engine.get_sensor('rgb_camera').perceive(to_float=False,new_parent_node=env.agent.origin,position=r['position'],hpr=r['hpr'])
    return np.ascontiguousarray(image[...,::-1])

def query(image,method,url):
    buffer=io.BytesIO();image.save(buffer,format='PNG')
    data=json.dumps(dict(image=base64.b64encode(buffer.getvalue()).decode(),mode=method)).encode()
    req=urllib.request.Request(url+'/predict',data,{'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as resp:return json.load(resp)

def run(a):
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'metaurban').symlink_to(ROOT/'third_party/metaurban/metaurban',target_is_directory=True)
    c=config(a.map,a.width);(out/'config.json').write_text(json.dumps(c,indent=2)+'\n')
    if a.collect:c['env_config']['horizon']=600
    (out/'config.json').write_text(json.dumps(c,indent=2)+'\n')
    os.chdir(out);random.seed(a.seed);np.random.seed(a.seed)
    started=time.monotonic();env=None;writer=None
    summary=dict(map=a.map,width=a.width,pedestrians=a.pedestrians,seed=a.seed,method=a.method,stage=a.stage,status='error')
    import hashlib
    summary['research_source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'research').glob('*.py')}
    try:
        print('RESET_BEGIN',a.map,a.seed,flush=True)
        env=_make_env(c,a.pedestrians,True);obs,info=env.reset(seed=a.seed)
        print('RESET_COMPLETE',time.monotonic()-started,flush=True)
        original_route=np.asarray(env.agent.navigation.position_list);region=polygons(env).buffer(.05)
        route,routing=reference_route(original_route,region,static_bodies(env))
        print('ROUTE_COMPLETE',routing,time.monotonic()-started,flush=True)
        g=dict(length=float(env.agent.LENGTH),width=float(env.agent.WIDTH),wheelbase=float(env.agent.FRONT_WHEELBASE+env.agent.REAR_WHEELBASE),max_steer=math.radians(env.agent.max_steering))
        dt=float(env.config['physics_world_step_size'])*int(env.config['decision_repeat']);tracker=PoseTracker();ego,people=snapshot(env,tracker,dt)
        initial=fingerprint(dict(route=route.tolist(),ego=list(ego.position),people=sorted([list(p.position) for p in people]),statics=sorted(static_bodies(env))))
        planner=LocalPlanner(route,c,region,g);base=Controller(route,c,**g)
        length=float(np.linalg.norm(np.diff(route,axis=0),axis=1).sum())
        summary.update(initial_fingerprint=initial,route_length_m=length,initial_goal_distance_m=math.dist(ego.position,route[-1]),region_area_m2=region.area,geometry=g,routing=routing)
        from shapely.geometry import mapping
        (out/'scene.json').write_text(json.dumps(dict(route=route.tolist(),region=mapping(region),statics=static_bodies(env),ego=[*ego.position,float(env.agent.heading_theta)]))+'\n')
        if length<5 or summary['initial_goal_distance_m']<5:
            summary.update(status='invalid_task',strict_goal=False,contact_free=False);return summary
        if a.video:
            import imageio.v2 as imageio
            writer=imageio.get_writer(out/'rollout.mp4',fps=5,codec='libx264',macro_block_size=1)
        wait=stand=near=outside_s=0.;contacts=False;ped_contact=False;travel=0.;lastpos=np.asarray(ego.position);rows=0;queries=[];samples=0;wall=[];lastchoice=None;last_query_step=-100
        with (out/'steps.jsonl').open('w') as log:
            for step in range(c['env_config']['horizon']):
                pb=people_bodies(env,people);sb=static_bodies(env);state=dict(position=list(ego.position),heading=float(env.agent.heading_theta),speed=math.hypot(*ego.velocity))
                t=time.monotonic();selection=None
                if a.method in ('rpp','forecast','dwa'):
                    dec=base.update(a.method,state,pb,sb,dt)
                    if a.collect and step%10==0:data=planner.evaluate(state,pb,sb)
                else:
                    data=planner.evaluate(state,pb,sb,'mppi' if a.method=='mppi' else 'lattice')
                    # Query at 1 Hz; revalidate a held choice at every 10-Hz physics decision.
                    if a.method.startswith(('vlm','lora')) and step-last_query_step>=10:
                        image=compose(rgb_frame(env,c),state,route,pb,sb,data,region,
                                      blank_rgb=a.method.endswith('no_rgb'),blank_all=a.method.endswith('no_image'))
                        prediction=query(image,a.method,a.server);lastchoice=int(prediction['choice']);last_query_step=step
                        queries.append(dict(step=step,**prediction));selection=lastchoice
                    elif a.method.startswith(('vlm','lora')):selection=lastchoice
                    elif a.method=='lattice':
                        if step-last_query_step>=10:lastchoice=int(data['index']);last_query_step=step
                        selection=lastchoice
                    dec=planner.decision(data,selection,dt)
                wall.append(time.monotonic()-t)
                if a.collect and step%10==0:
                    image=compose(rgb_frame(env,c),state,route,pb,sb,data,region)
                    dest=out/'samples';dest.mkdir(exist_ok=True);image.save(dest/f'{step:04d}.png')
                    with (out/'samples.jsonl').open('a') as f:f.write(json.dumps(dict(image=f'samples/{step:04d}.png',label=int(data['index']),feasible=data['feasible'].tolist(),scores=data['score'].tolist(),step=step))+'\n')
                    samples+=1
                action=apply_speed_cap([dec['steering'],1.],dec,math.hypot(*ego.velocity),reverse_enabled=False)
                env.agent._urban_yield_hold=bool(dec['state']=='WAIT')
                obs,reward,terminated,truncated,info=env.step(list(action));ego,people=snapshot(env,tracker,dt)
                hit=any(info.get(k,False) for k in ('crash_human','crash_vehicle','crash_object','crash_building','crash_sidewalk'))
                contacts|=hit;ped_contact|=bool(info.get('crash_human') or info.get('crash_vehicle'))
                wait+=dt*(dec['speed_cap_m_s']<=1e-6);stand+=dt*(math.hypot(*ego.velocity)<.1)
                travel+=float(np.linalg.norm(np.asarray(ego.position)-lastpos));lastpos=np.asarray(ego.position)
                from streetscape_baselines.geometry import gaps
                pg=gaps(np.array([[[*ego.position,float(env.agent.heading_theta)]]]),g['length'],g['width'],people_bodies(env,people),[0.],False)
                gap=float(pg.min()) if pg.size else None;near+=dt*(gap is not None and gap<1.)
                from shapely.geometry import Polygon
                h=float(env.agent.heading_theta);vertices=np.array([[-g['length']/2,-g['width']/2],[-g['length']/2,g['width']/2],[g['length']/2,g['width']/2],[g['length']/2,-g['width']/2]])@np.array([[math.cos(h),math.sin(h)],[-math.sin(h),math.cos(h)]])+np.asarray(ego.position)
                outside=not region.covers(Polygon(vertices));outside_s+=dt*outside
                row=dict(step=step,time_s=(step+1)*dt,ego=state,post_position=list(ego.position),post_speed=math.hypot(*ego.velocity),action=list(action),decision=dec,
                         contact=hit,pedestrian_contact=bool(info.get('crash_human') or info.get('crash_vehicle')),goal_distance_m=math.dist(ego.position,route[-1]),
                         native_arrival=bool(info.get('native_arrive_dest')),strict_arrival=bool(info.get('arrive_dest')),box_gap_m=gap,
                         out_of_road=bool(info.get('out_of_road')),post_heading=h,outside_walkable=outside,controller_wall_s=wall[-1])
                log.write(json.dumps(row)+'\n');rows+=1
                if writer is not None and step%2==0:writer.append_data(rgb_frame(env,c))
                if step==0:
                    from PIL import Image
                    Image.fromarray(rgb_frame(env,c)).save(out/'first_frame.png')
                if terminated or truncated:break
        summary.update(status='complete',strict_goal=bool(info.get('arrive_dest')),contact_free=bool(info.get('arrive_dest') and not contacts),
                       any_contact=contacts,pedestrian_contact=ped_contact,out_of_road=bool(info.get('out_of_road')),duration_s=rows*dt,
                       waiting_s=wait,physical_standstill_s=stand,near_fraction=near/(rows*dt),travel_m=travel,
                       final_goal_distance_m=math.dist(ego.position,route[-1]),mean_controller_wall_s=float(np.mean(wall)),p95_controller_wall_s=float(np.percentile(wall,95)),
                       queries=len(queries),samples=samples,steps=rows)
        summary['outside_walkable_fraction']=outside_s/(rows*dt)
        (out/'vlm_queries.json').write_text(json.dumps(queries,indent=2)+'\n')
        print(json.dumps(summary),flush=True)
    finally:
        if writer is not None:writer.close()
        if env is not None:env.close()
        summary['wall_seconds']=time.monotonic()-started
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--map',required=True);p.add_argument('--width',choices=['narrow','wide'],default='wide');p.add_argument('--pedestrians',type=int,default=5);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--method',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--stage',default='development');p.add_argument('--collect',action='store_true');p.add_argument('--video',action='store_true');p.add_argument('--server',default='http://127.0.0.1:18761');a=p.parse_args()
    if os.environ.get('PYTHONHASHSEED')!=str(a.seed):
        os.execve(sys.executable,[sys.executable,*sys.argv],dict(os.environ,PYTHONHASHSEED=str(a.seed),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2'))
    run(a)
