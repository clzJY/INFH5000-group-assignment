"""Separate batch-one latency probe; run after native simulation has finished."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from vlm_policy_v3 import Policy

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--adapter',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.dataset.read_text())['validation'][:50];images=[Image.open(r['image']).convert('RGB') for r in data]
    t=time.monotonic();policy=Policy();policy.load(a.adapter);torch.cuda.synchronize();load_s=time.monotonic()-t
    result=dict(model_constructor_and_adapter_load_s=load_s,loading_note='Fresh process; filesystem cache warm; Python imports excluded.',device=torch.cuda.get_device_name(0),torch_version=torch.__version__,sample_count=len(images),batch_size=1,modes={})
    for mode in ('vlm','lora'):
        for image in images[:5]:policy.predict(image,mode)
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();times=[]
        for image in images:
            start=time.monotonic();policy.predict(image,mode);torch.cuda.synchronize();times.append(time.monotonic()-start)
        result['modes'][mode]=dict(median_ms=1000*float(np.median(times)),p95_ms=1000*float(np.percentile(times,95)),mean_ms=1000*float(np.mean(times)),peak_tensor_allocated_bytes=torch.cuda.max_memory_allocated(),samples_s=times)
    result['scope']='Direct policy preprocessing and prediction with synchronization; no HTTP queue and no active native rollouts. Shared machine, not an exclusive hardware reservation.'
    temporary=a.output.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2)+'\n');temporary.replace(a.output)
    print('BATCH_ONE_LATENCY_PROBE_COMPLETE',a.output)

if __name__=='__main__':main()
