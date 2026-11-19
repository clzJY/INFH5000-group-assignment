"""Descriptive urban-space stratification of the audited natural suite."""
import argparse,csv,json,statistics
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);a=p.parse_args()
    assert json.loads((a.core/'audit.json').read_text())['passed']
    episodes=json.loads((a.core/'episodes.json').read_text());rows=[]
    for method in sorted({r['method'] for r in episodes}):
        for family in ('all','X','S','SC'):
            for width in ('narrow','wide'):
                for count in (5,15):
                    rs=[r for r in episodes if r['method']==method and (family=='all' or r['map']==family) and r['width']==width and r['pedestrians']==count]
                    valid=[r for r in rs if r['valid']]
                    rows.append(dict(method=method,map=family,width=width,pedestrians=count,n=len(rs),valid=len(valid),
                        strict=sum(r['strict_goal'] for r in rs),clean=sum(r['contact_free'] for r in rs),
                        waiting_s=statistics.mean(r['waiting_s'] for r in valid) if valid else None,
                        outside_fraction=statistics.mean(r['outside_walkable_fraction'] for r in valid) if valid else None))
    (a.core/'spatial_strata.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (a.core/'spatial_strata.csv').open('w') as f:
        writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('SPATIAL_STRATA_COMPLETE',len(rows))

if __name__=='__main__':main()
