#!/usr/bin/env python3
"""Five-page proposal built from accepted, frozen fresh-test evidence."""
import json
from pathlib import Path
from build_proposal import Doc,ROOT,OUT


def build():
    base=ROOT/'outputs/route_refinement'
    evidence=json.loads((base/'test/summary.json').read_text())
    rows={r['method']:r for r in evidence['summary'] if r['density']=='all'}
    b,p,r,f=[rows[m] for m in ('baseline','predictive','route','route_intent')]
    n=b['valid'];assert all(x['requested']==20 and x['valid']==n for x in rows.values())
    d=Doc()
    d.p('Route-aware control and endpoint validity in urban robot navigation','Title')
    d.p('A mini research proposal with a frozen three-dimensional pilot',size=23)
    d.p('UCMP-MB · Week 3 · Option 1 · Individual assignment · 2 November 2026','Caption')
    d.p('1. Research question and urban relevance','Heading')
    d.p('Can a small route-consistency correction improve actual waypoint attainment in a shared pedestrian streetscape, and does a route-aware footprint shield improve pedestrian-contact outcomes beyond that correction? The application is a service robot travelling to an inspection location, stopping and recording a street view. The research separates three questions: whether the robot reached the intended place, whether it made contact, and which control change caused the difference.')
    d.image(base/'figures/mission_scene_pair.png')
    d.p('Figure 1. Actual native MetaUrban RGB: mission start and recorded streetscape after stopping (development seed 902, 15 pedestrians). The robot entered the 2 m target radius at 40.9 s, then held speed below 0.1 m/s for one second and panned the camera. Navigation and inspection had no recorded contact. RGB documents the task; the policy uses state/LiDAR.','Caption')
    d.p('Shared pavements are interaction spaces rather than empty transport corridors. Efficient movement can conflict with access, predictability and perceived comfort [2,5]. Urban informatics contributes a measurement perspective: the spatial definition of arrival, the geometric support of proximity, and the unit used to aggregate encounters determine the meaning of an apparent improvement. A route-progress flag is not equivalent to being near a specific inspection point, and absence of contact is not evidence of comfort.')
    d.p('MetaUrban supplies generated streetscapes, street furniture and embodied navigation tasks [1]. This project keeps its public PointNav PPO weights fixed [3]. It tests a transparent control wrapper, without training another network or claiming a new state-of-the-art navigation algorithm. The wheelchair-shaped embodiment matches the checkpoint; it is not a calibrated wheelchair or humanoid locomotion system.')
    d.page()
    d.p('2. Data, spatial units and measurement audit','Heading')
    d.p('Data comprise synthetic trajectories, actions, native contact flags and RGB frames from official MetaUrban source pinned to commit 6b8ff9a. Public tiny streetscape assets and pedestrian models are imported offline with recorded hashes. Coordinates are local metres, without a geographic reference system. A 0.1 s decision is the observation unit; an episode is the outcome unit; crowd size × scene seed is the matched comparison unit. Seeds are shared across crowd sizes, so 20 conditions do not imply 20 independent city layouts.')
    d.table([['Element','Specification'],['Spatial setting','Native 3D X intersection, sidewalks, crossings and furniture; object-density parameter 0.3; one layout family'],['Embodiment / input','Official wheelchair agent, four-wheel Bullet dynamics; 271-dimensional state/LiDAR input; fixed deterministic PPO'],['Crowds / time','5 or 15 native pedestrians; other moving traffic disabled; 600 steps / 60 s; identical forward-only contract'],['Development / holdout','Development seeds 900–904; fresh test seeds 200–209; 4 methods × 2 crowds × 10 seeds = 80 requested runs'],['Valid generated task','Reference-route length and start-to-endpoint distance both ≥5 m, checked before policy steps; invalid tasks retained and not replaced']],[2350,7556])
    d.p('An audit of the earlier 60-run pilot exposed outcome-definition problems. The native arrival rule uses >95% projected route completion or a short-route branch. Its nontrivial successful baseline runs ended approximately 5–17 m from the endpoint. Two matched conditions had coincident start/goal locations and one-step native success. Those original runs remain unchanged; they cannot be directly pooled with the revised outcome definition.')
    d.p('The revised primary outcome requires BOTH the native arrival flag and Euclidean endpoint distance ≤2 m. Native first-arrival is logged separately, and all methods continue past an early native flag under the same wrapper. Pedestrian contact and any-contact-free arrival are separate outcomes. SimplePedestrian bodies are tagged as vehicles in native Bullet, so pedestrian contact includes crash_vehicle in this verified pedestrian-only setup, with all raw flags retained.')
    d.p('The previous robot-circle / pedestrian-radius separation overstated some clearances and understated others: the pedestrian declares a 0.35 m radius but has a 1 × 1 m collision box. The new control uses oriented planar footprints of the native boxes. For comparability, the reported near-time fraction still uses the old circle proxy; it is neither exact box distance nor a human-comfort score. Speeds above 20 m/s are flagged as numerical anomalies and retained in primary counts.')
    d.page()
    d.p('3. Implemented methods and analytical design','Heading')
    d.table([['Method','What changes'],['PPO baseline','Original deterministic policy actions under the common forward-only contract'],['CV yield','Original constant-velocity/circle risk layer: 2 s closest approach, 0.5/1.5 m stop/slow thresholds, unchanged PPO steering'],['Route governor','Local route-consistency steering/throttle correction plus a 3 m/s cruise cap and curvature-dependent speed limit'],['Route + footprint','The same route governor plus time-aligned, route-aware footprint candidate-speed selection']],[2350,7556])
    d.p('The route governor compares PPO steering with a pure-pursuit direction toward the supplied polyline [4]. It corrects steering/throttle when the actions disagree, heading or lateral error is large, or the policy requests braking while substantial route remains. Its lookahead is at least 3 m; every correction trigger and original PPO action is logged. The full route is privileged simulator information. This is a substantive control change, not only a pedestrian speed cap, and the route-only ablation is essential to attributing any gain.')
    d.p('The footprint shield predicts candidate speeds of 0, 0.5, 1, 2 m/s and the current cruise cap. It recomputes route-following motion over 1 s at 0.1 s intervals, assuming 1.5 m/s² acceleration, 2 m/s² braking and constant current pedestrian velocities. It uses the 1.5 × 1 m ego box and 1 × 1 m pedestrian boxes: exact planar Euclidean distance when disjoint, signed separating-axis penetration when overlapping. The highest candidate meeting a 0.25 m geometric buffer is selected; release requires 0.2 s clear. These are engineering settings, not validated social distances.')
    d.p('Stopping is explicitly predicted as a candidate. In a development failure, a pedestrian continued along its preplanned path into the stopped robot. If no candidate meets the buffer and stopping predicts overlap, a moving candidate may be chosen only if its worst predicted gap improves by more than 0.1 m. Such steps are marked as having no buffer-feasible option. This last-resort heuristic provides no collision-free guarantee. Finite native wheel braking handles a stop; neither position nor velocity is overwritten.')
    d.p('All four methods share initial scene, planned route, physics, checkpoint and time budget. Source and parameter hashes were frozen before fresh testing. Hypothesis H1 is that route correction increases strict arrival; H2 is that adding footprint prediction reduces pedestrian contact relative to route correction alone. Paired rescue/regression counts assess completion, and travel-time differences use only jointly successful conditions. Descriptive episode counts are reported without treating repeated crowd-size conditions as independent significance tests.')
    d.p('The upstream crowd manager uses ORCA-based path generation [6]; its preplanned pedestrian motion does not establish realistic reciprocal responses to the robot. Camera recording is repeated separately and checked against physics-only trajectories. Unit tests cover diagonal box geometry, turning, acceleration/braking, crossing timing, route correction and the unsafe-stop case.')
    d.page()
    d.p('4. Frozen fresh-test evidence','Heading')
    table=[['Method',f'Strict / {n}','Native flag','Ped. contact','Contact-free strict']]
    for method,name in [('baseline','PPO'),('predictive','CV yield'),('route','Route governor'),('route_intent','Route + footprint')]:
        x=rows[method];table.append([name,x['strict_goals'],x['native_goals'],x['pedestrian_contacts'],x['contact_free_goals']])
    d.table(table,[2300,1400,1600,1600,3006])
    d.p(f'Each method had 20 requested matched conditions and {n} valid generated tasks; {20-n} were rejected by the predeclared route gate. Contacts are episode counts. Strict arrival requires ≤2 m endpoint distance in addition to the native flag. Native-only counts are included to expose the sensitivity to the outcome definition.','Caption')
    d.image(base/'figures/fresh_outcomes.png')
    d.p('Figure 2. All valid fresh-test outcomes after the pre-test freeze. Failed and contact episodes are retained. These bars describe one synthetic layout family and ten seeds; they do not establish real-world safety or generalization.','Caption')
    d.p(f"Strict arrivals were {b['strict_goals']}/{n} for PPO, {p['strict_goals']}/{n} for CV yielding, {r['strict_goals']}/{n} for route correction and {f['strict_goals']}/{n} for route plus footprint prediction. Pedestrian contacts were {b['pedestrian_contacts']}, {p['pedestrian_contacts']}, {r['pedestrian_contacts']} and {f['pedestrian_contacts']}, respectively. The corresponding contact-free strict arrivals were {b['contact_free_goals']}, {p['contact_free_goals']}, {r['contact_free_goals']} and {f['contact_free_goals']}.")
    contrast=next(x for x in evidence['paired'] if x['control']=='baseline' and x['method']=='route')
    extra=next(x for x in evidence['paired'] if x['control']=='route' and x['method']=='route_intent')
    d.p(f"Against PPO, route correction rescued {contrast['rescued']} strict-completion conditions and lost {contrast['regressed']}. Adding footprint prediction to route correction rescued {extra['rescued']} and lost {extra['regressed']}. This ablation separates route-following gains from the incremental risk-layer effect. A successful development video is therefore an illustration of mechanism, not the aggregate result.")
    d.p(f"The footprint layer raised mean legacy-proxy near-time exposure from {100*r['mean_near_fraction']:.2f}% to {100*f['mean_near_fraction']:.2f}%. On the same {extra['jointly_successful_n']} successful conditions it added {extra['mean_joint_delay_s']:.2f} s on average. Fewer contacts therefore do not imply less close exposure or greater comfort. The route correction gate was active on {100*f['mean_route_correction_fraction']:.1f}% of full-method steps, confirming that the gain involves substantial action correction, not merely a changed risk threshold.")
    if any(x['physical_anomalies'] for x in rows.values()):
        d.p(f"Numerical-anomaly episodes remained in primary counts: {b['physical_anomalies']}, {p['physical_anomalies']}, {r['physical_anomalies']} and {f['physical_anomalies']} by method.")
    else:
        d.p('No fresh task was rejected or flagged with the prespecified numerical-anomaly threshold. All failed and contact episodes remain in the results.')
    d.page()
    d.p('5. Proposed extension, uncertainty and implications','Heading')
    if r['strict_goals']>b['strict_goals']:
        d.p('The pilot supports H1 within the tested configuration: route-consistency correction increased physical endpoint attainment. It does not show that all gains came from better pedestrian prediction. The full-route input and action correction explain an important part of the advantage and must be controlled in any extension.')
    else:
        d.p('The pilot does not establish H1 as a general improvement. Its main contribution is a reproducible separation of endpoint validity, route-following behavior and pedestrian-risk intervention, with failures retained for the next design stage.')
    if f['pedestrian_contacts']<r['pedestrian_contacts'] and f['strict_goals']>=r['strict_goals']:
        d.p('The observed footprint-layer contrast is promising, but the small paired sample cannot establish broad safety or comfort. The next study should test whether the contact reduction persists when perception and human behavior are less idealized.')
    else:
        d.p('The footprint layer does not provide a uniform contact/completion improvement over route correction alone. H2 remains unresolved or unsupported in this pilot. More precise geometry alone is insufficient when prediction errors and the timing of stopping change an encounter; this is a concrete target for the next experiment.')
    d.p('A feasible extension uses two layout families, two crowd sizes, twenty new seeds (300–319) and four methods: 320 runs. Parameters would be developed on separate scenes, then frozen. The study would vary the prediction horizon, geometric buffer and pedestrian-velocity error in a prespecified sensitivity analysis, retain route-only control, and compare endpoint attainment, contacts, waiting and close-exposure duration. Confidence intervals should resample scene seeds as clusters. A later perception-based condition would replace exact states before any real-world interpretation.')
    d.p('Limitations include one small asset profile, a single pretrained policy, ideal state access and route knowledge, simplified four-wheel dynamics, short trajectories and weakly responsive pedestrians. The 2 m arrival radius is an operational pilot definition, not evidence that an inspection image is useful. Synthetic local coordinates contain no personal data. A future public-space deployment would require consent-aware recording, retention limits, accessibility testing and consultation with people with diverse mobility needs. Geometry cannot substitute for their assessment of comfort [2,5].')
    d.p('References','Heading')
    refs=[
        '[1] Wu, W. et al. (2024). MetaUrban: An Embodied AI Simulation Platform for Urban Micromobility. arXiv:2407.08725. https://arxiv.org/abs/2407.08725',
        '[2] Kruse, T., Pandey, A. K., Alami, R. & Kirsch, A. (2013). Human-aware robot navigation: A survey. Robotics and Autonomous Systems 61, 1726–1743. doi:10.1016/j.robot.2013.05.007.',
        '[3] Schulman, J. et al. (2017). Proximal Policy Optimization Algorithms. arXiv:1707.06347. https://arxiv.org/abs/1707.06347',
        '[4] Coulter, R. C. (1992). Implementation of the Pure Pursuit Path Tracking Algorithm. CMU-RI-TR-92-01, Carnegie Mellon University.',
        '[5] Francis, A. et al. (2023). Principles and Guidelines for Evaluating Social Robot Navigation Algorithms. arXiv:2306.16740. https://arxiv.org/abs/2306.16740',
        '[6] van den Berg, J., Guy, S. J., Lin, M. & Manocha, D. (2011). Reciprocal n-body collision avoidance. Robotics Research, 3–19. doi:10.1007/978-3-642-19457-3_1.'
    ]
    for ref in refs:d.p(ref,size=18)
    path=OUT/'Week3_Streetscape_Research_Proposal_v2.docx';d.save(path);print(path)


if __name__=='__main__':build()
