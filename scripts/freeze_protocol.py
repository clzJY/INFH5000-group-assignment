#!/usr/bin/env python3
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from urban_service.provenance import dump_json, fingerprint, sha256
from evaluate import conditions

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=ROOT / "configs/evaluation.json")
    p.add_argument("--gate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    c = json.loads(args.config.read_text())
    gate = json.loads(args.gate.read_text())
    if not gate.get("passed") or gate.get("scope") != "real_simulator_gate" or gate.get("evaluation_config_sha256") != fingerprint(c):
        p.error("Real simulator gate must pass for this exact evaluation configuration")
    conditions(c, "test")
    if args.output.exists():
        p.error("Frozen protocol destination already exists")
    c.update(stage="frozen_after_simulator_gate", frozen_time=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
             gate_sha256=sha256(args.gate), gate_path=str(args.gate.resolve()))
    sources = list((ROOT / "src/urban_service").glob("*.py")) + [ROOT/"scripts/run_episode.py",ROOT/"scripts/evaluate.py"]
    c["frozen_source_sha256"] = {str(p.relative_to(ROOT)): sha256(p) for p in sources}
    dump_json(args.output, c)
    print("PROTOCOL_FROZEN", args.output)
