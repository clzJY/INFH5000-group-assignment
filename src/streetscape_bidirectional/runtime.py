"""Pinned MetaUrban integration. Import simulator dependencies only on real runs."""
import copy
from dataclasses import asdict, replace
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import traceback

from urban_service.action_adapter import apply_speed_cap
from streetscape_bidirectional.controller import Body, IntentGovernor
from urban_service.controller import Actor, PoseTracker, YieldConfig, YieldController
from urban_service.metrics import EpisodeMetrics
from urban_service.provenance import UPSTREAM_COMMIT, dump_json, fingerprint, sha256


def project_root():
    return Path(__file__).resolve().parents[2]


def input_errors(root, config):
    errors = []
    if config.get("upstream_commit") != UPSTREAM_COMMIT:
        errors.append("Unsupported upstream commit")
    source = root / "third_party/metaurban"
    if not (source / "metaurban/envs/sidewalk_dynamic_env.py").is_file():
        errors.append("Missing pinned upstream source")
    checkpoint = root / config["checkpoint"]
    if not checkpoint.is_file():
        errors.append("Missing pretrained checkpoint")
    elif sha256(checkpoint) != config["checkpoint_sha256"]:
        errors.append("Checkpoint SHA256 mismatch")
    assets = source / "metaurban/assets"
    if not (assets / "version.txt").is_file():
        errors.append("Missing assets/version.txt; automatic downloads are disabled")
    elif not (assets.resolve().parents[1] / "import_receipt.json").is_file():
        errors.append("Missing asset import receipt; use scripts/import_assets.py")
    if config["asset_profile"] == "full":
        if not (source / "metaurban/assets_pedestrain").is_dir():
            errors.append("Missing assets_pedestrain (upstream spelling)")
    if not list((source / "metaurban/orca_algo/build").glob("bind*.so")):
        errors.append("Missing Linux ORCA extension; build it offline first")
    return errors


def _geometry(obj, kind):
    # Ego uses its circumscribed radius; pedestrians use declared RADIUS.
    # These are navigation proxies, not mesh-exact or universally enclosing.
    if kind == "pedestrian":
        radius = float(obj.RADIUS)
    else:
        radius = math.hypot(float(obj.LENGTH), float(obj.WIDTH)) / 2
    return dict(actor_id=str(obj.id), position=[float(x) for x in obj.position[:2]],
                radius=radius, kind=kind)


def snapshot(env, tracker, dt):
    from metaurban.component.agents.pedestrian.base_pedestrian import BasePedestrian
    states = [_geometry(env.agent, "ego")]
    people = env.engine.get_objects(lambda obj: isinstance(obj, BasePedestrian))
    states += [_geometry(obj, "pedestrian") for obj in people.values()]
    actors = tracker.snapshot(states, dt)
    return actors[0], actors[1:]


def pedestrian_contact(info, pedestrian_only):
    """Native SimplePedestrian chassis uses VEHICLE, not PEDESTRIAN."""
    return bool(info.get("crash_human", False) or
                (pedestrian_only and info.get("crash_vehicle", False)))


def _make_env(config, pedestrian_count, record):
    from metaurban import SidewalkStaticMetaUrbanEnv, SidewalkDynamicMetaUrbanEnv
    from metaurban.engine.base_engine import BaseEngine
    from metaurban.engine.asset_loader import AssetLoader
    from metaurban.obs.state_obs import LidarStateObservation
    from metaurban.component.sensors.rgb_camera import RGBCamera

    if config.get("low_speed_hold_brake", False):
        from metaurban.component.delivery_robot.base_deliveryrobot import EgoDeliveryRobot
        if not getattr(EgoDeliveryRobot, "_urban_hold_installed", False):
            native_actuation = EgoDeliveryRobot._apply_throttle_brake
            def actuation_with_hold(self, throttle_brake):
                native_actuation(self, throttle_brake)
                if getattr(self, "_urban_yield_hold", False) and not self.enable_reverse and self.speed < 0.5:
                    for wheel in range(4):
                        self.system.applyEngineForce(0.0, wheel)
                        self.system.setBrake(self.config["max_brake_force"], wheel)
            EgoDeliveryRobot._apply_throttle_brake = actuation_with_hold
            EgoDeliveryRobot._urban_hold_installed = True

    # Native EGL rendering on the server, with the same Panda3D scene/physics.
    if not os.environ.get("DISPLAY"):
        from panda3d.core import loadPrcFileData
        loadPrcFileData("", "load-display p3headlessgl")
        # Upstream requests 16x floating-point MSAA, unsupported on this EGL
        # framebuffer. Disable target MSAA only; scene/physics are intact.
        from direct.filter.FilterManager import FilterManager
        if not getattr(FilterManager, "_urban_msaa_compatible", False):
            original_render = FilterManager.render_scene_into
            def render_scene_compatible(self, *args, **kwargs):
                props = kwargs.get("fbprops")
                if props is not None:
                    props.set_multisamples(0)
                return original_render(self, *args, **kwargs)
            FilterManager.render_scene_into = render_scene_compatible
            FilterManager._urban_msaa_compatible = True
        from metaurban.engine.core.pssm import PSSM
        if not getattr(PSSM, "_urban_depth_compatible", False):
            original_shadow = PSSM.create_render_buffer
            def shadow_buffer_compatible(self, width, height, depth_bits):
                return original_shadow(self, width, height, 24)
            PSSM.create_render_buffer = shadow_buffer_compatible
            PSSM._urban_depth_compatible = True

    def offline_assets(global_config):
        if not Path(AssetLoader.asset_path).is_dir() or AssetLoader.should_update_asset():
            raise RuntimeError("Missing/outdated scene assets; fetch on Mac and import offline")
    BaseEngine.try_pull_asset = staticmethod(offline_assets)
    base = SidewalkDynamicMetaUrbanEnv if config["environment"] == "dynamic" else SidewalkStaticMetaUrbanEnv

    class InspectionEnv(base):
        inspection_finished = False

        def done_function(self, vehicle_id):
            done, info = super().done_function(vehicle_id)
            hard = any(info.get(k, False) for k in ("out_of_road", "crash_building", "crash_human", "crash_vehicle", "crash_object"))
            if config["inspection_hold_s"] > 0 and info.get("arrive_dest") and not hard and not self.inspection_finished:
                done = False
            return done, info

    cfg = copy.deepcopy(config["env_config"])
    if config["environment"] == "dynamic":
        cfg["spawn_human_num"] = pedestrian_count
    cfg["agent_observation"] = LidarStateObservation
    images = bool(record or config["inspection_hold_s"] > 0)
    cfg["image_observation"] = images
    if images:
        r = config["render"]
        cfg["sensors"] = {"rgb_camera": (RGBCamera, r["width"], r["height"])}
        cfg["norm_pixel"] = False
        cfg["interface_panel"] = []
    return InspectionEnv(cfg)


def _scene_fingerprint(env, ego, people):
    geometry = []
    for obj in env.engine.get_objects().values():
        try:
            geometry.append([type(obj).__name__, [round(float(v), 6) for v in obj.position[:2]]])
        except (AttributeError, TypeError, ValueError):
            continue
    geometry.sort(key=lambda row: json.dumps(row))
    actors = sorted([[a.kind, list(a.position), a.radius] for a in [ego, *people]], key=lambda row: json.dumps(row))
    route = [[round(float(v), 6) for v in p] for p in env.agent.navigation.position_list]
    return fingerprint(dict(objects=geometry, actors=actors, planned_route=route))


def run_episode(config, method, seed, pedestrian_count, output, record=False):
    root = project_root()
    errors = input_errors(root, config)
    if errors:
        raise RuntimeError("; ".join(errors))
    if method not in ("baseline", "distance", "predictive", "governed", "intent"):
        raise ValueError("Unknown method")
    if not config["env_config"]["vehicle_config"].get("enable_reverse", False):
        raise ValueError("This explicit motion-contract ablation requires native reverse enabled")
    pedestrian_only = config.get("pedestrian_only_collision_attribution", False)
    if pedestrian_only:
        cfg = config["env_config"]
        if cfg.get("traffic_density", 0) != 0 or any(cfg.get(k, 0) for k in
            ("spawn_deliveryrobot_num", "spawn_wheelchairman_num", "spawn_edog_num", "spawn_erobot_num", "spawn_drobot_num")):
            raise ValueError("Pedestrian-only contact attribution requires all other traffic disabled")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    dump_json(output / "config.json", config)
    source = root / "third_party/metaurban"
    sys.path[:0] = [str(source / "metaurban/orca_algo/build"), str(source)]
    # Upstream resolves pedestrian paths relative to ./metaurban at import.
    # Keep per-run working files isolated while supplying its expected layout.
    (output / "metaurban").symlink_to(source / "metaurban", target_is_directory=True)
    started = time.monotonic()
    env = writer = None
    metrics = None
    result = dict(status="error", source="actual_simulator_attempt", method=method, seed=seed,
                  requested_pedestrians=pedestrian_count, config_sha256=fingerprint(config),
                  upstream_commit=UPSTREAM_COMMIT, checkpoint_sha256=config["checkpoint_sha256"])
    old_cwd = Path.cwd()
    try:
        # Keep upstream .cache and planner temporary files within this run.
        os.chdir(output)
        import numpy as np
        import torch
        from stable_baselines3 import PPO
        from stable_baselines3.common.save_util import load_from_zip_file
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.set_num_threads(4)
        env = _make_env(config, pedestrian_count, record)
        from metaurban.component.delivery_robot.base_deliveryrobot import EgoDeliveryRobot
        native_actuation = EgoDeliveryRobot._apply_throttle_brake
        def brake_override(agent, command):
            native_actuation(agent, command)
            fraction = getattr(agent, "_refinement_brake", 0.)
            if fraction > 0:
                for wheel in range(4):
                    agent.system.applyEngineForce(0., wheel)
                    agent.system.setBrake(fraction*agent.config["max_brake_force"], wheel)
        EgoDeliveryRobot._apply_throttle_brake = brake_override
        observation, info = env.reset(seed=seed)
        if env.observation_space.shape != (271,) or env.action_space.shape != (2,):
            raise RuntimeError(f"Checkpoint contract mismatch: {env.observation_space}, {env.action_space}")
        policy = PPO("MlpPolicy", env, device="cpu", n_steps=200, batch_size=200, seed=seed)
        _, parameters, _ = load_from_zip_file(str(root / config["checkpoint"]), device="cpu", load_data=False)
        policy.set_parameters(parameters, exact_match=True, device="cpu")
        dt = float(env.config["physics_world_step_size"]) * int(env.config["decision_repeat"])
        tracker = PoseTracker()
        ego, people = snapshot(env, tracker, dt)
        result.update(initial_scene_fingerprint=_scene_fingerprint(env, ego, people),
                      actual_initial_pedestrians=len(people), dt_s=dt,
                      versions={p: importlib.metadata.version(p) for p in
                                ("torch", "stable-baselines3", "numpy", "panda3d", "gymnasium")},
                      core_source_sha256={str(p.relative_to(root)): sha256(p) for package in ("urban_service", "streetscape_bidirectional") for p in (root / "src" / package).glob("*.py")})
        result["goal_position"] = [float(v) for v in env.agent.navigation.position_list[-1]]
        result["pedestrian_contact_definition"] = "native crash_human OR crash_vehicle in verified pedestrian-only traffic" if pedestrian_only else "native crash_human"
        receipt = (source / "metaurban/assets").resolve().parents[1] / "import_receipt.json"
        result["asset_import_receipt_sha256"] = sha256(receipt)
        dump_json(output / "initial_state.json", {"ego": asdict(ego), "pedestrians": [asdict(p) for p in people]})
        metrics = EpisodeMetrics(ego.position, config["near_clearance_m"])
        route = [[float(v) for v in xy] for xy in env.agent.navigation.position_list]
        route_length = float(env.agent.navigation.reference_trajectory.length)
        result.update(planned_route=route, initial_route_length_m=route_length,
                      start_goal_distance_m=math.dist(ego.position, result["goal_position"]))
        result["valid_task"] = route_length >= config["route_min_length_m"] and result["start_goal_distance_m"] >= config["route_min_length_m"]
        if not result["valid_task"]:
            result.update(status="invalid_task", invalid_reason="predeclared route/start-goal length gate; no policy steps executed")
            return result
        controller = (IntentGovernor(config["refinement"], method == "intent") if method in ("governed", "intent")
                      else YieldController(YieldConfig(mode=method, **config["controller"])))
        reached = False
        stop_elapsed = inspection_elapsed = 0.0
        inspection_complete = False
        inspection_collision = False
        navigation_result = None
        if record:
            import imageio.v2 as imageio
            writer = imageio.get_writer(str(output / "rollout.mp4"), fps=1 / dt,
                                       codec="libx264", macro_block_size=1)
        with (output / "steps.jsonl").open("w") as log:
            for step in range(int(config["env_config"]["horizon"])):
                raw, _ = policy.predict(observation, deterministic=True)
                raw = [float(v) for v in raw]
                # Constant-velocity risk uses measured speed; add a modest look-ahead
                # when the base policy requests forward motion from rest.
                speed = math.hypot(*ego.velocity)
                signed_speed = sum(float(v)*float(h) for v,h in zip(env.agent.velocity, env.agent.heading))
                nominal_speed = max(speed, config["controller"]["max_speed_m_s"] if raw[1] > 0 else 0.0)
                heading = tuple(float(v) for v in env.agent.heading)
                nominal_signed = signed_speed if abs(signed_speed) > .2 else (math.copysign(min(nominal_speed,2.),raw[1]) if abs(raw[1]) > .01 else 0.)
                predicted_ego = replace(ego, velocity=tuple(v * nominal_signed for v in heading))
                if method in ("governed", "intent"):
                    agent = env.agent
                    native_people = env.engine.get_objects(lambda o: getattr(o, "id", None) in {p.actor_id for p in people})
                    by_id = {str(o.id): o for o in native_people.values()}
                    body = Body(tuple(ego.position), float(agent.heading_theta), float(agent.LENGTH), float(agent.WIDTH))
                    bodies = [Body(tuple(p.position), float(by_id[p.actor_id].heading_theta),
                                   float(by_id[p.actor_id].LENGTH), float(by_id[p.actor_id].WIDTH), tuple(p.velocity)) for p in people]
                    curvature = math.tan(math.radians(float(agent.max_steering))*raw[0]) / (float(agent.FRONT_WHEELBASE)+float(agent.REAR_WHEELBASE))
                    decision = controller.update(body, bodies, raw, signed_speed, curvature, dt)
                else:
                    decision = controller.update(predicted_ego, people, dt)
                executed = tuple(raw)
                brake_fraction = 0.
                if decision["state"] != "PASS":
                    cap = decision["speed_cap_m_s"]
                    if cap <= 1e-9:
                        executed = (raw[0], 0.)
                        brake_fraction = 1.
                    elif speed > cap:
                        executed = (raw[0], 0.)
                        brake_fraction = min(1., (speed-cap)*2.)
                    else:
                        magnitude = min(abs(raw[1]), max(0., min(1., (cap-speed)*2.)))
                        executed = (raw[0], math.copysign(magnitude, raw[1]))
                phase = "inspection" if reached else "navigation"
                if reached:
                    # Same terminal brake for all methods, reverse disabled in evaluation.
                    executed = (0., 0.)
                    brake_fraction = 1.
                env.agent._urban_yield_hold = bool(config.get("low_speed_hold_brake", False) and
                    ((method != "baseline" and decision["state"] == "WAIT") or reached))
                env.agent._refinement_brake = brake_fraction
                observation, reward, terminated, truncated, info = env.step(list(executed))
                ego, people = snapshot(env, tracker, dt)
                if not reached:
                    measurement_info = dict(info, crash_human=pedestrian_contact(info, pedestrian_only))
                    metrics.update(ego, people, dt, measurement_info, decision["state"])
                    if info.get("arrive_dest", False):
                        reached = True
                        navigation_result = metrics.summary(True, bool(truncated))
                else:
                    inspection_elapsed += dt
                    inspection_collision |= any(info.get(k, False) for k in ("crash_human", "crash_vehicle", "crash_object", "crash_building"))
                    in_goal = bool(info.get("arrive_dest", False) and not info.get("out_of_road", False))
                    stop_elapsed = stop_elapsed + dt if math.hypot(*ego.velocity) < config["stop_speed_m_s"] and in_goal else 0.0
                    inspection_complete = stop_elapsed + 1e-9 >= config["inspection_hold_s"] and not inspection_collision
                row = dict(step=step, sim_time_s=(step + 1) * dt, phase=phase,
                           ego=asdict(ego), pedestrians=[asdict(p) for p in people],
                           raw_action=raw, executed_action=executed, controller=decision,
                           info={k: bool(info.get(k, False)) for k in
                                 ("arrive_dest", "crash_human", "crash_vehicle", "crash_object", "crash_building", "crash_sidewalk", "out_of_road", "max_step")})
                row["heading_rad"] = float(env.agent.heading_theta)
                row["physical_brake_fraction"] = brake_fraction
                row["signed_speed_before_m_s"] = signed_speed
                row["native_speed_m_s"] = float(env.agent.speed)
                row["route_completion"] = float(env.agent.navigation.route_completion)
                row["pedestrian_contact"] = pedestrian_contact(info, pedestrian_only)
                row["hold_brake_requested"] = env.agent._urban_yield_hold
                log.write(json.dumps(row, allow_nan=False) + "\n")
                if writer or inspection_complete:
                    import cv2
                    import imageio.v2 as imageio
                    camera = env.engine.get_sensor("rgb_camera")
                    r = config["render"]
                    frame_bgr = camera.perceive(to_float=False, new_parent_node=env.agent.origin,
                                               position=r["position"], hpr=r["hpr"])
                    frame_rgb = np.ascontiguousarray(frame_bgr[..., ::-1])
                    label = f"{method} seed={seed} t={(step+1)*dt:.1f}s {decision['state']} {phase}"
                    cv2.putText(frame_rgb, label, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    if writer:
                        writer.append_data(frame_rgb)
                        if step == 0:
                            imageio.imwrite(str(output / "first_frame.png"), frame_rgb)
                    if inspection_complete:
                        imageio.imwrite(str(output / "inspection.png"), frame_rgb)
                if terminated or truncated or inspection_complete:
                    break
                if reached and config["inspection_hold_s"] > 0 and inspection_elapsed >= config["inspection_max_s"]:
                    break
        result.update(navigation_result or metrics.summary(reached, bool(truncated) or step + 1 >= config["env_config"]["horizon"]))
        result.update(status="complete", inspection_complete=bool(inspection_complete and result["collision_free_success"]),
                      inspection_collision=inspection_collision, inspection_elapsed_s=inspection_elapsed,
                      recorded_video=bool(record))
        return result
    except Exception as exc:
        result.update(error=f"{type(exc).__name__}: {exc}")
        (output / "error.txt").write_text(traceback.format_exc())
        raise
    finally:
        try:
            if writer:
                writer.close()
            if env:
                env.close()
        finally:
            os.chdir(old_cwd)
            result["wall_seconds"] = time.monotonic() - started
            dump_json(output / "summary.json", result)
