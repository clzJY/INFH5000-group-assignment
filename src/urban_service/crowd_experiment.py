"""Official CrowdNav closed-loop simulator, with isolated speed-layer adapters."""
import configparser
from dataclasses import asdict, replace
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time

from .controller import Actor, YieldConfig, YieldController, closest_approach
from .provenance import dump_json, fingerprint, sha256

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "third_party/CrowdNav"
CROWD_COMMIT = "20d678085c06831e658a65b9e20c8bb6f6ecdc10"
RVO_COMMIT = "c2c46ba8d59556aa10faf03479293236efea154d"


def load_backend():
    # Only the Gym import namespace/registration is bridged. The upstream
    # simulator's reset, step, scenarios, rewards, and terminal rules are intact.
    import gymnasium
    import gymnasium.envs
    import gymnasium.envs.registration
    sys.modules.setdefault("gym", gymnasium)
    sys.modules.setdefault("gym.envs", gymnasium.envs)
    sys.modules.setdefault("gym.envs.registration", gymnasium.envs.registration)
    if str(UPSTREAM) not in sys.path:
        sys.path.insert(0, str(UPSTREAM))
    from crowd_sim.envs.crowd_sim import CrowdSim
    from crowd_sim.envs.policy.orca import ORCA
    from crowd_sim.envs.utils.robot import Robot
    from crowd_sim.envs.utils.action import ActionXY
    from crowd_sim.envs.utils.info import Collision, ReachGoal, Timeout
    return CrowdSim, ORCA, Robot, ActionXY, Collision, ReachGoal, Timeout


def make_env(config, scenario):
    CrowdSim, ORCA, Robot, *_ = load_backend()
    ini = configparser.RawConfigParser()
    ini.read(UPSTREAM / "crowd_nav/configs/env.config")
    ini.set("sim", "test_sim", scenario)
    ini.set("sim", "human_num", str(config["human_num"]))
    ini.set("robot", "visible", str(config["robot_visible"]).lower())
    env = CrowdSim()
    env.configure(ini)
    robot = Robot(ini, "robot")
    robot.set_policy(ORCA())
    env.set_robot(robot)
    return env


def state(env):
    def convert(agent, name, kind):
        return Actor(name, (float(agent.px), float(agent.py)),
                     (float(agent.vx), float(agent.vy)), float(agent.radius), kind)
    return convert(env.robot, "robot", "ego"), [convert(h, f"human_{i}", "pedestrian") for i, h in enumerate(env.humans)]


def exposure_interval(p, w, radius, dt):
    """Exact interval inside a circle for constant relative velocity in a step."""
    a = sum(v * v for v in w)
    b = 2 * sum(x * y for x, y in zip(p, w))
    c = sum(v * v for v in p) - radius * radius
    if a < 1e-15:
        return (0.0, dt) if c < 0 else None
    discr = b * b - 4 * a * c
    if discr <= 0:
        return None
    lo, hi = (-b - math.sqrt(discr)) / (2 * a), (-b + math.sqrt(discr)) / (2 * a)
    lo, hi = max(0.0, lo), min(dt, hi)
    return (lo, hi) if hi > lo else None


def union_duration(intervals):
    intervals = sorted(x for x in intervals if x is not None)
    total = 0.0
    hi = 0.0
    for a, b in intervals:
        total += max(0.0, b - max(a, hi))
        hi = max(hi, b)
    return total


def run_episode(config, scenario, method, case_id, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    env = make_env(config, scenario)
    *_, ActionXY, Collision, ReachGoal, Timeout = load_backend()
    observation = env.reset("test", case_id)
    ego, people = state(env)
    initial = dict(ego=asdict(ego), people=[asdict(p) for p in people],
                   goals=[[float(h.gx), float(h.gy)] for h in env.humans])
    dump_json(output / "initial_state.json", initial)
    controller = YieldController(YieldConfig(mode=method if method in ("baseline","distance","predictive") else "baseline", **config["controller"]))
    _, ORCA, _, *_ = load_backend()
    margin_policy = ORCA()
    margin_policy.time_step = float(env.time_step)
    previous_margin = 0.0
    dt = float(env.time_step)
    path = exposure = waiting = 0.0
    min_clearance = math.inf
    overlap = False
    rows = []
    trace = []
    done = False
    info = None
    while not done:
        raw = env.robot.act(observation)
        if method in ("fixed_margin", "adaptive_margin"):
            from crowd_sim.envs.utils.state import JointState
            b = config["buffer"]
            goal_delta = (env.robot.gx-ego.position[0],env.robot.gy-ego.position[1])
            norm = math.hypot(*goal_delta)
            desired_velocity = tuple(v/max(1.0,norm) for v in goal_delta)
            risk = min(closest_approach(replace(ego,velocity=desired_velocity),p,b["horizon_s"])[1] for p in people)
            target = b["fixed_m"] if method=="fixed_margin" else b["max_m"]*max(0.0,min(1.0,(b["trigger_clearance_m"]-risk)/b["trigger_clearance_m"]))
            margin = target if method=="fixed_margin" else max(target,previous_margin-b["release_rate_m_s"]*dt)
            previous_margin = margin
            # Apply clearance inside ORCA's velocity optimization, rather than
            # multiplying its already-solved velocity and invalidating constraints.
            margin_policy.safety_space = margin
            margin_policy.sim = None
            action = margin_policy.predict(JointState(env.robot.get_full_state(),observation))
            decision = dict(state="BUFFER",margin_m=margin,risk_clearance_m=risk)
        else:
            # Development-only post-hoc speed interventions, retained as failures.
            decision = controller.update(replace(ego, velocity=(float(raw.vx), float(raw.vy))), people, dt)
            speed = math.hypot(raw.vx, raw.vy)
            factor = 1.0
            if decision["state"] != "PASS" and speed > 1e-12:
                factor = min(1.0, decision["speed_cap_m_s"] / speed)
            action = ActionXY(float(raw.vx * factor), float(raw.vy * factor))
        before_ego, before_people = ego, people
        observation, reward, done, info = env.step(action)
        ego, people = state(env)
        path += math.dist(before_ego.position, ego.position)
        waiting += dt if math.hypot(*ego.velocity) < 0.05 else 0.0
        actual_ego = replace(before_ego, velocity=tuple((y-x)/dt for x,y in zip(before_ego.position,ego.position)))
        intervals = []
        step_min = math.inf
        for old, new in zip(before_people, people):
            actual_person = replace(old, velocity=tuple((y-x)/dt for x,y in zip(old.position,new.position)))
            _, d = closest_approach(actual_ego, actual_person, dt)
            step_min = min(step_min, d)
            relative_p = tuple(y-x for x,y in zip(actual_ego.position,actual_person.position))
            relative_v = tuple(y-x for x,y in zip(actual_ego.velocity,actual_person.velocity))
            intervals.append(exposure_interval(relative_p,relative_v,actual_ego.radius+actual_person.radius+config["near_clearance_m"],dt))
        exposure += union_duration(intervals)
        min_clearance = min(min_clearance, step_min)
        overlap |= step_min < -1e-8
        row = dict(step=len(rows),time_s=float(env.global_time),ego=asdict(ego),people=[asdict(p) for p in people],
                   raw_action=[float(raw.vx),float(raw.vy)],executed_action=[action.vx,action.vy],
                   decision=decision,step_min_clearance_m=step_min,native_info=type(info).__name__)
        rows.append(row)
        trace.append([ego.position,[[p.position,p.velocity] for p in people]])
        if len(rows) > 200:
            raise RuntimeError("Unexpected nontermination of native 25-second episode")
    (output / "steps.jsonl").write_text("".join(json.dumps(row,allow_nan=False)+"\n" for row in rows))
    result = dict(status="complete",backend="official_CrowdNav_CrowdSim",scenario=scenario,method=method,case_id=case_id,
        simulator_rng_seed=1000+case_id,config_sha256=fingerprint(config),initial_fingerprint=fingerprint(initial),
        outcome=type(info).__name__,success=isinstance(info,ReachGoal),native_collision=isinstance(info,Collision),
        timeout=isinstance(info,Timeout),swept_overlap=overlap,
        collision_free_success=isinstance(info,ReachGoal) and not overlap,
        min_clearance_m=min_clearance,near_exposure_s=exposure,near_time_fraction=exposure/env.global_time,
        duration_s=float(env.global_time),path_length_m=path,wait_time_s=waiting,
        goal_error_m=math.dist(ego.position,(env.robot.gx,env.robot.gy)),steps=len(rows),
        wall_seconds=time.monotonic()-started,dt_s=dt,trace_sha256=fingerprint(trace),
        crowdnav_commit=CROWD_COMMIT,rvo2_commit=RVO_COMMIT,
        runner_sha256=sha256(Path(__file__)),controller_sha256=sha256(Path(__file__).with_name("controller.py")))
    dump_json(output / "summary.json",result)
    return result


def run_campaign(config, output, split):
    if set(config["development_cases"]) & set(config["test_cases"]):
        raise ValueError("Development/test case leakage")
    if split == "test":
        if config.get("stage") != "frozen":
            raise ValueError("Freeze the final protocol before test execution")
        if config.get("runner_sha256") != sha256(Path(__file__)):
            raise ValueError("Frozen runner changed")
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    dump_json(output / "protocol.json",config)
    results=[]
    for scenario in config["scenarios"]:
        for case in config[f"{split}_cases"]:
            for method in config.get("methods",("baseline","distance","predictive")):
                result=run_episode(config,scenario,method,case,output/f"{scenario}_{case}_{method}")
                results.append(result)
                print(f"{scenario} case={case} {method}: {result['outcome']} clearance={result['min_clearance_m']:.3f} t={result['duration_s']:.2f}",flush=True)
    for scenario in config["scenarios"]:
        for case in config[f"{split}_cases"]:
            paired=[r for r in results if r["scenario"]==scenario and r["case_id"]==case]
            if len({r["initial_fingerprint"] for r in paired}) != 1:
                raise RuntimeError("Unmatched initial conditions")
    dump_json(output/"results.json",results)
    return results
