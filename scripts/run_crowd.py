#!/usr/bin/env python3
import os
os.environ.setdefault("OMP_NUM_THREADS","1")
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from urban_service.crowd_experiment import run_episode,run_campaign

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--config",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--split",choices=["development","test"],default="development")
    p.add_argument("--case",type=int)
    p.add_argument("--method",default="baseline")
    p.add_argument("--scenario",default="circle_crossing")
    a=p.parse_args();c=json.loads(a.config.read_text())
    if a.case is None:run_campaign(c,a.output,a.split)
    else:print(json.dumps(run_episode(c,a.scenario,a.method,a.case,a.output),indent=2))
