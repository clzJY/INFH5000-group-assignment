import math
import pytest
from streetscape_refinement.controller import Body, box_separation, predict_path, IntentGovernor


def test_native_square_is_larger_than_declared_pedestrian_radius():
    ego = Body((0,0),0,1.5,1.)
    pedestrian = Body((1.3,0),0,1.,1.)
    assert box_separation(ego,pedestrian) == pytest.approx(.05)
    # RADIUS=.35 would overstate the forward gap by .15 m.
    assert math.dist(ego.position,pedestrian.position)-.75-.35 == pytest.approx(.2)


def test_rotated_boxes_and_translation_invariance():
    a=Body((0,0),0,2,1);b=Body((0,1.6),0,2,1)
    assert box_separation(a,b) == pytest.approx(.6)
    rotated=Body((0,1.6),math.pi/2,2,1)
    assert box_separation(a,rotated) == pytest.approx(.1)
    assert box_separation(Body((4,8),0,2,1),Body((4,9.6),math.pi/2,2,1)) == pytest.approx(.1)


def test_turning_avoids_straight_line_false_alarm():
    ego=Body((0,0),0,1.5,1);ped=Body((4,0),0,1,1)
    straight=predict_path(ego,2,2,0,2,.1,1.5,2)
    turning=predict_path(ego,2,2,.5,2,.1,1.5,2)
    assert min(box_separation(e,ped) for _,e in straight)<0
    assert min(box_separation(e,ped) for _,e in turning)>.25


def test_acceleration_and_braking_prediction_reachable_from_rest():
    body=Body((0,0),0,1.5,1)
    path=predict_path(body,0,2,0,1,.1,1,2)
    assert path[-1][1].position[0] == pytest.approx(.5)
    stopped=predict_path(body,2,0,0,2,.1,1,2)
    assert stopped[-1][1].position[0] == pytest.approx(1.)


def test_crossing_interaction_is_time_aligned():
    ego=Body((0,0),0,1.5,1)
    path=predict_path(ego,2,2,0,2,.1,1.5,2)
    crossing=Body((2,2),0,1,1,(0,-2))
    risks=[box_separation(e,Body((2,2-2*t),0,1,1)) for t,e in path]
    assert min(risks)<0
    # The same spatial crossing at a different time can be clear.
    assert min(box_separation(e,Body((2,8-2*t),0,1,1)) for t,e in path)>.25
