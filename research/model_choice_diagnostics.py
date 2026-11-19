"""Count actual model proposals, separately from executed physical actions."""
import argparse,json
from collections import defaultdict
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    results=defaultdict(lambda:dict(episodes=0,queries=0,choice_counts=[0]*6))
    for row in json.loads((a.campaign/'plan.json').read_text()):
        folder=a.campaign/('{map}_{width}_p{pedestrians}_s{seed}_{method}'.format(**row));summary=json.loads((folder/'summary.json').read_text());assert summary['status']=='complete'
        queries=json.loads((folder/'vlm_queries.json').read_text());assert len(queries)==summary['queries'];result=results[row['method']];result['episodes']+=1;result['queries']+=len(queries)
        for query in queries:result['choice_counts'][query['choice']]+=1
    a.output.write_text(json.dumps(dict(modes=dict(results),interpretation='Proposed A-F tokens before geometric revalidation; long episodes contribute more queries.'),indent=2)+'\n')
    print('MODEL_PROPOSAL_DIAGNOSTICS_COMPLETE')

if __name__=='__main__':main()
