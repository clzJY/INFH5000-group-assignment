"""FP32 low-rank parameters/optimizer state with a frozen bfloat16 base."""
import torch
from torch.nn import functional as F
from vlm_policy import LowRank
from vlm_policy_v2 import Policy as MultimodalPolicy

class FP32LowRank(LowRank):
    def forward(self,x):
        base=self.base(x)
        if not self.enabled:return base
        residual=F.linear(F.linear(x.float(),self.A),self.B)*2
        return base+residual.to(base.dtype)

class Policy(MultimodalPolicy):
    def __init__(self,seed=0):
        super().__init__(seed)
        for name,old in list(self.adapters.items()):
            new=FP32LowRank(old.base,rank=old.rank)
            new.A.data=old.A.data.float();new.B.data=old.B.data.float()
            parent,key=name.rsplit('.',1);setattr(self.model.get_submodule(parent),key,new);self.adapters[name]=new
