#!/usr/bin/env python3
"""Read-only readiness report; never downloads or starts a simulator."""
import argparse
from datetime import datetime
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from urban_service.runtime import input_errors


def inspect(config):
    errors = input_errors(ROOT, config)
    dependencies = {}
    for name in ("numpy", "torch", "stable-baselines3", "gymnasium", "panda3d", "imageio-ffmpeg"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
            errors.append(f"Missing runtime distribution: {name}")
    if sys.version_info[:2] != (3, 11):
        errors.append("Simulator runtime requires the prepared Python 3.11 interpreter")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        errors.append("Simulator requires Linux x86_64")
    for executable in ("cmake", "make", "gcc", "g++"):
        if not shutil.which(executable):
            errors.append(f"Missing build tool: {executable}")
    return dict(time=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                scope="read_only_preflight_no_rollout", ready=not errors,
                python=sys.executable, python_version=platform.python_version(),
                platform=platform.platform(), dependencies=dependencies, errors=errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/evaluation.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(json.loads(args.config.read_text()))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ready"] else 2)
