#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from streetscape_route.runtime import run_episode

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=ROOT / "configs/baseline_static.json")
    p.add_argument("--method", choices=["baseline", "distance", "predictive", "route", "route_intent"], default="baseline")
    p.add_argument("--seed", type=int, default=20)
    p.add_argument("--pedestrians", type=int, default=5)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--record", action="store_true")
    args = p.parse_args()
    if os.environ.get("PYTHONHASHSEED") != str(args.seed):
        environment = dict(os.environ, PYTHONHASHSEED=str(args.seed), OMP_NUM_THREADS="4")
        os.execve(sys.executable, [sys.executable, *sys.argv], environment)
    result = run_episode(json.loads(args.config.read_text()), args.method, args.seed,
                         args.pedestrians, args.output, args.record)
    print(json.dumps({k:v for k,v in result.items() if k not in ("planned_route","core_source_sha256")}, indent=2))
