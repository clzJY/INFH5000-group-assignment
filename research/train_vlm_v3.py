"""Scene-disjoint behavioural cloning of a geometric local-trajectory teacher."""
import argparse,json,random,time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from vlm_policy import MODEL
from vlm_policy_v3 import Policy

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,default=0);p.add_argument('--epochs',type=int,default=6);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);rng=random.Random(a.seed);np.random.seed(a.seed)
    data=json.loads(a.dataset.read_text());train=data['train'];val=data['validation'];policy=Policy(a.seed)
    optimizer=torch.optim.AdamW([p for p in policy.model.parameters() if p.requires_grad],lr=3e-4,weight_decay=.01)
    counts=np.bincount([r['label'] for r in train],minlength=6);weights=torch.tensor(np.clip(len(train)/(6*np.maximum(counts,1)),.3,4),device='cuda',dtype=torch.float32)
    best=-1.;history=[];started=time.monotonic()
    def validate():
        policy.model.eval();correct=0;preds=[]
        with torch.inference_mode():
            for begin in range(0,len(val),8):
                batch=val[begin:begin+8];x=policy.inputs([Image.open(r['image']).convert('RGB') for r in batch]);pred=policy.logits(x).argmax(-1).cpu().tolist()
                for r,j in zip(batch,pred):correct+=r['label']==j;preds.append([r['label'],j])
        return correct/max(1,len(val)),preds
    for epoch in range(a.epochs):
        rng.shuffle(train);policy.model.train();losses=[]
        for begin in range(0,len(train),4):
            batch=train[begin:begin+4];x=policy.inputs([Image.open(r['image']).convert('RGB') for r in batch]);y=torch.tensor([r['label'] for r in batch],device='cuda')
            logits=policy.logits(x);loss=torch.nn.functional.cross_entropy(logits,y,weight=weights)
            assert torch.isfinite(loss);loss.backward();torch.nn.utils.clip_grad_norm_([p for p in policy.model.parameters() if p.requires_grad],1.)
            optimizer.step();optimizer.zero_grad(set_to_none=True);losses.append(loss.item())
        accuracy,predictions=validate();recalls=[sum(t==k and y==k for t,y in predictions)/sum(t==k for t,y in predictions) for k in range(6) if any(t==k for t,y in predictions)];balanced=float(np.mean(recalls));selection=.5*(accuracy+balanced);row=dict(epoch=epoch+1,loss=float(np.mean(losses)),validation_accuracy=accuracy,balanced_accuracy=balanced,selection_score=selection,elapsed_s=time.monotonic()-started)
        history.append(row);print(json.dumps(row),flush=True)
        if selection>best:best=selection;policy.save(a.output/'adapter.pt');(a.output/'validation_predictions.json').write_text(json.dumps(predictions)+'\n')
        policy.save(a.output/'last_adapter.pt')
        torch.save(dict(optimizer=optimizer.state_dict(),rng=rng.getstate(),torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state(),epoch=epoch+1),a.output/'resume.pt')
        (a.output/'history.json').write_text(json.dumps(history,indent=2)+'\n')
    (a.output/'training.json').write_text(json.dumps(dict(seed=a.seed,epochs=a.epochs,train_samples=len(train),validation_samples=len(val),trainable_parameters=sum(p.numel() for p in policy.model.parameters() if p.requires_grad),model=str(MODEL),rank=8,alpha=16,adapter_targets='vision and text q/v attention projections',labels='Geometric rollout teacher; not counterfactual simulator outcomes',class_counts=counts.tolist(),best_selection_score=best,learning_rate=3e-4,selection='mean of accuracy and class-balanced recall'),indent=2)+'\n')
if __name__=='__main__':main()
