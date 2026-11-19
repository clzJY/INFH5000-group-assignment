"""RGB-plus-local-map visual prompt, with no oracle outcome labels in the image."""
import math
import numpy as np
from PIL import Image,ImageDraw

PROMPT='Navigate to the inspection point along the blue route. Avoid pedestrians and street furniture; remain on the sidewalk or crosswalk. The left panel is the robot camera. The right panel is a privileged local map, not camera perception. White is walkable; grey is not. Black boxes are street furniture; orange boxes are people. Choose a labelled candidate path A,B,C,D,E, or F to wait. Reply with one letter only.'
COLORS=['#d43737','#ec9a12','#109535','#3279ce','#9445ce','#777777']

def compose(rgb,ego,route,people,statics,data,region,blank_rgb=False,blank_all=False):
    rgb=Image.fromarray(np.asarray(rgb,dtype=np.uint8)).resize((320,240))
    if blank_rgb:rgb=Image.new('RGB',(320,240),(128,128,128))
    panel=Image.new('RGB',(320,320),'#888888');draw=ImageDraw.Draw(panel)
    pos=np.asarray(ego['position']);h=ego['heading'];rot=np.array([[math.cos(h),math.sin(h)],[-math.sin(h),math.cos(h)]])
    def xy(points):
        pts=(np.asarray(points)-pos)@rot.T
        return [(float(160-q[1]*18),float(275-q[0]*18)) for q in pts]
    geoms=region.geoms if hasattr(region,'geoms') else [region]
    for p in geoms:
        if p.geom_type=='Polygon':
            draw.polygon(xy(p.exterior.coords),fill='#eeeeee')
            for hole in p.interiors:draw.polygon(xy(hole.coords),fill='#888888')
    if len(route)>1:draw.line(xy(route),fill='#79b4ff',width=2)
    for bodies,color in ((statics,'#252525'),(people,'#dd8400')):
        for x,y,theta,l,w,*_ in bodies:
            v=np.array([[a*l/2,b*w/2] for a,b in ((-1,-1),(-1,1),(1,1),(1,-1))]);c,s=math.cos(theta),math.sin(theta)
            v=v@np.array([[c,s],[-s,c]])+np.array([x,y]);draw.polygon(xy(v),fill=color)
    for i,path in enumerate(data['poses'][:5]):
        coords=xy(path[:,:2]);draw.line(coords,fill=COLORS[i],width=2);draw.text(coords[-1],chr(65+i),fill=COLORS[i])
    draw.ellipse((155,270,165,280),fill='blue');draw.text((5,5),'F: WAIT',fill='black')
    canvas=Image.new('RGB',(640,320),'white');canvas.paste(rgb,(0,40));canvas.paste(panel,(320,0))
    if blank_all:canvas=Image.new('RGB',canvas.size,(128,128,128))
    return canvas
