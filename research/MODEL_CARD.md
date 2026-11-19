# SmolVLM2 local-navigation adapters

These adapters make a pretrained multimodal transformer choose one of six local navigation tokens. They are research artifacts for the accompanying MetaUrban study.

| Item | Value |
| --- | --- |
| Backbone | [HuggingFaceTB/SmolVLM2-500M-Video-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct) |
| Backbone revision | `7b375e1b73b11138ff12fe22c8f2822d8fe03467` |
| Backbone license | Apache 2.0, as stated in the upstream model card |
| Adaptation | Query/value attention projections in vision and language transformers |
| Trainable parameters | 1,114,112; rank 8, alpha 16 |
| Precision | Frozen bfloat16 base; FP32 adapters and optimizer states |
| Inputs | One native RGB/local-map composite and a fixed navigation instruction |
| Output | Conditional next-token probabilities for A–F |
| Supervision | Geometric rollout teacher, class-weighted cross-entropy |
| Final full-layout dataset | 598 training decisions; 304 validation decisions |
| Primary training seed | 0, specified before formal visual testing |
| Additional models | Seeds 1 and 2; seed-0 adapter excluding SC from training and validation |
| Selection | Mean of validation accuracy and six-class macro recall |

The primary adapter achieves 77.3% validation agreement and 47.5% class-balanced recall. A constant-label comparator achieves 54.6% agreement. These are teacher-imitation metrics, not navigation success rates. Training and validation have disjoint scene seeds and no identical cross-split image hashes. Validation includes repeated views within scenes; decisions are not independent city observations.

A–E correspond to local lateral route-following choices; F stops. Geometric checking can replace a proposed action before native steering/throttle/brake execution. The model receives privileged simulator geometry in its map panel, uses no explicit visual history and has not been evaluated as an open-vocabulary instruction follower. It is not a standalone end-to-end VLA or a real-robot navigation policy.

The release contains adapter tensors only. Acquire the frozen backbone separately from its upstream distribution and retain its license and notices. Generated input images, labels, training histories, selected-checkpoint hashes and separate test outcomes accompany the adapters. The pretrained backbone is unchanged; the navigation adapters and training procedure were developed for this project.

Use the code in `vlm_policy_v3.py` and `serve_v3.py` for these final checkpoints. Earlier development trainers/servers reproduce development attempts and should not be substituted for the final FP32-adapter implementation.
