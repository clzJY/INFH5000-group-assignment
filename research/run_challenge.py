"""Controlled newly placed street-furniture blockage after reference planning.

The existing native TestObject is relocated only during task initialisation.
Robot state is never reset/teleported after native env.reset. All methods receive
the same post-placement scene; the fixed reference route is not recomputed.
"""
import json,math,sys
import numpy as np
import run_native as native

_make=native._make_env;_reference=native.reference_route;current={}

def make(*args,**kwargs):
    env=_make(*args,**kwargs);current['env']=env;return env

def route(original,region,statics,*args,**kwargs):
    points,receipt=_reference(original,region,statics,*args,**kwargs)
    env=current['env']
    from metaurban.component.static_object.test_new_object import TestObject
    objects=list(env.engine.get_objects(lambda obj:isinstance(obj,TestObject)).values())
    eligible=[o for o in objects if .2<float(o.WIDTH)<1.5 and .2<float(o.LENGTH)<2.]
    if not eligible:
        receipt['challenge']={'status':'no_suitable_native_object'};return points,receipt
    obj=min(eligible,key=lambda o:(float(o.LENGTH)*float(o.WIDTH),float(o.position[0]),float(o.position[1])))
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    index=min(len(points)-2,int(np.searchsorted(arc,20.)))
    tangent=points[index+1]-points[max(0,index-1)];tangent/=max(np.linalg.norm(tangent),1e-6);normal=np.array([-tangent[1],tangent[0]])
    side=1 if env.engine.global_random_seed%2==0 else -1
    target=points[index]+side*.35*normal
    original_position=[float(v) for v in obj.position[:2]]
    obj.set_position(target);obj.set_heading_theta(math.atan2(tangent[1],tangent[0]))
    receipt['challenge']=dict(status='placed',original_position=original_position,position=target.tolist(),length=float(obj.LENGTH),width=float(obj.WIDTH),side=side,reference_distance_m=float(arc[index]))
    print('CONTROLLED_BLOCKAGE',receipt['challenge'],flush=True)
    return points,receipt

native._make_env=make;native.reference_route=route
if __name__=='__main__':
    # Execute the unchanged runner entry point while preserving the patched module.
    import os
    seed=sys.argv[sys.argv.index('--seed')+1]
    if os.environ.get('PYTHONHASHSEED')!=seed:
        os.execve(sys.executable,[sys.executable,*sys.argv],dict(os.environ,PYTHONHASHSEED=seed,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2'))
    source=open(native.__file__).read();entry=source[source.index("if __name__=='__main__':"):]
    exec(compile(entry,native.__file__,'exec'),dict(native.__dict__,__name__='__main__'))
