import json,math,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'research'),str(ROOT/'src')]
from local_planner import LocalPlanner

def planner():
    c=json.loads((ROOT/'configs/classical_frozen_20261102.json').read_text())
    return LocalPlanner([[x,0] for x in np.arange(0,31,.1)],c,box(-2,-2,32,2),dict(length=1.5,width=1.,wheelbase=2.81,max_steer=math.pi/3))

def test_region_checks_entire_footprint():
    p=planner();poses=np.array([[[0,1.8,0]],[[0,0,0]]])
    assert p.region_valid(poses).tolist()==[False,True]

def test_all_candidates_blocked_stops():
    p=planner();state=dict(position=[0,0],heading=0.,speed=0.)
    d=p.evaluate(state,[],[[0,0,0,4,4,0,0]])
    action=p.decision(d);assert action['speed_cap_m_s']==0

def test_free_route_moves_and_respects_slew():
    p=planner();state=dict(position=[0,0],heading=0.,speed=0.)
    for method in ('lattice','mppi'):
        d=p.evaluate(state,[],[],method);a=p.decision(d)
        assert a['speed_cap_m_s']>0 and abs(a['steering'])<=.15+1e-9
