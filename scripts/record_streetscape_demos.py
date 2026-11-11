#!/usr/bin/env python3
"""RGB repeats of the preselected lowest test seed; excluded from test counts."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cfg=ROOT/'configs/streetscape_frozen_20261102.json'
record=Path((ROOT/'outputs/preparation/current_execution_record.txt').read_text().strip())
for method in ['baseline','distance','predictive']:
 out=ROOT/f'runs/streetscape_demo_high100_{method}_20261102'
 with (record/f'demo_high100_{method}.log').open('w') as log:
  code=subprocess.run([sys.executable,str(ROOT/'scripts/run_episode.py'),'--config',str(cfg),'--method',method,'--seed','100','--pedestrians','15','--record','--output',str(out)],stdout=log,stderr=subprocess.STDOUT).returncode
 print(method,'exit',code,flush=True)
 if code:raise SystemExit(code)
