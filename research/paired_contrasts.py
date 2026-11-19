"""Exploratory hierarchy contrasts and seed-blocked uncertainty sensitivity."""
import argparse,json,statistics
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('--episodes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=json.loads(a.episodes.read_text());lookup={(r['map'],r['width'],r['pedestrians'],r['seed'],r['method']):r for r in rows};results=[]
    for method,control in [('lattice','rpp'),('lattice','forecast'),('lora','lattice')]:
        keys=[key[:-1] for key in lookup if key[-1]==method and (*key[:-1],control) in lookup]
        deltas=np.array([int(lookup[(*k,method)]['contact_free'])-int(lookup[(*k,control)]['contact_free']) for k in keys]);result=dict(method=method,control=control,n=len(keys),clean_delta_pp=100*float(deltas.mean()))
        for name,group in [('family_seed',lambda k:(k[0],k[3])),('seed_only',lambda k:k[3])]:
            clusters=sorted({group(k) for k in keys});values=np.array([np.mean([d for k,d in zip(keys,deltas) if group(k)==c]) for c in clusters])
            rng=np.random.default_rng(20261119);bootstrap=values[rng.integers(0,len(values),size=(10000,len(values)))].mean(1)
            result[name]=dict(clusters=len(clusters),interval_95_pp=(100*np.percentile(bootstrap,[2.5,97.5])).tolist())
        joint=[k for k in keys if lookup[(*k,method)]['strict_goal'] and lookup[(*k,control)]['strict_goal']]
        result['joint_successes']=len(joint);result['joint_delay_s']=statistics.mean(lookup[(*k,method)]['duration_s']-lookup[(*k,control)]['duration_s'] for k in joint) if joint else None
        results.append(result)
    a.output.write_text(json.dumps(dict(comparisons=results,interpretation='Additional descriptive package comparisons; seed-only clustering keeps all families/width/crowd variants of a seed together. No model or checkpoint selection.'),indent=2)+'\n')
    print('ADDITIONAL_PAIRED_CONTRASTS_COMPLETE',len(results))

if __name__=='__main__':main()
