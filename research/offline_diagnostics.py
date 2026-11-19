"""Class-level and exact-image-deduplication checks of frozen validation outputs."""
import argparse,json
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--predictions',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.dataset.read_text())['validation'];results=json.loads(a.predictions.read_text())
    labels=np.array([r['label'] for r in data]);assert len(labels)==results['samples']
    unique={}
    for i,row in enumerate(data):
        if row['image_sha256'] in unique:assert labels[unique[row['image_sha256']]]==row['label']
        else:unique[row['image_sha256']]=i
    indices=np.array(list(unique.values()));modes={}
    for mode,result in results['results'].items():
        pred=np.asarray(result['choices']);confusion=np.zeros((6,6),int)
        for x,y in zip(labels,pred):confusion[x,y]+=1
        modes[mode]=dict(confusion=confusion.tolist(),class_recall=np.divide(confusion.diagonal(),confusion.sum(1)).tolist(),
            unique_image_accuracy=float(np.mean(pred[indices]==labels[indices])),unique_image_n=len(indices))
    a.output.write_text(json.dumps(dict(samples=len(data),unique_images=len(indices),class_counts=np.bincount(labels,minlength=6).tolist(),
        class_names=['A: -1.5 m','B: -0.75 m','C: reference','D: +0.75 m','E: +1.5 m','F: stop'],results=modes,
        interpretation='Deduplication is a descriptive diagnostic; original scene-split validation selection is unchanged.'),indent=2)+'\n')
    print('OFFLINE_CLASS_DIAGNOSTICS_COMPLETE',len(data),len(indices))

if __name__=='__main__':main()
