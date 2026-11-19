"""Recorded flag sensitivity, without changing the primary arrival definition."""
import argparse,json
from collections import defaultdict
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();counts=defaultdict(lambda:dict(n=0,strict=0,native_flag_any=0,within_2m_any=0,native_without_strict=0,within_2m_without_strict=0))
    for suite in ('main_classical_v1','main_visual_v1'):
        base=a.runs/suite
        for row in json.loads((base/'plan.json').read_text()):
            folder=base/('{map}_{width}_p{pedestrians}_s{seed}_{method}'.format(**row))
            s=json.loads((folder/'summary.json').read_text());assert s['status']=='complete'
            trace=[json.loads(line) for line in (folder/'steps.jsonl').read_text().splitlines()]
            native=any(r['native_arrival'] for r in trace);near=any(r['goal_distance_m']<=2 for r in trace);strict=any(r['strict_arrival'] for r in trace)
            assert strict==s['strict_goal'];c=counts[row['method']];c['n']+=1;c['strict']+=strict;c['native_flag_any']+=native;c['within_2m_any']+=near;c['native_without_strict']+=native and not strict;c['within_2m_without_strict']+=near and not strict
    a.output.write_text(json.dumps(dict(methods=dict(counts),interpretation='Flags observed along the recorded strict-criterion trajectories. This is not a rerun with alternative termination rules; the prespecified primary criterion remains native flag AND distance<=2m.'),indent=2)+'\n')
    print('ARRIVAL_FLAG_DIAGNOSTIC_COMPLETE')

if __name__=='__main__':main()
