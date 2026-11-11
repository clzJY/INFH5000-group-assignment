#!/usr/bin/env python3
"""Finite real-simulator gate: repeated scenes, policy rollout, video, braking."""
import argparse
import copy
from dataclasses import asdict
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from urban_service.action_adapter import apply_speed_cap
from urban_service.controller import PoseTracker
from urban_service.provenance import dump_json, fingerprint
from urban_service.runtime import _make_env, run_episode, snapshot


def motion_trace(path):
    rows = [json.loads(s) for s in (path / "steps.jsonl").read_text().splitlines()]
    return [[*[round(v, 5) for v in row["ego"]["position"]],
             *[round(v, 5) for v in row["executed_action"]]] for row in rows]


def brake_gate(config, output):
    cfg = copy.deepcopy(config)
    cfg["environment"] = "static"
    cfg["inspection_hold_s"] = 0
    # Native AssetManager divides by object_density; a small positive density
    # keeps the braking fixture valid while avoiding dense street furniture.
    cfg["env_config"].update(object_density=0.01, spawn_deliveryrobot_num=0, horizon=120)
    cfg["env_config"]["vehicle_config"]["enable_reverse"] = False
    env = None
    old = Path.cwd()
    output.mkdir()
    try:
        os.chdir(output)
        env = _make_env(cfg, 0, False)
        env.reset(seed=900)
        dt = env.config["physics_world_step_size"] * env.config["decision_repeat"]
        tracker = PoseTracker()
        ego, _ = snapshot(env, tracker, dt)
        rows = []
        for step in range(60):
            speed = math.hypot(*ego.velocity)
            action = (0.0, 0.5) if step < 20 else apply_speed_cap((0.0, 0.5),
                     {"state": "WAIT", "speed_cap_m_s": 0.0}, speed)
            env.agent._urban_yield_hold = bool(config.get("low_speed_hold_brake", False) and step >= 20)
            _, _, terminated, truncated, info = env.step(list(action))
            ego, _ = snapshot(env, tracker, dt)
            forward_speed = sum(v * float(h) for v, h in zip(ego.velocity, env.agent.heading))
            rows.append(dict(step=step, ego=asdict(ego), speed_m_s=math.hypot(*ego.velocity),
                             forward_speed_m_s=forward_speed, action=action))
            if terminated or truncated:
                break
        accelerated = len(rows) > 20 and max(r["speed_m_s"] for r in rows[:20]) > 0.2
        stopped = len(rows) >= 40 and max(r["speed_m_s"] for r in rows[-5:]) < 0.1
        no_reverse = all(r["forward_speed_m_s"] > -0.1 for r in rows[20:])
        result = dict(passed=accelerated and stopped and no_reverse, accelerated=accelerated,
                      stopped=stopped, no_reverse=no_reverse, trace=rows)
        dump_json(output / "brake_gate.json", result)
        return result["passed"]
    finally:
        if env:
            env.close()
        os.chdir(old)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=ROOT / "configs/evaluation.json")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    config = json.loads(args.config.read_text())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = dict(scope="real_simulator_gate", passed=False,
                  evaluation_config_sha256=fingerprint(config),
                  time=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat())
    try:
        # Each rollout in an isolated interpreter, including the recording path.
        import subprocess
        cfg = copy.deepcopy(config)
        cfg["env_config"]["horizon"] = 80
        cfg["inspection_hold_s"] = 0
        dump_json(output / "gate_config.json", cfg)
        for label, method, record in (("repeat_a", "baseline", True), ("repeat_b", "baseline", False), ("modified", "predictive", True)):
            cmd = [sys.executable, str(ROOT / "scripts/run_episode.py"), "--config", str(output / "gate_config.json"),
                   "--seed", "900", "--pedestrians", str(config["densities"]["low"]),
                   "--method", method, "--output", str(output / label)]
            if record:
                cmd.append("--record")
            subprocess.run(cmd, check=True)
        a, b = [json.loads((output / label / "summary.json").read_text()) for label in ("repeat_a", "repeat_b")]
        result["initial_scene_repeatable"] = a["initial_scene_fingerprint"] == b["initial_scene_fingerprint"]
        result["trajectory_repeatable_to_1e5"] = motion_trace(output / "repeat_a") == motion_trace(output / "repeat_b")
        result["has_pedestrians"] = a["actual_initial_pedestrians"] == config["densities"]["low"]
        import imageio.v2 as imageio
        videos = []
        for label in ("repeat_a", "modified"):
            with imageio.get_reader(str(output / label / "rollout.mp4")) as reader:
                frame = reader.get_data(0)
                videos.append(frame.ndim == 3 and float(frame.std()) > 1.0)
        result["videos_decodable_nonuniform"] = all(videos)
        # Braking uses the same pinned wheel embodiment and action adapter.
        sys.path[:0] = [str(ROOT / "third_party/metaurban/metaurban/orca_algo/build"), str(ROOT / "third_party/metaurban")]
        result["braking_passed"] = brake_gate(config, output / "braking")
        result["passed"] = all(result[k] for k in ("initial_scene_repeatable", "trajectory_repeatable_to_1e5", "has_pedestrians", "videos_decodable_nonuniform", "braking_passed"))
        result["note"] = "Finite integration gate; task success and research improvement must be evaluated separately."
    finally:
        dump_json(output / "gate_report.json", result)
    if not result["passed"]:
        sys.exit(1)
    print("REAL_SIMULATOR_GATE_PASSED")


if __name__ == "__main__":
    main()
