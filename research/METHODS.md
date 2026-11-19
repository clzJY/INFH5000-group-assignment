# What is implemented

The task is native wheeled point-goal navigation through pedestrian space. RGB images are recorded from the three-dimensional simulator. The robot's pose and velocity are updated by Bullet physics, never overwritten by the research controller. Pedestrians and furniture come from the installed MetaUrban assets. This study does not train perception from real street photographs.

## Shared spatial information

Every method receives simulator states: the current robot state, pedestrian positions and velocities, static-object rectangles and a common reference route. The route uses A* on an eroded native walkable union after subtracting furniture footprints. Intersection (`X`), straight (`S`) and straight-plus-curve (`SC`) are distinct procedural map compositions. Nominal clear-band widths are 2.6 and 4.6 m; crowd settings are counts of 5 and 15 agents, not density estimates.

Those numerical states feed the execution/planning layers. The VLM selector sees a current trailing-camera view and a rendered map of body outlines, without explicit velocity annotations or previous frames. Its observation is a partial projection of the teacher's state. The selector comparison includes this representation difference.

The polygon union includes the selected native sidewalk, crosswalk and near-road sidewalk/buffer regions, expanded by a declared 0.05 m geometric tolerance. Planning checks and the recorded outside-exposure metric use this same toleranced union.

## Comparisons

| Code name | Executed method | Question tested |
| --- | --- | --- |
| `rpp` | Retained Regulated Pure Pursuit-inspired tracking, proximity regulation and short projected collision stopping | Does regulated route tracking with pedestrians held fixed in its short check suffice? |
| `forecast` | Retained route-constrained speed forecasting | Is speed adaptation sufficient without lateral choices? |
| `dwa` | Retained Dynamic Window Approach-style local search | How does the prior local-search adaptation perform on the common route? |
| `mppi` | New sampling/weighting of 96 bounded control sequences | Does a more flexible sampling-based controller help? |
| `lattice` | New geometric ranking of five lateral choices and stopping | What can the same candidate/fallback hierarchy achieve without a neural selector? |
| `vlm` | Frozen SmolVLM2 action-token selection plus the new geometric fallback | Does the pretrained model alone understand these action choices? |
| `lora` | Vision/text low-rank adaptation of SmolVLM2, with the same fallback | Does task adaptation improve selection and completed navigation? |

These are project implementations, not official reproductions of RPP, DWA, MPPI, NaVILA or VLFM. The retained pilot's zero-velocity ablation remains available in the original results; it is not pooled into the new seven-method comparison. PPO is not used as the main comparison.

The first three controllers retain their original common static-body guard and do not receive the new walkable-candidate filter. Comparisons against them evaluate the combined navigation hierarchy. The `lora` versus `lattice` comparison isolates the high-level selector within the same new candidate and fallback system.

## What the model learns

SmolVLM2-500M-Video-Instruct receives a current RGB/local-map composite and a fixed instruction. The map is privileged simulator information. A–E identify five lateral route-following trajectories; F commands stopping. The next-token logits are restricted to these six labels.

The final model trains rank-8 query/value adapters in both vision and text attention, with 1,114,112 FP32 trainable parameters over frozen bfloat16 pretrained weights. The training objective is class-weighted cross-entropy on a geometric rollout teacher's choices. It does not learn from counterfactual native outcomes, human feedback or reinforcement learning. Three training seeds are evaluated separately, and a fourth adapter excludes the curve family from training and validation.

This is a VLM-guided navigation hierarchy with action-token adaptation. It is not an end-to-end navigation VLA, open-vocabulary instruction-following benchmark or semantic street-perception system.

## Executing a decision

High-level choices update every second. At every 0.1-second physics decision, the local planner recomputes bounded three-second trajectories and sampled rectangle clearances. An infeasible model proposal falls back to geometric selection. If no option is feasible, the system commands physical braking. Current boundary violations can activate an explicit recovery rule; actual exposure outside the walkable union remains a reported outcome.

These checks approximate the simulator and do not guarantee continuous safety. The simulator pauses during synchronous model requests. Simulated travel time, controller computation and queued model latency must be interpreted separately.

## Test separation

The natural suite contains 120 matched conditions per method. Input removals, training-seed variation, held-out-curve testing and post-planning furniture blockages are separate suites. The blockage wrapper moves one existing static object during initialisation; it does not move the robot or replan its reference. Previously planned pedestrian paths are not regenerated after that manipulation.

Strict arrival requires both the native destination flag and distance at most 2 m from the final reference point. Contact-free arrival additionally requires no recorded contact at any step. Waiting commands, physical standstill, pedestrian proximity and actual full-footprint walkable exposure are distinct metrics. A completed task can still have contact or boundary exposure.
