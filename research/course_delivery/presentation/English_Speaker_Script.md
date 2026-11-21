# English presentation script

Total rehearsal duration: **09:47**. The spoken script contains 1127 words. Aim for roughly 150–160 words per minute; actual human recording time will vary.

**Review copy:** replace the pending group identity, names and actual work shares before recording. The supplied MP4 uses synthetic rehearsal narration; it is not a recording of the group.

## Slide 01 — Constrained local planning and vision–language guidance
**00:00–00:28**

This project studies how a wheeled service robot can share urban pedestrian space. We compare explicit local planning with vision and language guidance in three simulated street families. The main result is an improvement from geometric local selection, while the trained visual selector does not outperform that baseline. This is a rehearsal copy: our group identity, members and agreed work percentages must be completed before submission.

## Slide 02 — The question is when to wait and when to use lateral space
**00:28–01:03**

A robot can slow down for a pedestrian, but slowing alone cannot take it around an obstruction. Our question has two parts. First, does constrained local trajectory selection improve contact-free completion across spatial conditions? Second, does a compact vision–language model add value beyond geometric selection? The project combines artificial intelligence for action adaptation, data science for matched evaluation, and computational media for procedural three-dimensional simulation and visual evidence.

## Slide 03 — Three scene families define 120 matched natural conditions
**01:03–01:31**

We use intersections, straight sidewalks, and streets containing a curve. Each family has two nominal clear-width bands, two pedestrian counts, and ten fresh scene seeds. That gives one hundred and twenty conditions per method. The images are native simulator captures. Coordinates are local metres, not observations from a real city. Five and fifteen describe agent counts, not crowd density.

## Slide 04 — The extension adds lateral choices, learning and broader evidence
**01:31–02:07**

This project builds on the retained single-scene pilot. We keep its route-following and speed-forecast comparisons, but add three scene families, a constrained lateral trajectory library, an MPPI-style sampling controller, and actual multimodal adapter training. We also add training-seed checks, input removals, curve exclusion, and controlled blockages. These are project-level extensions. Pure Pursuit, local search, predictive control, LoRA and the simulator itself come from existing work.

## Slide 05 — A learned proposal always passes through geometric execution
**02:07–02:44**

The shared route provides a direction of travel. The local library offers five lateral trajectories and physical stopping. The geometric selector ranks feasible options, while the adapted model proposes one action token every second. At each tenth of a second, the execution layer checks predicted footprints, pedestrians, obstacles and walkable space. An infeasible model proposal falls back to geometric selection. If no candidate is feasible, the robot brakes. Native physics, rather than direct position changes, moves the robot.

## Slide 06 — LoRA learns geometric teacher choices from 598 decisions
**02:44–03:22**

The model is SmolVLM2 with about five hundred million base parameters. Six labels identify the five paths and stopping. We freeze the backbone and train about one point one million low-rank parameters in visual and language attention. Training uses five hundred and ninety-eight decisions, with three hundred and four validation decisions from separate scene seeds. This is supervised imitation of geometric predictions, not reinforcement learning or counterfactual trials. We train ten epochs for each seed and select checkpoints on validation only.

## Slide 07 — Seven comparisons separate tracking, local planning and adaptation
**03:22–04:04**

The comparisons answer different questions. Regulated Pure Pursuit-inspired control provides regulated path following. Speed forecasting changes timing along that route. Dynamic Window Approach-style control searches local commands. Model Predictive Path Integral-style control samples ninety-six sequences. Our geometric selector tests the new lateral candidate hierarchy. Frozen and adapted visual models test pretrained action use and task adaptation. The older controllers do not receive every new candidate filter, and the model does not receive the teacher's explicit pedestrian velocities, so attribution must remain bounded.

## Slide 08 — Strict arrival and contact-free completion are distinct outcomes
**04:04–04:43**

An episode has a one hundred and twenty second simulated budget. Strict arrival requires the native destination flag and a distance within two metres. Contact-free arrival also excludes any recorded contact during the episode. We retain failures, timeouts and contacts. The full campaign has one thousand three hundred and eighty-four formal episodes, with separate denominators for each diagnostic suite. Independent audits check more than one point three million decisions and about sixty-nine thousand model queries. Uncertainty analysis groups related scene variants.

## Slide 09 — Geometric local selection reaches 79 contact-free arrivals out of 120
**04:43–05:13**

Here are all seven natural-scene results on the same one hundred and twenty conditions. The geometric selector records seventy-nine contact-free arrivals, versus sixty-two for route-constrained speed forecasting. The primary adapted model reaches sixty-eight; the frozen model reaches zero. These results support the new local planning package in this simulator. They do not support a claim that adding a visual model is the best-performing strategy.

## Slide 10 — The supported gain is geometric; VLM guidance adds no further gain
**05:13–05:54**

The geometric package improves contact-free completion by fourteen point two percentage points over speed forecasting. Its paired interval is positive, but it is about half a second slower on ninety-three jointly successful conditions. The adapted model is nine point two percentage points below geometric selection and takes twelve point two seconds longer on eighty joint successes. These timing comparisons exclude failures. All methods share the new reference route; the geometric gain concerns the local candidate, constraint and execution package, while the learned selector shows no added benefit in this test.

## Slide 11 — Training seeds and input removals expose an unstable selector
**05:54–06:34**

Changing the training seed gives sixty-eight, eighteen and fifty-eight contact-free arrivals, all below the geometric result of seventy-nine. On twenty-four separate input-removal conditions, full input gives fourteen completions, no RGB gives thirteen, no image gives fifteen, and minimal instruction gives five. Without an image the model always proposes the centre path, while geometric checking remains active. Outside exposure is higher than with full input. These findings do not establish that vision is unnecessary. They show that task priors, fallback and small correlated data can dominate this selector.

## Slide 12 — Blockages and curve exclusion reveal limited robustness
**06:34–07:06**

The controlled blockage suite places the same existing object after reference planning. Geometric selection achieves eleven contact-free arrivals out of twenty-four; MPPI-style reaches seven and the adapted model four. On forty curve conditions, the model trained without curves reaches three contact-free arrivals, versus thirty-two after full-layout training. Removing curves also reduces the training sample count, so that difference mixes layout coverage and data volume.

## Slide 13 — Native intersection demo: all three methods complete this example
**07:06–07:41**

This intersection demonstration uses the same fixed illustrative seed for all three controllers. Each completes without recorded contact, while their simulated travel times differ. These three episodes are not part of the formal test sample. The demonstration helps explain behaviour, but it cannot establish an overall ranking.

**Video cue:** after the spoken explanation, show the 12-second excerpt. In PowerPoint, click the embedded full video if discussing it live.

## Slide 14 — Native straight-street demo: arrival alone misses important failures
**07:41–08:20**

In the straight-street example, regulated tracking arrives but records contact. The geometric selector arrives without recorded contact. The adapted model records no contact but times out. This separates arrival, contact-free completion and simply avoiding contact by waiting. A paused-looking or stationary robot should not automatically be described as safe and successful.

**Video cue:** after the spoken explanation, show the 12-second excerpt. In PowerPoint, click the embedded full video if discussing it live.

## Slide 15 — Native curve demo: the aggregate winner can still fail
**08:20–09:00**

The curve example reverses the aggregate ranking. Regulated tracking and adapted guidance complete without recorded contact, but the geometric selector times out and has substantial outside exposure. A method can lead on one hundred and twenty matched conditions and still fail on a particular scene. This is why we report footprint exposure and individual failure cases alongside overall completion.

**Video cue:** after the spoken explanation, show the 12-second excerpt. In PowerPoint, click the embedded full video if discussing it live.

## Slide 16 — Use explicit geometry now; treat learned guidance as an open result
**09:00–09:42**

Our supported conclusion is that constrained local planning improves contact-free completion in these simulated streets. We also complete real multimodal adapter training, but its additional navigation benefit is not established. The project contributes a transparent comparison across spatial conditions, rather than a claim of a new foundation model or state of the art. Important limits include privileged observations, a single-frame selector, small training diversity and approximate dynamics. Future temporal observations and better-matched supervision remain unimplemented. Code, data and records are public; model weights stay local.

## Slide 17 — References and reproducibility
**09:42–09:47**

Reference page; no additional spoken content.

