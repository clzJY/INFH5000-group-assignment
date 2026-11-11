import json
import math
from pathlib import Path
import numpy as np
import pytest
from streetscape_baselines.geometry import gaps
from streetscape_baselines.controller import Controller
from streetscape_route.controller import Body,box_separation

CONFIG=json.loads((Path(__file__).resolve().parents[1]/'configs/classical_development.json').read_text())
ROUTE=[[float(x),0.] for x in np.arange(0,50,.1)]


def test_batched_geometry_matches_independent_scalar_rectangles():
    rng=np.random.default_rng(45)
    poses=rng.normal(size=(5,7,3))*3
    bodies=np.c_[rng.normal(size=(8,3))*3,rng.uniform(.4,2,(8,2)),rng.normal(size=(8,2))]
    times=np.arange(7)*.1
    result=gaps(poses,1.5,1.,bodies,times,True)
    for i in range(5):
        for j in range(7):
            for k,b in enumerate(bodies):
                a=Body(tuple(poses[i,j,:2]),poses[i,j,2],1.5,1.)
                other=Body(tuple(b[:2]+times[j]*b[5:7]),b[2],b[3],b[4])
                assert result[i,j,k]==pytest.approx(box_separation(a,other),abs=1e-10)


def test_zero_velocity_forecast_ablation_is_exact():
    ego={'position':[0.,0.],'heading':0.,'speed':2.}
    people=[[4.,1.5,0.,1.,1.,0.,0.]]
    a=Controller(ROUTE,CONFIG).update('forecast',ego,people,[],.1)
    b=Controller(ROUTE,CONFIG).update('forecast_static',ego,people,[],.1)
    assert a['speed_cap_m_s']==b['speed_cap_m_s']
    assert a['candidates']==b['candidates']


def test_all_methods_share_steering_and_limits_without_obstacles():
    ego={'position':[0.,0.],'heading':0.,'speed':1.}
    for method in ('pp','rpp','distance','forecast_static','forecast','dwa'):
        r=Controller(ROUTE,CONFIG).update(method,ego,[],[],.1)
        assert abs(r['steering'])<1e-10
        assert 0<r['speed_cap_m_s']<=CONFIG['tracking']['max_speed_m_s']


def test_static_guard_is_shared_including_unregulated_tracker():
    ego={'position':[0.,0.],'heading':0.,'speed':2.}
    obstacle=[[2.,0.,0.,1.,1.,0.,0.]]
    for method in ('pp','rpp','distance','forecast_static','forecast','dwa'):
        r=Controller(ROUTE,CONFIG).update(method,ego,[],obstacle,.1)
        assert r['speed_cap_m_s']==0


def test_moving_away_person_does_not_trigger_fixed_occupancy_stop():
    ego={'position':[0.,0.],'heading':0.,'speed':2.}
    people=[[3.,0.,0.,1.,1.,3.,0.]]
    dynamic=Controller(ROUTE,CONFIG).update('forecast',ego,people,[],.1)
    static=Controller(ROUTE,CONFIG).update('forecast_static',ego,people,[],.1)
    assert dynamic['speed_cap_m_s']>static['speed_cap_m_s']


def test_dwa_commands_respect_shared_steering_slew():
    ego={'position':[0.,-1.],'heading':.3,'speed':1.}
    controller=Controller(ROUTE,CONFIG)
    r=controller.update('dwa',ego,[],[],.1)
    assert abs(r['steering'])<=CONFIG['dwa']['steering_rate_per_s']*.1+1e-10
