"""Supplement metric recomputation with condition, source and query checks."""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUITES=['main_classical_v1','main_visual_v1','model_seed_variation_v1','input_ablations_v1','holdout_curve_v1','challenge_test_v1']
CRITICAL=['run_native.py','routing.py','local_planner.py','observation.py','probe_scene.py']

def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,default=ROOT/'research/runs');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    protocol=json.loads((ROOT/'research/protocol_final.json').read_text());model=json.loads((ROOT/'research/protocol_model_v3.json').read_text())
    for name in CRITICAL:assert hashlib.sha256((ROOT/'research'/name).read_bytes()).hexdigest()==protocol['source_sha256'][name],name
    for name,sha in model['source_sha256'].items():assert hashlib.sha256((ROOT/'research'/name).read_bytes()).hexdigest()==sha,name
    episodes=queries=steps=0;placements={}
    for suite in SUITES:
        base=a.runs/suite
        for row in json.loads((base/'plan.json').read_text()):
            name='{map}_{width}_p{pedestrians}_s{seed}_{method}'.format(**row);folder=base/name
            summary=json.loads((folder/'summary.json').read_text());assert all(summary[k]==v for k,v in row.items()),name
            assert summary['status'] in ('complete','invalid_task'),name
            for k in CRITICAL:assert summary['research_source_sha256'][k]==protocol['source_sha256'][k],(name,k)
            episodes+=1
            if summary['status']=='invalid_task':continue
            q=json.loads((folder/'vlm_queries.json').read_text());assert len(q)==summary['queries']
            visual=row['method'].startswith(('vlm','lora'))
            assert len(q)==math.ceil(summary['steps']/10) if visual else len(q)==0
            expected='holdout' if 'holdout' in row['method'] else 'seed1' if '_s1' in row['method'] else 'seed2' if '_s2' in row['method'] else 'seed0'
            for index,item in enumerate(q):
                assert item['step']==10*index and item['model_revision']==model['revision']
                probabilities=item['probabilities'];assert len(probabilities)==6 and all(math.isfinite(v) and 0<=v<=1 for v in probabilities)
                assert abs(sum(probabilities)-1)<1e-5
                assert item['choice']==max(range(6),key=lambda i:probabilities[i])
                if row['method'].startswith('lora'):assert Path(item['adapter']).parent.name==expected
                else:assert item['adapter'] is None
            queries+=len(q)
            trace=[json.loads(line) for line in (folder/'steps.jsonl').read_text().splitlines()];assert len(trace)==summary['steps']<=1200
            assert any(item['pedestrian_contact'] for item in trace)==summary['pedestrian_contact']
            assert all(not item['pedestrian_contact'] or item['contact'] for item in trace)
            for index,item in enumerate(trace):
                assert item['step']==index and math.isclose(item['time_s'],(index+1)*.1,abs_tol=1e-7)
                assert all(math.isfinite(v) for v in item['post_position']) and math.isfinite(item['post_speed'])
            steps+=len(trace)
            if suite=='challenge_test_v1':
                placement=summary['routing']['challenge'];key=(row['map'],row['width'],row['pedestrians'],row['seed'])
                serial=json.dumps(placement,sort_keys=True);assert key not in placements or placements[key]==serial
                placements[key]=serial
    statuses={}
    for value in placements.values():
        status=json.loads(value)['status'];statuses[status]=statuses.get(status,0)+1
    result=dict(passed=True,episodes=episodes,steps_checked=steps,queries_checked=queries,critical_source_files=CRITICAL,
        conditions_match_plan=True,model_checkpoint_routes_verified=True,model_source_hashes_verified=True,query_budget_verified=True,
        challenge_condition_placement_statuses=statuses,challenge_placements_match_across_methods=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
