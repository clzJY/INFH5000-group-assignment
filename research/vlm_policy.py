"""Frozen SmolVLM2 with low-rank q/v adapters and six action-token logits."""
import json,math,time,os
from pathlib import Path
import torch
from torch import nn
from transformers import AutoProcessor,AutoModelForImageTextToText
from observation import PROMPT

MODEL=Path(os.environ.get('INFH_VLM_PATH',Path.home()/'.cache/huggingface/hub/models--HuggingFaceTB--SmolVLM2-500M-Video-Instruct/snapshots/7b375e1b73b11138ff12fe22c8f2822d8fe03467'))

class LowRank(nn.Module):
    def __init__(self,base,rank=8):
        super().__init__();self.base=base;self.rank=rank;self.enabled=True
        self.A=nn.Parameter(torch.empty(rank,base.in_features,device=base.weight.device,dtype=base.weight.dtype))
        self.B=nn.Parameter(torch.zeros(base.out_features,rank,device=base.weight.device,dtype=base.weight.dtype))
        nn.init.kaiming_uniform_(self.A,a=math.sqrt(5))
    def forward(self,x):
        result=self.base(x)
        return result+torch.nn.functional.linear(torch.nn.functional.linear(x,self.A),self.B)*2 if self.enabled else result

class Policy:
    def __init__(self,seed=0):
        torch.manual_seed(seed);torch.set_num_threads(2)
        self.processor=AutoProcessor.from_pretrained(MODEL,local_files_only=True)
        self.processor.image_processor.size={'longest_edge':512}
        self.processor.image_processor.do_image_splitting=False
        self.processor.tokenizer.padding_side='left'
        self.model=AutoModelForImageTextToText.from_pretrained(MODEL,local_files_only=True,dtype=torch.bfloat16,attn_implementation='sdpa').to('cuda')
        for p in self.model.parameters():p.requires_grad_(False)
        self.adapters={}
        for name,module in list(self.model.named_modules()):
            if name.startswith('model.text_model.') and name.endswith(('.q_proj','.v_proj')) and isinstance(module,nn.Linear):
                parent,key=name.rsplit('.',1);adapter=LowRank(module)
                setattr(self.model.get_submodule(parent),key,adapter);self.adapters[name]=adapter
        assert self.adapters
        self.ids=[self.processor.tokenizer.encode(c,add_special_tokens=False)[0] for c in 'ABCDEF']
        self.model.eval();self.tag='base'
    def enabled(self,value):
        for a in self.adapters.values():a.enabled=value
    def load(self,path):
        weights=torch.load(path,map_location='cuda',weights_only=True)
        self.model.load_state_dict(weights,strict=False);self.tag=str(path)
    def save(self,path):
        torch.save({k:v.detach().cpu() for k,v in self.model.state_dict().items() if k.endswith(('.A','.B'))},path)
    def inputs(self,images,prompt=PROMPT):
        messages=[{'role':'user','content':[{'type':'image'},{'type':'text','text':prompt}]}]
        text=self.processor.apply_chat_template(messages,add_generation_prompt=True)
        return self.processor(text=[text]*len(images),images=[[im] for im in images],padding=True,return_tensors='pt').to('cuda',dtype=torch.bfloat16)
    def logits(self,inputs):
        return self.model(**inputs,use_cache=False,logits_to_keep=1).logits[:,-1,self.ids].float()
    def predict(self,image,mode='vlm'):
        self.enabled(mode.startswith('lora'))
        prompt=PROMPT if not mode.endswith('no_language') else 'Choose A, B, C, D, E, or F.'
        t=time.monotonic()
        with torch.inference_mode():probs=self.logits(self.inputs([image],prompt)).softmax(-1)[0].cpu().tolist()
        return dict(choice=max(range(6),key=lambda i:probs[i]),probabilities=probs,latency_s=time.monotonic()-t,model_revision=MODEL.name,adapter=self.tag if mode.startswith('lora') else None)
