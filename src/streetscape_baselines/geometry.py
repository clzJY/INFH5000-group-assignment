"""Batched exact planar separation of disjoint oriented rectangles.

Signed SAT penetration is used when overlapping. This is planar native-box
geometry, not rendered mesh distance or a collision-free continuous-time proof.
"""
import numpy as np


def gaps(poses, length, width, bodies, times, moving=True):
    """poses: N,T,3; bodies: M,7 [x,y,heading,length,width,vx,vy]."""
    poses=np.asarray(poses,dtype=float);bodies=np.asarray(bodies,dtype=float)
    if len(bodies)==0:return np.empty((*poses.shape[:2],0))
    times=np.asarray(times,dtype=float)
    ce=np.cos(poses[...,2])[...,None];se=np.sin(poses[...,2])[...,None]
    cp=np.cos(bodies[:,2])[None,None,:];sp=np.sin(bodies[:,2])[None,None,:]
    px=bodies[:,0][None,None,:]+(times[None,:,None]*bodies[:,5] if moving else 0)
    py=bodies[:,1][None,None,:]+(times[None,:,None]*bodies[:,6] if moving else 0)
    dx=px-poses[...,0,None];dy=py-poses[...,1,None]
    a=length/2;b=width/2;c=bodies[:,3][None,None,:]/2;d=bodies[:,4][None,None,:]/2
    dot=ce*cp+se*sp;cross=ce*sp-se*cp
    sat=np.maximum.reduce([np.abs(dx*ce+dy*se)-a-c*np.abs(dot)-d*np.abs(cross),
        np.abs(-dx*se+dy*ce)-b-c*np.abs(cross)-d*np.abs(dot),
        np.abs(dx*cp+dy*sp)-c-a*np.abs(dot)-b*np.abs(cross),
        np.abs(-dx*sp+dy*cp)-d-a*np.abs(cross)-b*np.abs(dot)])
    exact=np.full_like(sat,np.inf)
    for u,v in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        # Ego vertices to other rectangle.
        xx=-dx+u*a*ce-v*b*se;yy=-dy+u*a*se+v*b*ce
        value=np.hypot(np.maximum(0,np.abs(xx*cp+yy*sp)-c),np.maximum(0,np.abs(-xx*sp+yy*cp)-d))
        exact=np.minimum(exact,value)
        # Other vertices to ego rectangle.
        xx=dx+u*c*cp-v*d*sp;yy=dy+u*c*sp+v*d*cp
        value=np.hypot(np.maximum(0,np.abs(xx*ce+yy*se)-a),np.maximum(0,np.abs(-xx*se+yy*ce)-b))
        exact=np.minimum(exact,value)
    return np.where(sat<=0,sat,exact)


def reachable_bodies(position, speed, horizon, accel, length, width, bodies, extra=0.):
    """Safe broad phase under the declared finite-horizon motion model."""
    arr=np.asarray(bodies,dtype=float).reshape(-1,7)
    if not len(arr):return arr
    distance=np.linalg.norm(arr[:,:2]-np.asarray(position),axis=1)
    reach=horizon*(abs(speed)+accel*horizon+np.linalg.norm(arr[:,5:7],axis=1))
    radius=np.hypot(length,width)/2+np.hypot(arr[:,3],arr[:,4])/2
    return arr[distance<=reach+radius+extra]
