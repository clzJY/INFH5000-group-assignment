# Multi-scene vision-language-guided navigation

This extension implements local trajectory selection and actual multimodal adapter training in native three-dimensional MetaUrban. The retained v12 proposal and pilot sources remain separate. See [the implemented modules and comparisons](METHODS.md) and the [model card](MODEL_CARD.md).

SmolVLM2-500M-Video-Instruct selects six action tokens from native RGB, a privileged local map and a fixed instruction. Rank-8 adapters train 1,114,112 vision/text attention parameters. The execution layer checks sampled geometry and pedestrian motion before native wheel actuation. This is a VLM-guided hierarchy, with geometric fallback.

## Evidence

- Native [intersection](results/videos/native_X_comparison.mp4), [straight-street](results/videos/native_S_comparison.mp4) and [curve](results/videos/native_SC_comparison.mp4) comparison videos. All nine fixed-seed demonstrations are retained, including failures. Playback is twice simulated speed; ended runs hold their last recorded view.
- [Validation input diagnostics](results/offline_validation.json), [class-level checks](results/offline_diagnostics.json) and [training histories](results/training/).
- [Final model protocol](protocol_model_v3.json), [frozen scenario/core-runner protocol](protocol_final.json) and [saved condition plans](plans/).

The formal campaign completed 1,384 episodes across separate suites. Independent audits checked 1,306,599 decision steps and 69,172 model queries. See the [completed paper](paper/urban_vlm_navigation.pdf), [Chinese results](RESULTS_zh.md), [provenance audit](results/provenance_audit.json) and [execution record](results/execution_record.json). Development, teacher collection, runtime probes and demonstrations are excluded from formal outcomes.

| Plan | Episodes | Purpose |
| --- | ---: | --- |
| `main_classical_v1` | 600 | Five classical/geometric methods on 120 natural conditions |
| `main_visual_v1` | 240 | Frozen/adapted VLM on the same 120 conditions |
| `model_seed_variation_v1` | 240 | Two additional training seeds |
| `input_ablations_v1` | 96 | Four input variants on 24 fresh conditions |
| `holdout_curve_v1` | 40 | Adapter trained and validated without the curve family |
| `challenge_test_v1` | 168 | Seven methods on 24 post-planning blockages |

## Environments and graphics

Keep two environments. The native simulator uses retained Python 3.11, CPU Torch 2.3.0, Panda3D 1.10.14 and Shapely 2.0.6. The model uses Python 3.13, CUDA Torch 2.11.0 and Transformers 5.5.4; see [direct model dependencies](requirements-model.txt) and the root [native reproduction instructions](../docs/REPRODUCTION.md).

Set `INFH_VLM_PATH` to the local snapshot of revision `7b375e1b73b11138ff12fe22c8f2822d8fe03467`, retaining that revision as its directory name. Code reads local files; automatic model/asset downloads are disabled. This study reused a cached backbone. Releases contain adapters, not backbone weights or source asset bundles.

Check EGL identity before launching renderers:

```bash
envs/python311/bin/python3 research/probe_render_devices.py
```

EGL/CUDA ordinals can differ. On this server EGL 0 mapped to physical GPU 3, and EGL 3 to GPU 1. Renderer memory reached approximately 3.8 GB per process, in addition to approximately 1.5 GB for the shared model. Bound concurrency using actual free memory and other scheduled work. Prefer the machine's scheduler when available.

## Run a plan

Work from repository root. Extract the generated data/adapters release to `research/training_data/`; its image paths are relative to repository root. Start a shared inference server in the separate model environment:

```bash
export INFH_VLM_PATH=/path/to/7b375e1b73b11138ff12fe22c8f2822d8fe03467
CUDA_VISIBLE_DEVICES=3 HF_HUB_OFFLINE=1 /path/to/model-env/bin/python \
  research/serve_v3.py --port 18762 \
  --adapter-root research/training_data/adapters \
  --adapter research/training_data/adapters/seed0/adapter.pt
```

Use a new experiment directory and a unique operation directory below workspace `storage_management/` for logs:

```bash
envs/python311/bin/python3 research/execute_plan.py \
  --plan research/plans/main_visual_v1.json \
  --output research/runs/reproduction_main_visual \
  --records /path/to/workspace/storage_management/infh_reproduction_TIMESTAMP \
  --workers 4 --egl-device 0 --server http://127.0.0.1:18762 \
  --runtime-cache /dev/shm/infh_reproduction_TIMESTAMP
```

The optional private memory cache avoids repeated glTF temporary/model-cache disk writes; allocate adequate RAM. Select the correct EGL ordinal for the actual host. The coordinator preserves Slurm-provided CUDA allocation and refuses to overwrite incomplete directories. Use `--runner run_challenge.py` for blockage plans, `--collect` for teacher collection, and `--video` for demonstrations. Setup faults are explicitly archived and recovered with the same fixed condition; navigation outcomes are not retried for improvement.

## Train and analyse

Train to a new checkpoint directory, using the model environment:

```bash
CUDA_VISIBLE_DEVICES=3 HF_HUB_OFFLINE=1 /path/to/model-env/bin/python \
  research/train_vlm_v3.py --dataset research/training_data/dataset.json \
  --output research/models/reproduction_seed0 --seed 0 --epochs 10
```

Use `dataset_holdout.json` for the curve-excluded model. Final inference/training requires `vlm_policy_v3.py` and its parent modules. Earlier trainers/servers retain development variants and should not replace the final FP32-adapter implementation.

After extracting released raw evaluations to their original `research/runs/` paths:

```bash
envs/python311/bin/python3 research/analyze.py \
  research/runs/main_classical_v1 research/runs/main_visual_v1 \
  --output research/results/core
envs/python311/bin/python3 research/spatial_analysis.py --core research/results/core
envs/python311/bin/python3 research/paired_contrasts.py \
  --episodes research/results/core/episodes.json --output research/results/core/additional_contrasts.json
envs/python311/bin/python3 research/arrival_flag_diagnostic.py \
  --runs research/runs --output research/results/core/arrival_flag_diagnostic.json
envs/python311/bin/python3 research/model_choice_diagnostics.py \
  --campaign research/runs/input_ablations_v1 --output research/results/ablations/choice_diagnostics.json
envs/python311/bin/python3 research/audit_provenance.py \
  --output research/results/provenance_audit.json
```

Analyse the other four suites separately into `variation`, `ablations`, `holdout` and `challenge`. Audits recompute arrival/contact/waiting/standstill/outside exposure and check matched conditions. The provenance audit checks immutable sources, model routing, query budgets and blockage placement. `make_figures.py`, `make_videos.py` and `make_paper.py` build curated outputs. Compile the article twice with `pdflatex`; rebuilding its prose from curated JSON requires no GPU.

## Interpretation

Privileged states are shared inputs. Training clones a geometric teacher, not native counterfactual outcomes or human preferences. The simulator pauses during model requests; simulated travel time and queued wall latency are distinct. Runtime probes retained control/physical trajectories but not every rendered pixel/probability, so matched scenes do not imply byte-identical animated views. Sampled geometry, native tracking error, limited training scenes and the asset domain constrain transfer. Contact-free arrival alone does not establish comfort, accessibility or deployment safety.

Raw runs, installed environments, local cache pointers, dataset manifests and checkpoints are excluded from Git. Curated sources/results are versioned; data and adapter archives provide portable inputs and selected-checkpoint hashes.
