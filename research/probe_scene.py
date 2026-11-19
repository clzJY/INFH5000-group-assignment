"""Read native geometry and RGB for a fresh scene; never alters robot state."""
import argparse, json, math, os, sys, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'third_party/metaurban'),str(ROOT/'third_party/metaurban/metaurban/orca_algo/build')]
from streetscape_route.runtime import _make_env

def polygons(env):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    shapes=[]
    for name in ('sidewalks','crosswalks','sidewalks_near_road','sidewalks_near_road_buffer'):
        for entry in getattr(env.current_map,name).values():
            points=np.asarray(entry['polygon'],dtype=float).reshape(-1,2)
            if len(points)>=3:
                p=Polygon(points)
                if not p.is_valid:p=p.buffer(0)
                if not p.is_empty:shapes.append(p)
    return unary_union(shapes)

def main():
    p=argparse.ArgumentParser();p.add_argument('--map',required=True);p.add_argument('--seed',type=int,default=1100);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);out=a.output.resolve()
    c=json.loads((ROOT/'configs/classical_frozen_20261102.json').read_text());c['env_config'].update(map=a.map,num_scenarios=10000,object_density=.1,horizon=900)
    c['render'].update(width=640,height=360)
    (out/'metaurban').symlink_to(ROOT/'third_party/metaurban/metaurban',target_is_directory=True)
    os.chdir(out);t=time.monotonic();env=_make_env(c,5,True)
    try:
        obs,info=env.reset(seed=a.seed)
        from PIL import Image
        from shapely.geometry import Point,LineString,mapping
        image=np.asarray(env.engine.get_sensor('rgb_camera').perceive(to_float=False,new_parent_node=env.agent.origin,position=c['render']['position'],hpr=c['render']['hpr']))[...,::-1];print('IMAGE',image.shape,flush=True)
        if image.ndim==4:image=image[:,:,:,-1]
        if image.max()<=1:image=(image*255).astype('uint8')
        Image.fromarray(image.astype('uint8')).save('native_rgb.png')
        route=np.asarray(env.agent.navigation.position_list)
        free=polygons(env)
        result=dict(map=a.map,seed=a.seed,sidewalk_type=env.current_map.sidewalk_type,
                    route=route.tolist(),route_length=float(env.agent.navigation.reference_trajectory.length),
                    ego_length=env.agent.LENGTH,ego_width=env.agent.WIDTH,
                    walkable_area=free.area,route_samples_inside=sum(free.buffer(.1).covers(Point(x)) for x in route),route_samples=len(route),
                    walkable_geojson=mapping(free),elapsed_s=time.monotonic()-t)
        Path('scene.json').write_text(json.dumps(result)+'\n')
        print({k:v for k,v in result.items() if k not in ('route','walkable_geojson')},flush=True)
    finally:env.close()
if __name__=='__main__':main()
