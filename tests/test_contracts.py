"""Analytic engineering fixtures only; these are not simulated research results."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from urban_service.controller import Actor, PoseTracker, YieldConfig, YieldController, closest_approach
from urban_service.action_adapter import apply_speed_cap
from urban_service.metrics import EpisodeMetrics
from urban_service.provenance import fingerprint
from urban_service.runtime import input_errors
from evaluate import conditions
from verify_artifacts import verify, digest
from summarize import collect
from prepare_orca_build import prepare


def actor(name, x, y, vx=0.0, vy=0.0, radius=0.3):
    return Actor(name, (x, y), (vx, vy), radius)


class GeometryAndControl(unittest.TestCase):
    def test_crossing_is_predicted_before_distance_trigger(self):
        ego = actor("ego", 0, 0, 1, 0)
        person = actor("person", 2, 2, 0, -1)
        t, d = closest_approach(ego, person, 3)
        self.assertAlmostEqual(t, 2)
        self.assertAlmostEqual(d, -0.6)
        simple = YieldController(YieldConfig(mode="distance"))
        predictive = YieldController(YieldConfig(mode="predictive"))
        self.assertEqual(simple.update(ego, [person], 0.1)["state"], "PASS")
        self.assertEqual(predictive.update(ego, [person], 0.1)["state"], "WAIT")

    def test_receding_person_does_not_create_future_collision(self):
        t, d = closest_approach(actor("a", 0, 0), actor("b", 5, 0, 1, 0), 2)
        self.assertEqual(t, 0)
        self.assertAlmostEqual(d, 4.4)

    def test_equal_velocity_has_finite_distance(self):
        t, d = closest_approach(actor("a", 0, 0, 1), actor("b", 2, 0, 1), 2)
        self.assertEqual(t, 0)
        self.assertAlmostEqual(d, 1.4)

    def test_horizon_clips_prediction(self):
        t, _ = closest_approach(actor("a", 0, 0, 1), actor("b", 10, 0), 2)
        self.assertEqual(t, 2)

    def test_no_people_is_missing_measurement_and_pass(self):
        for mode in ("baseline", "distance", "predictive"):
            d = YieldController(YieldConfig(mode=mode)).update(actor("e", 0, 0), [], 0.1)
            self.assertEqual(d["state"], "PASS")
            self.assertIsNone(d["clearance_m"])
            json.dumps(d, allow_nan=False)

    def test_baseline_passthrough_near_people(self):
        c = YieldController(YieldConfig(mode="baseline"))
        d = c.update(actor("a", 0, 0), [actor("b", 0.2, 0)], 0.1)
        self.assertEqual(apply_speed_cap((0.3, 0.8), d, 1), (0.3, 0.8))

    def test_wait_release_requires_continuous_clearance(self):
        c = YieldController(YieldConfig(mode="predictive"))
        ego = actor("e", 0, 0)
        near = [actor("p", 1.0, 0)]
        self.assertEqual(c.update(ego, near, 0.1)["state"], "WAIT")
        for _ in range(4):
            self.assertEqual(c.update(ego, [], 0.1)["state"], "WAIT")
        c.update(ego, near, 0.1)
        for _ in range(4):
            self.assertEqual(c.update(ego, [], 0.1)["state"], "WAIT")
        d = c.update(ego, [], 0.1)
        self.assertEqual(d["state"], "SLOW")
        self.assertAlmostEqual(d["speed_cap_m_s"], 0.1)

    def test_recovery_acceleration_is_bounded(self):
        c = YieldController(YieldConfig(mode="predictive", release_hold_s=0))
        ego = actor("e", 0, 0)
        c.update(ego, [actor("p", 0, 0)], 0.1)
        previous = 0
        for _ in range(8):
            d = c.update(ego, [], 0.1)
            self.assertLessEqual(d["speed_cap_m_s"] - previous, 0.1000001)
            previous = d["speed_cap_m_s"]

    def test_wait_brakes_without_accelerating_or_reversing(self):
        d = {"state": "WAIT", "speed_cap_m_s": 0}
        self.assertEqual(apply_speed_cap((0.2, 1), d, 1), (0.2, -1))
        self.assertEqual(apply_speed_cap((0.2, 1), d, 0), (0.2, 0))
        with self.assertRaises(ValueError):
            apply_speed_cap((0, 1), d, 1, reverse_enabled=True)

    def test_cap_preserves_base_braking(self):
        a = apply_speed_cap((0.2, -0.9), {"state": "SLOW", "speed_cap_m_s": 1}, 0.3)
        self.assertEqual(a, (0.2, -0.9))

    def test_velocities_use_decision_dt_and_reset_spawn(self):
        t = PoseTracker()
        s = {"actor_id": "a", "position": [0, 0], "radius": 0.3}
        self.assertEqual(t.snapshot([s], 0.1)[0].velocity, (0, 0))
        s["position"] = [0.2, 0]
        self.assertEqual(t.snapshot([s], 0.1)[0].velocity, (2, 0))
        t.snapshot([], 0.1)
        self.assertEqual(t.snapshot([s], 0.1)[0].velocity, (0, 0))

    def test_invalid_parameters_and_states_fail(self):
        for kwargs in ({"mode": "unknown"}, {"horizon_s": -1}, {"stop_clearance_m": 2}, {"max_speed_m_s": math.nan}):
            with self.assertRaises(ValueError):
                YieldConfig(**kwargs)
        with self.assertRaises(ValueError):
            actor("x", math.nan, 0)
        with self.assertRaises(ValueError):
            YieldController(YieldConfig()).update(actor("e", 0, 0), [], 0)


class MetricsAndProtocol(unittest.TestCase):
    def test_metrics_geometry_path_time_and_latched_collision(self):
        m = EpisodeMetrics((0, 0))
        m.update(actor("e", 0.3, 0.4), [actor("p", 1, 0.4)], 0.1, {"crash_human": True}, "WAIT")
        m.update(actor("e", 0.6, 0.8), [], 0.1, {"crash_human": True}, "PASS")
        r = m.summary(True, False)
        self.assertAlmostEqual(r["path_length_m"], 1)
        self.assertAlmostEqual(r["duration_s"], 0.2)
        self.assertAlmostEqual(r["near_time_fraction"], 0.5)
        self.assertTrue(r["pedestrian_collision"])
        self.assertFalse(r["collision_free_success"])
        self.assertAlmostEqual(r["wait_time_s"], 0.1)

    def test_no_pedestrian_minimum_is_null(self):
        m = EpisodeMetrics((0, 0))
        m.update(actor("e", 0, 0), [], 0.1, {}, "PASS")
        self.assertIsNone(m.summary(False, True)["min_clearance_m"])

    def test_exactly_sixty_prespecified_test_conditions(self):
        c = json.loads((ROOT / "configs/evaluation.json").read_text())
        rows = conditions(c, "test")
        self.assertEqual(len(rows), 60)
        self.assertEqual(len({(r['density'], r['seed'], r['method']) for r in rows}), 60)

    def test_seed_leakage_is_rejected(self):
        c = json.loads((ROOT / "configs/evaluation.json").read_text())
        c["development_seeds"] = c["test_seeds"][:1]
        with self.assertRaises(ValueError):
            conditions(c, "test")

    def test_missing_assets_prevent_any_download_or_run(self):
        c = json.loads((ROOT / "configs/evaluation.json").read_text())
        with tempfile.TemporaryDirectory() as d:
            errors = input_errors(Path(d), c)
        self.assertTrue(any("automatic downloads are disabled" in x for x in errors))
        self.assertTrue(any("checkpoint" in x for x in errors))

    def test_missing_paired_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "protocol.json").write_text('{}')
            (p / "conditions.json").write_text(json.dumps([dict(density="low",seed=1,method="baseline",pedestrians=5)]))
            with self.assertRaises(ValueError):
                collect(p)

    def test_unmatched_initial_scenes_or_versions_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            protocol = {"engineering_fixture": True}
            rows = [dict(density="low", seed=1, method=m, pedestrians=5) for m in ("baseline", "distance", "predictive")]
            (p / "protocol.json").write_text(json.dumps(protocol))
            (p / "conditions.json").write_text(json.dumps(rows))
            for row in rows:
                path = p / f"low_seed1_{row['method']}"
                path.mkdir()
                value = dict(status="complete", config_sha256=fingerprint(protocol),
                    method=row["method"], seed=1, requested_pedestrians=5,
                    initial_scene_fingerprint="scene-A", core_source_sha256={"fixture": "A"},
                    asset_import_receipt_sha256="fixture-A", checkpoint_sha256="fixture-A",
                    upstream_commit="fixture-A", versions={"fixture": "A"})
                (path / "summary.json").write_text(json.dumps(value))
            self.assertEqual(len(collect(p)), 3)
            changed = p / "low_seed1_predictive/summary.json"
            value = json.loads(changed.read_text())
            value["initial_scene_fingerprint"] = "scene-B"
            changed.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "scene mismatch"):
                collect(p)
            value["initial_scene_fingerprint"] = "scene-A"
            value["versions"] = {"fixture": "B"}
            changed.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "identity changed"):
                collect(p)

    def test_python311_orca_compatibility_patch_is_scoped_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "CMakeLists.txt"
            original = "project(test)\nadd_subdirectory(pybind11)\nfind_package(pybind11 REQUIRED)\nadd_library(x STATIC x.cpp)\n"
            p.write_text(original)
            prepare(p)
            once = p.read_text()
            prepare(p)
            self.assertEqual(once, p.read_text())
            self.assertIn("find_package(pybind11 CONFIG REQUIRED)", once)
            self.assertIn("add_library(x STATIC x.cpp)", once)
            p.write_text("unknown configuration")
            with self.assertRaises(ValueError):
                prepare(p)

    def test_receipt_integrity_and_uncovered_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "downloads").mkdir()
            f = p / "downloads/runtime.tar.gz"
            f.write_bytes(b"engineering fixture, not real artifact")
            (p / "receipt_test.json").write_text(json.dumps({"entries": [{"path": "/mac/downloads/runtime.tar.gz", "sha256": digest(f)}]}))
            self.assertEqual(verify(p), 1)
            f.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify(p)

    def test_fingerprint_is_key_order_independent(self):
        self.assertEqual(fingerprint({"x":1,"y":2}), fingerprint({"y":2,"x":1}))


if __name__ == "__main__":
    unittest.main()
