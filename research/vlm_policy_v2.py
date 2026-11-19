"""Vision-and-language q/v adapters; disabled adapters recover the frozen model."""
import torch
from torch import nn
from vlm_policy import Policy as TextPolicy,LowRank

class Policy(TextPolicy):
    def __init__(self,seed=0):
        super().__init__(seed)
        for name,module in list(self.model.named_modules()):
            if name.startswith('model.vision_model.') and name.endswith(('.q_proj','.v_proj')) and isinstance(module,nn.Linear):
                parent,key=name.rsplit('.',1);adapter=LowRank(module)
                setattr(self.model.get_submodule(parent),key,adapter);self.adapters[name]=adapter
