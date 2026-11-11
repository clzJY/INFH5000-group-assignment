#!/usr/bin/env python3
"""Require complete paired results and equal initial scenes before aggregation."""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from urban_service.provenance import dump_json, fingerprint


def collect(campaign):
    protocol = json.loads((campaign / "protocol.json").read_text())
    expected = json.loads((campaign / "conditions.json").read_text())
    rows = []
    paired = {}
    identities = None
    for condition in expected:
        name = f"{condition['density']}_seed{condition['seed']}_{condition['method']}"
        path = campaign / name / "summary.json"
        if not path.is_file():
            raise ValueError(f"Missing condition: {name}")
        row = json.loads(path.read_text())
        if row.get("status") != "complete" or row.get("config_sha256") != fingerprint(protocol):
            raise ValueError(f"Incomplete/inconsistent condition: {name}")
        identity = {k: row[k] for k in ("core_source_sha256", "asset_import_receipt_sha256", "checkpoint_sha256", "upstream_commit", "versions")}
        if identities is None:
            identities = identity
        elif identities != identity:
            raise ValueError(f"Runtime/source/asset identity changed: {name}")
        for key, target in (("method", condition["method"]), ("seed", condition["seed"]), ("requested_pedestrians", condition["pedestrians"])):
            if row[key] != target:
                raise ValueError(f"Condition identity mismatch: {name}, {key}")
        key = condition["density"], condition["seed"]
        previous = paired.setdefault(key, row["initial_scene_fingerprint"])
        if previous != row["initial_scene_fingerprint"]:
            raise ValueError(f"Initial scene mismatch for paired condition {key}")
        row["density"] = condition["density"]
        rows.append(row)
    if len(rows) != len({(r["density"], r["seed"], r["method"]) for r in rows}):
        raise ValueError("Duplicate conditions")
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("campaign", type=Path)
    args = p.parse_args()
    rows = collect(args.campaign)
    fields = ["density", "method", "seed", "navigation_success", "collision_free_success",
              "pedestrian_collision", "any_collision", "duration_s", "path_length_m", "min_clearance_m",
              "near_time_fraction", "wait_time_s", "timeout", "inspection_complete"]
    with (args.campaign / "episodes.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    grouped = []
    for density, method in sorted({(r["density"], r["method"]) for r in rows}):
        part = [r for r in rows if r["density"] == density and r["method"] == method]
        successful = [r for r in part if r["navigation_success"]]
        d = dict(density=density, method=method, n=len(part),
                 success_count=sum(r["navigation_success"] for r in part),
                 collision_free_success_count=sum(r["collision_free_success"] for r in part),
                 pedestrian_collision_count=sum(r["pedestrian_collision"] for r in part),
                 timeout_count=sum(r["timeout"] for r in part),
                 successful_duration_median_s=statistics.median(r["duration_s"] for r in successful) if successful else None)
        for key in ("min_clearance_m", "near_time_fraction", "wait_time_s"):
            values = [r[key] for r in part if r[key] is not None]
            d[key + "_median"] = statistics.median(values) if values else None
        grouped.append(d)
    differences = []
    for density, seed in sorted({(r["density"], r["seed"]) for r in rows}):
        part = {r["method"]: r for r in rows if r["density"] == density and r["seed"] == seed}
        for method in ("distance", "predictive"):
            base, modified = part["baseline"], part[method]
            differences.append(dict(density=density, seed=seed, method=method,
                success_delta=int(modified["navigation_success"]) - int(base["navigation_success"]),
                pedestrian_collision_delta=int(modified["pedestrian_collision"]) - int(base["pedestrian_collision"]),
                duration_delta_s=modified["duration_s"] - base["duration_s"] if base["navigation_success"] and modified["navigation_success"] else None))
    dump_json(args.campaign / "grouped_results.json", grouped)
    dump_json(args.campaign / "paired_differences.json", differences)
    print(f"PAIRED_RESULTS_VERIFIED {len(rows)}")


if __name__ == "__main__":
    main()
