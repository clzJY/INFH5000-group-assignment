"""Export immutable generated training inputs and adapters with portable paths."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--holdout',type=Path,required=True)
    p.add_argument('--models',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'research/training_data');a=p.parse_args()
    a.output=a.output.resolve();a.output.relative_to(ROOT);a.output.mkdir(parents=True,exist_ok=False)
    images=a.output/'images';images.mkdir();source_hashes={};copied=set()
    for name,source in [('dataset.json',a.dataset),('dataset_holdout.json',a.holdout)]:
        data=json.loads(source.read_text());source_hashes[name]=digest(source)
        collection_protocol=data.pop('protocol')
        data['protocol']=dict(source_collection_protocol=collection_protocol,
            effective_conditions={split:[list(c) for c in sorted({tuple(r['condition']) for r in data[split]})] for split in ('train','validation')},
            excluded_family='SC' if name=='dataset_holdout.json' else None)
        for split in ('train','validation'):
            for row in data[split]:
                original=Path(row['image']);sha=digest(original);assert sha==row['image_sha256']
                target=images/(sha+'.png')
                if sha not in copied:shutil.copyfile(original,target);copied.add(sha)
                row['image']=str(target.relative_to(ROOT))
        (a.output/name).write_text(json.dumps(data,indent=2)+'\n')
    metrics=ROOT/'research/results/training';metrics.mkdir(parents=True,exist_ok=True)
    adapter_hashes={}
    for name in ('seed0','seed1','seed2','holdout'):
        source=a.models/name;target=a.output/'adapters'/name;target.mkdir(parents=True)
        shutil.copyfile(source/'adapter.pt',target/'adapter.pt');adapter_hashes[name]=digest(target/'adapter.pt')
        destination=metrics/name;destination.mkdir(exist_ok=False)
        for filename in ('training.json','history.json','validation_predictions.json'):
            data=json.loads((source/filename).read_text())
            if filename=='training.json':
                data['model']='HuggingFaceTB/SmolVLM2-500M-Video-Instruct';data['model_revision']='7b375e1b73b11138ff12fe22c8f2822d8fe03467';data['adapter_sha256']=adapter_hashes[name]
            text=json.dumps(data,indent=2)+'\n';(target/filename).write_text(text);(destination/filename).write_text(text)
    manifest=dict(unique_images=len(copied),adapter_sha256=adapter_hashes,source_manifest_sha256=source_hashes,
        paths='Image paths are relative to repository root; extract research/training_data and execute from repository root.',
        base_weights_included=False,labels='Geometric rollout teacher, not counterfactual native outcomes')
    (a.output/'export.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
