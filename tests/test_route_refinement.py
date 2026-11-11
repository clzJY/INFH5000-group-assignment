import json
import math
from pathlib import Path
import pytest
from streetscape_route.navigation import RouteGovernor
from streetscape_route.controller import Body, IntentGovernor, box_separation

CFG=json.loads((Path(__file__).resolve().parents[1]/'configs/route_development.json').read_text())


def governor(route):
    return RouteGovernor(route,CFG['route_governor'])


def test_on_route_policy_action_is_preserved():
    g=governor([(i*.1,0.) for i in range(300)])
    action,diagnostic=g.action((0,0),0,2,[0,1],2.81,math.pi/3)
    assert action==[0,1] and not diagnostic['active']


def test_negative_throttle_stall_corrected_only_away_from_goal():
    route=[(i*.1,0.) for i in range(300)]
    g=governor(route)
    action,d=g.action((0,0),0,0,[0,-1],2.81,math.pi/3)
    assert action[1]>0 and 'brake_stall_risk' in d['reasons']
    g=governor(route);g.index=295
    action,d=g.action((29.5,0),0,0,[0,-1],2.81,math.pi/3)
    assert action==[0,-1] and not d['active']


def test_route_prediction_bends_before_a_crossing():
    route=[(i*.1,0.) for i in range(31)]+[(3.,i*.1) for i in range(1,101)]
    g=governor(route);g.index=20
    path=g.predict(Body((2.,0.),0,1.5,1),2,2,CFG['refinement'],2.81,math.pi/3)
    assert path[-1][1].position[1]>.5
    assert path[-1][1].heading>0


def test_stop_is_not_automatically_selected_if_person_will_walk_into_it():
    c=dict(CFG['refinement']);c['cruise_speed_m_s']=3.
    shield=IntentGovernor(c,True)
    ego=Body((0,0),0,1.5,1.)
    # Construct known candidate trajectories to isolate the decision rule:
    # moving clears the pedestrian; staying is struck by an approaching person.
    def predicted(body,speed,target,settings):
        return [(0.,body),(1.,Body((target*.4,0),0,1.5,1.))]
    ped=Body((-1.6,0),0,1,1,(1.6,0))
    d=shield.update(ego,[ped],[0,1],0,0,.1,predicted)
    assert d['speed_cap_m_s']>0
    assert d['state']!='WAIT'
    assert d['reason']=='least_predicted_overlap' and d['no_buffer_feasible']


def test_first_sample_overlap_is_reported_as_no_feasible_buffer():
    shield=IntentGovernor(CFG['refinement'],True)
    ego=Body((0,0),0,1.5,1.)
    d=shield.update(ego,[Body((0,0),0,1,1)],[0,1],0,0,.1)
    assert d['no_buffer_feasible']
    assert d['state']=='WAIT'


def test_diagonal_box_gap_is_euclidean_not_sat_lower_bound():
    a=Body((0,0),0,1,1);b=Body((2,2),0,1,1)
    assert box_separation(a,b)==pytest.approx(math.sqrt(2))
