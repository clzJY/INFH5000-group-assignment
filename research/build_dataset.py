"""Whole-scene split, duplicate-wait thinning and immutable input manifest."""
import argparse,hashlib,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--train',type=Path,required=True);p.add_argument('--validation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result={};conditions={}
    for split,root in (('train',a.train),('validation',a.validation)):
        rows=[];keys=[]
        for sf in sorted(root.glob('*/summary.json')):
            summary=json.loads(sf.read_text())
            if summary['status']!='complete':continue
            key=(summary['map'],summary['width'],summary['pedestrians'],summary['seed']);keys.append(key)
            last_label=None;repeats=0
            for line in (sf.parent/'samples.jsonl').read_text().splitlines():
                sample=json.loads(line);repeats=repeats+1 if sample['label']==last_label else 0;last_label=sample['label']
                if repeats>3 and repeats%10!=0:continue
                image=(sf.parent/sample['image']).resolve()
                rows.append(dict(image=str(image),label=sample['label'],condition=list(key),step=sample['step'],image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
        result[split]=rows;conditions[split]=keys
    assert set(tuple(c) for c in conditions['train']).isdisjoint(tuple(c) for c in conditions['validation'])
    assert {c[3] for c in conditions['train']}.isdisjoint(c[3] for c in conditions['validation'])
    result['protocol']=dict(conditions=conditions,labels='Feasible geometric trajectory teacher, no future simulator outcomes',frames='Native RGB and privileged local geometry',group_split='Complete scenario seed, no frame random split')
    assert result['train'] and result['validation']
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:len(result[k]) for k in ('train','validation')})
if __name__=='__main__':main()
