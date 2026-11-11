#!/usr/bin/env python3
"""Isolated matched evaluation; source identities checked before and after runs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from urban_service.provenance import sha256, dump_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--split', choices=['development','test'], required=True)
    p.add_argument('--campaign', type=Path, required=True)
    p.add_argument('--log-root', type=Path, required=True)
    p.add_argument('--workers', type=int, default=2, choices=[1,2])
    a = p.parse_args()
    c = json.loads(a.config.read_text())
    assert not set(c['development_seeds']) & set(c['test_seeds'])
    assert not set(c['test_seeds']) & (set(range(100,110)) | set(range(200,210))), 'Old tests are diagnostic data, not fresh tests'
    if a.split == 'test':
        assert c['stage'] == 'classical_frozen' and c['frozen_source_sha256']
    def check():
        for rel, expected in c.get('frozen_source_sha256', {}).items():
            assert sha256(ROOT/rel) == expected, rel
    check()
    out = a.campaign.resolve(); out.mkdir(parents=True,exist_ok=False)
    logs = a.log_root.resolve()/out.name; logs.mkdir(parents=True,exist_ok=False)
    rows=[]
    for density,seed in itertools.product(c['densities'],c[a.split+'_seeds']):
        methods=list(c['methods']); random.Random(seed).shuffle(methods)
        rows.extend(dict(density=density, seed=seed, pedestrians=c['densities'][density],method=m) for m in methods)
    dump_json(out/'protocol.json',c);dump_json(out/'conditions.json',rows)
    # Preserve exploratory source revisions too, before any results are inspected.
    import shutil
    snapshot=out/'source_snapshot'
    paths=[*list((ROOT/'src/streetscape_baselines').glob('*.py')),ROOT/'scripts/run_classical_episode.py',ROOT/'scripts/evaluate_classical.py']
    for path in paths:
        destination=snapshot/path.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    dump_json(out/'source_snapshot_manifest.json',{str(path.relative_to(ROOT)):sha256(path) for path in paths})
    def run(row):
        check()
        name=f"{row['density']}_seed{row['seed']}_{row['method']}"
        cmd=[sys.executable,str(ROOT/'scripts/run_classical_episode.py'),'--config',str(out/'protocol.json'),
             '--method',row['method'],'--seed',str(row['seed']),'--pedestrians',str(row['pedestrians']),'--output',str(out/name)]
        with (logs/(name+'.log')).open('w') as f:
            code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')).returncode
        check()
        print(name,'exit',code,flush=True)
        return code
    errors=0;completed=0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for f in as_completed([pool.submit(run,row) for row in rows]):
            errors+=bool(f.result());completed+=1
            dump_json(out/'campaign_status.json',dict(planned=len(rows),completed=completed,errors=errors,complete=completed==len(rows) and errors==0))
    check()
    if errors: raise SystemExit(1)


if __name__ == '__main__': main()
