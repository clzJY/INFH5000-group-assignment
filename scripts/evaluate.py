#!/usr/bin/env python3
"""Pairwise campaign runner, one isolated simulator process per episode."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from urban_service.controller import YieldConfig
from urban_service.provenance import dump_json, fingerprint, sha256


def conditions(config, split):
    seeds = config[f"{split}_seeds"]
    if set(config["development_seeds"]) & set(config["test_seeds"]):
        raise ValueError("Development and test seeds overlap")
    if len(seeds) != len(set(seeds)):
        raise ValueError("Duplicate seeds")
    if set(config["methods"]) != {"baseline", "distance", "predictive"} or len(config["methods"]) != 3:
        raise ValueError("Three distinct methods required")
    for method in config["methods"]:
        YieldConfig(mode=method, **config["controller"])
    if any(not isinstance(n, int) or n < 1 or n > config["env_config"]["max_actor_num"] for n in config["densities"].values()):
        raise ValueError("Invalid pedestrian count")
    rows = []
    # Deterministic shuffled execution order reduces systematic order effects.
    for density, seed in itertools.product(config["densities"], seeds):
        methods = list(config["methods"])
        random.Random(seed).shuffle(methods)
        for method in methods:
            rows.append(dict(density=density, pedestrians=config["densities"][density], seed=seed, method=method))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=ROOT / "configs/evaluation.json")
    p.add_argument("--split", choices=["development", "test"], default="development")
    p.add_argument("--plan-only", action="store_true")
    p.add_argument("--campaign", type=Path)
    p.add_argument("--record", action="store_true", help="Record every episode (slower)")
    p.add_argument("--workers", type=int, choices=[1, 2], default=1)
    p.add_argument("--log-root", type=Path, required=True, help="Central execution-record directory")
    args = p.parse_args()
    config = json.loads(args.config.read_text())
    rows = conditions(config, args.split)
    if args.plan_only:
        print(json.dumps(dict(split=args.split, episodes=len(rows), conditions=rows), indent=2))
        return
    if args.split == "test" and config.get("stage") != "frozen_after_simulator_gate":
        p.error("Test split requires a frozen protocol after a real simulator gate")
    def check_sources():
        for relative, expected in config.get("frozen_source_sha256", {}).items():
            if sha256(ROOT / relative) != expected:
                raise ValueError(f"Frozen source changed: {relative}")
    if args.split == "test" and not config.get("frozen_source_sha256"):
        p.error("Test protocol must freeze source hashes")
    check_sources()
    if args.record and args.workers != 1:
        p.error("Use a single renderer; two workers are for physics-only evaluation")
    campaign = args.campaign or ROOT / "runs" / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S-%f")
    campaign = campaign.resolve()
    campaign.mkdir(parents=True, exist_ok=False)
    dump_json(campaign / "protocol.json", config)
    dump_json(campaign / "conditions.json", rows)
    log_root = args.log_root.resolve() / campaign.name
    log_root.mkdir(parents=True, exist_ok=False)
    errors = 0
    def execute(row):
        check_sources()
        output = campaign / f"{row['density']}_seed{row['seed']}_{row['method']}"
        cmd = [sys.executable, str(ROOT / "scripts/run_episode.py"), "--config", str(campaign / "protocol.json"),
               "--method", row["method"], "--seed", str(row["seed"]), "--pedestrians", str(row["pedestrians"]),
               "--output", str(output)]
        if args.record:
            cmd.append("--record")
        with (log_root / (output.name + ".console.log")).open("w") as console:
            process = subprocess.run(cmd, stdout=console, stderr=subprocess.STDOUT)
        check_sources()
        print(f"{output.name}: exit={process.returncode}", flush=True)
        return process.returncode
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for index in range(0, len(rows), args.workers):
            codes = list(pool.map(execute, rows[index:index+args.workers]))
            errors += sum(code != 0 for code in codes)
            completed += len(codes)
            if errors:
                break
    dump_json(campaign / "campaign_status.json", dict(config_sha256=fingerprint(config),
              split=args.split, planned_episodes=len(rows), process_errors=errors,
              completed_episodes=completed, workers=args.workers, complete=not errors and completed==len(rows)))
    if errors:
        sys.exit(1)
    subprocess.run([sys.executable, str(ROOT / "scripts/summarize.py"), str(campaign)], check=True)


if __name__ == "__main__":
    main()
