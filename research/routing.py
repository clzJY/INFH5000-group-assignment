"""Shared clearance-aware reference route on native walkable polygons."""
import heapq,math
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString

def reference_route(original,region,statics,radius=.78,resolution=.4):
    blocked=[]
    for x,y,h,l,w,*_ in statics:
        pts=np.array([[-l/2,-w/2],[-l/2,w/2],[l/2,w/2],[l/2,-w/2]])
        c,s=math.cos(h),math.sin(h);pts=pts@np.array([[c,s],[-s,c]])+[x,y]
        blocked.append(Polygon(pts))
    free=region
    if blocked:free=free.difference(shapely.union_all(blocked))
    safe=free.buffer(-radius)
    shapely.prepare(safe)
    xmin,ymin,xmax,ymax=region.bounds
    nx=math.ceil((xmax-xmin)/resolution)+1;ny=math.ceil((ymax-ymin)/resolution)+1
    xx,yy=np.meshgrid(xmin+np.arange(nx)*resolution,ymin+np.arange(ny)*resolution)
    mask=shapely.covers(safe,shapely.points(np.c_[xx.ravel(),yy.ravel()])).reshape(ny,nx)
    coords=np.argwhere(mask)
    if not len(coords):return np.asarray(original),dict(status='empty_eroded_region',radius=radius)
    def nearest(point):
        desired=np.array([(point[1]-ymin)/resolution,(point[0]-xmin)/resolution])
        return tuple(coords[np.argmin(np.sum((coords-desired)**2,axis=1))])
    start=nearest(original[0]);goal=nearest(original[-1]);queue=[(0.,0.,start)];dist={start:0.};parent={};found=False
    while queue:
        _,cost,node=heapq.heappop(queue)
        if cost>dist[node]+1e-9:continue
        if node==goal:found=True;break
        for dy,dx in ((0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
            q=(node[0]+dy,node[1]+dx)
            if not(0<=q[0]<ny and 0<=q[1]<nx) or not mask[q]:continue
            if dx and dy and not(mask[node[0],q[1]] and mask[q[0],node[1]]):continue
            nc=cost+math.hypot(dx,dy)
            if nc<dist.get(q,math.inf):
                dist[q]=nc;parent[q]=node;heapq.heappush(queue,(nc+math.hypot(q[0]-goal[0],q[1]-goal[1]),nc,q))
    if not found:return np.asarray(original),dict(status='disconnected',radius=radius)
    cells=[goal]
    while cells[-1]!=start:cells.append(parent[cells[-1]])
    points=np.array([[xmin+x*resolution,ymin+y*resolution] for y,x in cells[::-1]])
    # Visibility shortcutting only inside the same eroded free space.
    shortcut=[points[0]];i=0
    while i<len(points)-1:
        j=min(i+25,len(points)-1)
        while j>i+1 and not safe.covers(LineString([points[i],points[j]])):j-=1
        shortcut.append(points[j]);i=j
    points=np.vstack([original[0],shortcut,original[-1]])
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1);dense=[]
    for a,b,l in zip(points[:-1],points[1:],lengths):
        for f in np.linspace(0,1,max(2,math.ceil(l/.1)),endpoint=False):dense.append(a+(b-a)*f)
    dense.append(points[-1])
    return np.asarray(dense),dict(status='astar',radius=radius,resolution=resolution,length_m=float(lengths.sum()),start_snap_m=float(np.linalg.norm(points[1]-points[0])),goal_snap_m=float(np.linalg.norm(points[-2]-points[-1])))
