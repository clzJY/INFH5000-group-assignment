"""Validation-only teacher agreement and visual-input sensitivity diagnostics."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from vlm_policy_v3 import Policy
from observation import PROMPT

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--adapter',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.dataset.read_text())['validation'];policy=Policy();policy.load(a.adapter);policy.model.eval();results={}
    labels=np.array([r['label'] for r in data]);prior=int(np.bincount(labels,minlength=6).argmax())
    for mode in ('vlm','lora','no_rgb','no_image','minimal_language'):
        policy.enabled(mode!='vlm');probs=[]
        for begin in range(0,len(data),8):
            batch=data[begin:begin+8];images=[]
            for r in batch:
                im=Image.open(r['image']).convert('RGB')
                if mode=='no_rgb':im.paste((128,128,128),(0,40,320,280))
                if mode=='no_image':im=Image.new('RGB',im.size,(128,128,128))
                images.append(im)
            prompt=PROMPT if mode!='minimal_language' else 'Choose A, B, C, D, E, or F.'
            with torch.inference_mode():probs.extend(policy.logits(policy.inputs(images,prompt)).softmax(-1).cpu().tolist())
        pred=np.asarray(probs).argmax(axis=1)
        results[mode]=dict(accuracy=float(np.mean(pred==labels)),balanced_accuracy=float(np.mean([np.mean(pred[labels==k]==k) for k in set(labels)])),
                           choices=pred.tolist(),probabilities=probs)
    full=np.array(results['lora']['choices'])
    for mode in ('no_rgb','no_image','minimal_language'):
        results[mode]['action_agreement_with_full']=float(np.mean(np.array(results[mode]['choices'])==full))
    a.output.write_text(json.dumps(dict(samples=len(data),constant_label=prior,constant_accuracy=float(np.mean(labels==prior)),results=results),indent=2)+'\n')
if __name__=='__main__':main()
