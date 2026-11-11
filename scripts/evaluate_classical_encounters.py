#!/usr/bin/env python3
"""Separate controlled-encounter campaign, preserving configs and source copies."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import copy
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from urban_service.provenance import dump_json,sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--split',choices=['development','test'],required=True)
    p.add_argument('--campaign',type=Path,required=True);p.add_argument('--log-root',type=Path,required=True);p.add_argument('--workers',type=int,default=2,choices=[1,2]);a=p.parse_args()
    c=json.loads(a.config.read_text());seeds=c['encounter_'+a.split+'_seeds']
    assert not set(c['encounter_development_seeds']) & set(c['encounter_test_seeds'])
    assert not set(c['encounter_test_seeds']) & (set(range(100,110))|set(range(200,210))|set(c['test_seeds']))
    def check():
        for relative,h in c.get('frozen_source_sha256',{}).items():assert sha256(ROOT/relative)==h,relative
    if a.split=='test':assert c['stage']=='classical_frozen' and c['frozen_source_sha256']
    check();out=a.campaign.resolve();out.mkdir(parents=True,exist_ok=False)
    logs=a.log_root.resolve()/out.name;logs.mkdir(parents=True,exist_ok=False)
    dump_json(out/'protocol.json',c);rows=[]
    for kind,seed in itertools.product(c['encounter_cases'],seeds):
        methods=list(c['encounter_methods']);random.Random(seed).shuffle(methods)
        for method in methods:rows.append(dict(density=kind,seed=seed,method=method,pedestrians=1,encounter=c['encounter_cases'][kind]))
    dump_json(out/'conditions.json',rows)
    paths=[*list((ROOT/'src/streetscape_baselines').glob('*.py')),ROOT/'scripts/run_classical_encounter.py',ROOT/'scripts/evaluate_classical_encounters.py']
    for path in paths:
        dest=out/'source_snapshot'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    dump_json(out/'source_snapshot_manifest.json',{str(path.relative_to(ROOT)):sha256(path) for path in paths})
    cfgdir=out/'condition_configs';cfgdir.mkdir()
    for kind,recipe in c['encounter_cases'].items():
        config=copy.deepcopy(c);config['encounter']=recipe;dump_json(cfgdir/(kind+'.json'),config)
    def run(row):
        check();name=f"{row['density']}_seed{row['seed']}_{row['method']}"
        cmd=[sys.executable,str(ROOT/'scripts/run_classical_encounter.py'),'--config',str(cfgdir/(row['density']+'.json')),
             '--method',row['method'],'--seed',str(row['seed']),'--pedestrians','1','--output',str(out/name)]
        with (logs/(name+'.log')).open('w') as f:
            code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')).returncode
        check();print(name,'exit',code,flush=True);return code
    errors=0;completed=0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for f in as_completed([pool.submit(run,row) for row in rows]):
            errors+=bool(f.result());completed+=1
            dump_json(out/'campaign_status.json',dict(planned=len(rows),completed=completed,errors=errors,complete=completed==len(rows) and errors==0))
    check()
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
