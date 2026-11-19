"""Generate a completed short article from independently audited result files."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'research/results';P=ROOT/'research/paper'
NAMES={'rpp':'RPP-inspired','forecast':'Speed forecast','dwa':'DWA-style','mppi':'MPPI-style','lattice':'Rule local planner','vlm':'Frozen VLM','lora':'Adapted VLM','lora_s1':'Adapted VLM, seed 1','lora_s2':'Adapted VLM, seed 2','lora_no_rgb':'No RGB','lora_no_image':'No visual input','lora_no_language':'Minimal instruction','lora_holdout':'Curve held out from training','lora_curve':'Full training, curve test subset'}

def load(path):return json.loads(path.read_text())
def escaped(s):return str(s).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def table(rows,caption,columns):
    head=' & '.join(k for k,_ in columns)+r' \\ \midrule'+'\n'
    body='\n'.join(' & '.join(fn(r) for _,fn in columns)+r' \\' for r in rows)
    return r'\begin{table}[tb]\centering\small\caption{'+caption+r'}\begin{tabular}{'+('l'+'r'*(len(columns)-1))+r'}\toprule'+'\n'+head+body+'\n'+r'\bottomrule\end{tabular}\end{table}'

def main():
    audit=load(R/'core/audit.json');assert audit['passed'] and audit['episodes']==840
    for name in ('challenge','ablations','variation','holdout'):assert load(R/name/'audit.json')['passed']
    core=load(R/'core/summary.json');allrows={r['method']:r for r in core if r['map']=='all'};f=allrows['lora'];rule=allrows['lattice'];base=allrows['vlm']
    episodes=load(R/'core/episodes.json')
    for method,row in allrows.items():row['ped_contacts']=sum(bool(r.get('pedestrian_contact')) for r in episodes if r['method']==method)
    paired=load(R/'core/paired.json');pair=next(x for x in paired if x['control']=='lattice')
    challenge=[r for r in load(R/'challenge/summary.json') if r['map']=='all'];ch={r['method']:r for r in challenge}
    ablations=[r for r in load(R/'ablations/summary.json') if r['map']=='all'];ab={r['method']:r for r in ablations}
    noimage_proposals=load(R/'ablations/choice_diagnostics.json')['modes']['lora_no_image']
    assert noimage_proposals['choice_counts'][2]==noimage_proposals['queries']
    variation=[r for r in load(R/'variation/summary.json') if r['map']=='all'];hold=next(r for r in load(R/'holdout/summary.json') if r['map']=='all')
    arrival_flags=load(R/'core/arrival_flag_diagnostic.json')['methods']
    seed_counts=[f['clean'],*[r['clean'] for r in variation]]
    replacements={method:sum(r['query_override_fraction'] for r in episodes if r['method']==method)/sum(r['method']==method for r in episodes) for method in ('lora','vlm')}
    trained=load(R/'training/seed0/training.json');offline=load(R/'offline_validation.json');latency=load(R/'latency_probe.json')
    contrasts=load(R/'core/additional_contrasts.json')['comparisons']
    geometric=next(r for r in contrasts if r['method']=='lattice' and r['control']=='forecast')
    sensitivity=next(r for r in contrasts if r['method']=='lora' and r['control']=='lattice')['seed_only']
    forecast=allrows['forecast']
    geometric_text=(f"The new geometric selector records {rule['clean']}/{rule['n']} contact-free arrivals versus {forecast['clean']}/{forecast['n']} for route-constrained speed forecasting. "
        f"The additional descriptive contrast is {geometric['clean_delta_pp']:+.1f} percentage points (95\\% family--seed bootstrap interval {geometric['family_seed']['interval_95_pp'][0]:+.1f} to {geometric['family_seed']['interval_95_pp'][1]:+.1f}). "
        f"Pedestrian-contact episodes decrease from {forecast['ped_contacts']} to {rule['ped_contacts']}. "
        f"On {geometric['joint_successes']} jointly successful conditions, geometric selection changes simulated travel time by {geometric['joint_delay_s']:+.2f} s (new minus forecast). "
        'This comparison tests the combined candidate/geometry hierarchy and does not isolate a single submodule.')
    abstract_geometry=(f"Geometric local selection achieved {rule['clean']}/{rule['n']} contact-free arrivals, versus {forecast['clean']}/{forecast['n']} for route-constrained speed forecasting. ")
    total=sum(load(R/name/'audit.json')['episodes'] for name in ('core','challenge','ablations','variation','holdout'))
    delta=f['clean']-rule['clean'];direction='higher' if delta>0 else 'lower' if delta<0 else 'identical'
    finding=(f"The adapted model recorded {f['clean']}/{f['n']} contact-free arrivals, compared with {rule['clean']}/{rule['n']} for rule-based local selection and {base['clean']}/{base['n']} for the unadapted model. "
             f"Its paired contact-free difference from the rule planner was {pair['clean_delta_pp']:+.1f} percentage points (95\\% scene-cluster bootstrap interval {pair['interval_95_pp'][0]:+.1f} to {pair['interval_95_pp'][1]:+.1f}).")
    if pair['interval_95_pp'][0]>0:
        conclusion='The paired improvement supports further evaluation of learned selection within these simulated conditions.'
    elif pair['interval_95_pp'][1]<0:
        conclusion='Adapted guidance reduces contact-free completion relative to geometric selection in this tested suite.'
    else:
        conclusion='The study does not establish an added completion benefit from VLM guidance over geometric selection.'
    timing=(f"On {pair['joint_successes']} jointly successful natural conditions, adapted guidance changes simulated travel time by {pair['joint_delay_s']:+.2f} s relative to rule selection (adapted minus rule). "
            'This conditional comparison excludes failures and is not an unconditional efficiency ranking.') if pair['joint_successes'] else 'There are no jointly successful adapted/rule conditions, so a paired travel-time estimate is not reported.'
    columns=[('Method',lambda r:NAMES[r['method']]),('Strict',lambda r:f"{r['strict']}/{r['n']}"),('Contact-free',lambda r:f"{r['clean']}/{r['n']}"),('Contact',lambda r:str(r['contacts'])),('Wait (s)',lambda r:f"{r['waiting_s']:.1f}"),('Outside (\\%)',lambda r:f"{100*r['outside_fraction']:.2f}")]
    rows=[allrows[m] for m in ['rpp','forecast','dwa','mppi','lattice','vlm','lora']]
    main_columns=columns[:4]+[('Ped. contact',lambda r:str(r['ped_contacts']))]+columns[4:]
    main_table=table(rows,'Natural-scene results on 120 matched conditions per method. Contact counts episodes with any contact; pedestrian contact is a subset. Outside is mean sampled footprint exposure outside the declared walkable union.',main_columns)
    challenge_table=table(challenge,'Controlled post-planning blockage suite, reported separately from natural scenes. All methods use the same obstacle placement and fixed reference.',columns[:5])
    ablation_table=table(ablations,'Input removal with the same adapted model, matched conditions and geometric fallback. These are inference-time distribution shifts, not separately trained models.',columns)
    curve=next(r for r in core if r['method']=='lora' and r['map']=='SC')
    seed_table=table([f,*variation,dict(curve,method='lora_curve'),hold],'Training-seed and held-out-layout checks. The two curve-only rows share 40 test conditions; the first three rows use all 120 natural conditions.',columns[:4])
    offline_names={'vlm':'Frozen VLM','lora':'Adapted VLM','no_rgb':'No RGB','no_image':'No visual input','minimal_language':'Minimal instruction'}
    offline_rows=[dict(mode=k,**v) for k,v in offline['results'].items()]
    offline_table=table(offline_rows,'Validation agreement with geometric teacher labels (304 decisions). Balanced recall averages the six action classes; this is not closed-loop task success.',[
        ('Input/model',lambda r:offline_names[r['mode']]),
        ('Accuracy (\\%)',lambda r:f"{100*r['accuracy']:.1f}"),
        ('Balanced recall (\\%)',lambda r:f"{100*r['balanced_accuracy']:.1f}"),
        ('Same as full (\\%)',lambda r:f"{100*r['action_agreement_with_full']:.1f}" if 'action_agreement_with_full' in r else '--')])
    strata=load(R/'core/spatial_strata.json')
    spatial_table=table([dict(method=m) for m in ('rpp','lattice','lora')],
        'Contact-free arrival by nominal clear-width band and pedestrian count, pooled descriptively across three families (30 conditions per cell). These are simulated spatial factors, not citywide prevalence estimates.',
        [('Method',lambda r:NAMES[r['method']])]+[
        (f'{label}, {n} people',lambda r,w=w,n=n:next(str(x["clean"])+"/"+str(x["n"]) for x in strata if x['method']==r['method'] and x['map']=='all' and x['width']==w and x['pedestrians']==n))
        for w,label in [('narrow','2.6 m'),('wide','4.6 m')] for n in (5,15)])
    text=r'''\documentclass[10pt,a4paper]{article}
\usepackage[margin=18mm]{geometry}
\usepackage{graphicx,booktabs,amsmath,amssymb,microtype,enumitem,float}
\usepackage[hidelinks]{hyperref}
\usepackage{caption}
\captionsetup{font=small,labelfont=bf}
\setlength{\parskip}{3pt}\setlength{\parindent}{0pt}
\setlength{\textfloatsep}{11pt}\setlength{\floatsep}{9pt}
\title{Constrained Local Planning and Vision--Language Guidance for Urban Robot Navigation\\\large A Matched Three-Scene Simulation Study}
\author{INFH5000 Research Project}
\date{November 2026}
\begin{document}\maketitle
\begin{abstract}
Service robots must make progress through pedestrian spaces while avoiding obstruction and contact. We test constrained local planning and ask whether a compact vision--language model (VLM) adds value to geometric action selection. Native three-dimensional MetaUrban experiments cover intersections, straight sidewalks and curved streets, with two clear-width settings and two pedestrian counts. A shared reference route and actuator interface support seven methods on 120 matched conditions. Low-rank adaptation (LoRA) trains SmolVLM2 on geometric teacher choices, using one current color (RGB) camera image, a privileged local map and a fixed instruction. All proposed actions are revalidated before execution. '''+abstract_geometry+f"The adapted selector reached {f['clean']}/{f['n']} contact-free outcomes and was {abs(pair['clean_delta_pp']):.1f} percentage points below geometric selection. "+r''' Separate controlled blockages, input removals, training seeds and a held-out-layout check probe the contributions and limits of the hierarchy. The study supports local planning within these simulated conditions while exposing limits of this single-frame learned selector.
\end{abstract}

\section{Introduction}
A robot sharing a pavement with people must decide when to continue, wait or change its local path. Urban space matters because crossings connect otherwise separated regions, street furniture reduces usable clearance, and corners change the trajectories a wheeled robot can execute. These conditions connect an urban informatics question about shared spatial resources to a measurable navigation problem. Arrival alone cannot establish acceptable public-space behaviour: contact, geometric exposure and obstruction must be considered separately \cite{francis}.

A route-constrained speed layer changes when a robot moves, but cannot choose a lateral path around a local obstruction. This motivates a richer action space: a blocked robot may need a different local trajectory, not only a different speed. We ask whether vision--language guidance contributes beyond an explicit trajectory library and geometric constraints, and how that contribution changes across spatial conditions. The question concerns action selection under shared privileged state; it does not evaluate visual perception from RGB alone.

The completed work extends the simulator to three scene families, implements a clearance-aware route and local trajectory hierarchy, adapts a pretrained multimodal transformer to discrete navigation actions, and evaluates the components under matched initial conditions. Its contribution is the implemented system and comparative evidence, including failure and input-removal results. We do not claim a new foundation-model architecture or a reproduction of a published navigation vision--language--action (VLA) model.

\section{Related Work}
MetaUrban provides procedural urban micromobility scenes and native robot/pedestrian simulation \cite{metaurban}. Classical controllers remain relevant: Regulated Pure Pursuit (RPP) changes speed along a path \cite{rpp}; the Dynamic Window Approach (DWA) searches local motion commands \cite{dwa}; Model Predictive Path Integral (MPPI) control weights sampled control sequences \cite{mppi}. Our versions are local adaptations with a common route and speed adapter, rather than complete official implementations.

Vision--language approaches operate at different levels of a navigation hierarchy. Vision--Language Frontier Maps (VLFM) uses semantic values to guide exploration \cite{vlfm}, while NaVILA separates language-expressed navigation actions from learned locomotion \cite{navila}. These systems motivate separating a semantic decision from its execution, but solve tasks different from our constrained wheeled point-goal study. Learning risk for candidate planning, as in Learning-Risk Model Predictive Control (LR-MPC), is also established \cite{lrmcp}. We use the compact SmolVLM family \cite{smolvlm} and low-rank adaptation \cite{lora} to test whether a small pretrained model can make useful local choices in this particular hierarchy.

\section{Data, Scenarios and Evaluation}
The experiment uses MetaUrban with its tiny scene-asset profile and native pedestrian models. The robot is a wheeled wheelchair-shaped model, controlled through native Bullet steering, throttle and brake operations. Its pose and velocity are never overwritten during a rollout. The three map families are an intersection, a straight street and a straight-plus-curve composition (Fig.~\ref{fig:scenes}).

The nominal clear sidewalk bands are 2.6 and 4.6 m, with five or fifteen pedestrians per condition. Crowd size is an agent count, not people per square metre. Ten fresh scene seeds per family yield $3\times2\times2\times10=120$ natural conditions. Scene identity is the family--seed pair; width and crowd variants remain grouped in inference. Coordinates are local metres, not geographic observations or representative city samples. All execution layers receive the common reference, robot geometry, current pedestrian states and static footprints. The visual selector receives native RGB and a rendered map of current geometry, rather than the complete numerical state.
The street-object density parameter is fixed at 0.15; the actual arrangement and occupied footprints vary by scene.

\begin{figure}[tb]\centering\includegraphics[width=\linewidth]{../results/figures/scene_atlas.png}\caption{Recorded native views and spatial layouts for the three scene families. Lower panels show the shared reference and the executed rule-planner trajectory for the fixed illustration condition (wide, five pedestrians, seed 1600). All RGB panels are native simulator captures.}\label{fig:scenes}\end{figure}

Training uses whole-scene seeds distinct from validation and test. Initial natural-scene collection was supplemented with controlled blockages to diversify action labels. A small existing street object is relocated approximately 20 m along the fixed reference during task initialisation, after global planning; the robot itself is not moved. This creates a new local obstruction without replanning the reference. Blockage training, validation and testing use disjoint seeds, and their outcomes are reported separately from natural scenes.

The blockage test has $3\times2\times4=24$ conditions per method: three families, two crowd counts and four fresh seeds, using only the wider clear band. Input removal uses 24 further conditions per variant across both widths, both counts and two separate seeds. These smaller diagnostic suites have different denominators and purposes from the main natural sample.

Each formal episode has a 120 s simulated budget, a 0.1 s decision interval and a 2 m/s maximum target speed. Strict arrival requires both the simulator arrival flag and endpoint distance at most 2 m. Contact-free arrival additionally excludes recorded pedestrian, object, building and sidewalk contacts. We retain raw native flags; pedestrian contact includes both relevant native human and vehicle tags, with other traffic disabled. Failed, timeout and contact episodes remain in the denominator. Waiting measures stop commands; physical standstill uses measured speed below 0.1 m/s. We also record the fraction of post-step oriented footprints outside the declared walkable union, since a native out-of-road flag alone can miss geometric deviations.

Travel-time comparisons use jointly successful conditions and state their denominator. Contact-free differences use paired scene-cluster bootstrap intervals with 10,000 resamples, keeping width/crowd variants together. A sensitivity analysis additionally blocks all families and spatial variants sharing a scene-generation seed. Degenerate intervals do not establish population equivalence. Model training seeds describe parameter variation rather than additional independent city scenes. Recorded outcome metrics are independently recomputed from per-step logs, and initial physical-condition fingerprints are checked across methods. Matched conditions do not guarantee byte-identical animated views.

\section{Navigation Hierarchy and Adaptation}
\subsection{Reference and local planning}
A shared A* route is computed on native sidewalk/crosswalk-side geometry after subtracting static footprints, using a 0.4 m raster and a 0.78 m erosion radius. The native walkable union has a declared 0.05 m geometric tolerance; both planning and logged outside exposure use this same expanded union. Visibility shortcuts remain inside the eroded region. The route is guidance rather than a proof of vehicle executability; oriented footprint and motion checks are still required.
If the eroded grid is empty or disconnected, the implementation retains the original reference and records that fallback. Endpoints are retained with short grid connectors. Such tasks remain in the evaluation.

The retained RPP-inspired controller regulates tracking speed using proximity and a short projected collision check that holds pedestrian positions fixed. The route-forecast controller instead predicts constant-velocity pedestrians while selecting a route-following speed. The DWA-style controller searches bounded speed/steering pairs. These three retain their common static-body guard and do not use the new walkable-candidate filter. Comparisons against them therefore evaluate the combined hierarchy; learned versus rule selection within the new hierarchy is the controlled test of the model's additional contribution.

The local library contains five lateral offsets ($-1.5,-0.75,0,0.75,1.5$ m) and physical stopping. Bounded bicycle rollouts follow the offset reference for 3 s, sampling every 0.15 s with acceleration, braking and steering-rate limits. Candidate occupied rectangles are compared with static geometry and constant-velocity pedestrian footprints. Feasible predictions preserve a 0.25 m pedestrian buffer and 0.1 m static buffer. The rule score rewards route-arc progress and clearance and penalises cross-track/lateral deviation and switching. High-level rule and model choices update at 1 Hz; feasibility and actuation are re-evaluated at 10 Hz.

Native motion can deviate from a prediction. If a current footprint partly crosses a boundary, a recovery candidate must finish inside and cannot increase its initial outside area by more than 0.005 m$^2$. This recovery rule is declared and the actual outside exposure remains in the results. When a proposed model action is infeasible, the system uses the rule choice; when none is feasible it commands physical stopping. Neither stopping nor the sampled checks guarantee future collision avoidance.

The MPPI-style comparison samples 96 temporally correlated, bounded 3 s control sequences and forms an exponentially weighted sequence from feasible scores. It validates this weighted sequence and otherwise uses the best feasible sample. The implementation is a practical sampling-based adaptation and does not claim all properties of canonical MPPI.

\begin{figure}[tb]\centering\includegraphics[width=\linewidth]{../results/figures/pipeline.png}\caption{The tested hierarchy. The model receives native RGB, an explicitly privileged local-map panel and a fixed instruction, then scores six action tokens. It does not replace geometric checking, control or native dynamics.}\label{fig:method}\end{figure}

\subsection{Vision--language action selection}
The pretrained model is SmolVLM2-500M-Video-Instruct. Its visual input is a 640$\times$320 composite: a native trailing-camera view on the left and a local map on the right. The map shows walkable geometry, current bodies, the reference and labelled candidates; it does not display oracle outcomes, teacher scores or explicit velocity annotations. A fixed English instruction asks the robot to reach the inspection point, remain in allowed space and avoid people and furniture. We restrict the next-token logits to A--F rather than interpreting free-form explanations as executable actions.

Query/value adapters modify both vision- and language-transformer attention. Rank is 8 with scaling 16; original pretrained weights remain frozen. Training minimises class-weighted cross-entropy for geometric teacher choices. Those labels come from model rollouts, not observed counterfactual successes or human preferences. Consequently, teacher imitation alone cannot establish improvement over the teacher.

The final training set contains '''+str(trained['train_samples'])+r''' sampled decisions, with '''+str(trained['validation_samples'])+r''' validation decisions after repeated-action thinning. 32-bit floating-point (FP32) adapter parameters and optimizer states are used over a frozen bfloat16 base. Adam with decoupled weight decay (AdamW) uses learning rate $3\times10^{-4}$ for ten epochs and three training seeds. Checkpoint selection uses the mean of validation accuracy and class-balanced recall, never formal test performance. A separate held-out model excludes curve scenes from both training and validation. Only the small adapter matrices are optimized, totalling 1,114,112 trainable parameters. A local RTX 5880 executes the model; the original CPU simulator environment remains separate.

\section{Results}
\subsection{Matched natural-scene comparisons}
'''+finding+' '+conclusion+'\n'+main_table+r'''
'''+geometric_text+r'''
Blocking all families sharing each scene-generation seed gives a model-minus-rule sensitivity interval of '''+f"{sensitivity['interval_95_pp'][0]:+.1f} to {sensitivity['interval_95_pp'][1]:+.1f}"+r''' percentage points across ten seed blocks. This checks the dependence assumption of the primary family--seed interval rather than providing another independent sample.
Arrival and contact-free arrival must be read together with waiting and actual walkable exposure (Table~1). A method can finish after contact or take a short path that leaves the intended pedestrian space. The sampled outside metric is therefore reported independently of the native success flag. Figure~\ref{fig:results} separates the overall counts from scene-family variation rather than treating one average as a universal controller ranking. '''+timing+r'''

The native arrival flag appeared in '''+str(arrival_flags['lattice']['native_flag_any'])+r''' geometric-selector episodes and '''+str(arrival_flags['lora']['native_flag_any'])+r''' adapted-model episodes, whereas the strict criterion counts '''+str(rule['strict'])+' and '+str(f['strict'])+r''', respectively. Every recorded entry within 2 m also satisfied the native flag. Thus the distance check removes broad-flag positives without missing a recorded physical entry in this sample. These are diagnostics on the executed trajectories, not reruns with different termination rules.

\begin{figure}[tb]\centering\includegraphics[width=\linewidth]{../results/figures/main_results.png}\caption{Natural-scene strict/contact-free arrival and scene-family contact-free outcomes. All seven methods use 120 matched conditions; the right panel has 40 per family. The chart reports episode counts as percentages, without implying rare-event safety or population equivalence.}\label{fig:results}\end{figure}
'''+spatial_table+r'''
The width--crowd breakdown links controller outcomes to the amount of nominal pedestrian space and the number of moving agents. Actual effective clearance also depends on furniture and corners; a wider nominal band does not make every local manoeuvre feasible. These small stratified counts are descriptive and do not isolate independent causal effects of urban design.
The straight family has '''+str(next(r['clean'] for r in core if r['method']=='lattice' and r['map']=='S'))+r'''/40 contact-free geometric completions, compared with '''+str(next(r['clean'] for r in core if r['method']=='lattice' and r['map']=='SC'))+r'''/40 in the curve family. This ordering warns against equating turning complexity with overall difficulty: route exposure, available space and local encounters also differ between the generated layouts.

\subsection{Controlled blockages and input dependence}
The separate post-planning blockage suite records '''+f"{ch['lora']['clean']}/{ch['lora']['n']}"+r''' contact-free arrivals for adapted guidance, compared with '''+f"{ch['lattice']['clean']}/{ch['lattice']['n']}"+r''' for rule selection. These conditions directly exercise a locally obstructed reference; they are not pooled with the natural sample to enlarge a headline success rate.
'''+challenge_table+r'''
Removing native RGB retains the privileged map; removing all visual content also removes that map, while the geometric execution layer remains active. Replacing the task instruction with a minimal token-selection request tests sensitivity to that wording, not general language-following ability. These diagnostic removals are distribution shifts for the same checkpoint. The full model obtains '''+f"{ab['lora']['clean']}/{ab['lora']['n']}"+r''' contact-free arrivals, versus '''+f"{ab['lora_no_rgb']['clean']}/{ab['lora_no_rgb']['n']}"+r''' without RGB and '''+f"{ab['lora_no_image']['clean']}/{ab['lora_no_image']['n']}"+r''' without any visual content. Similar closed-loop outcomes under removal can reflect action priors and geometric fallback, so they cannot be presented as evidence that every modality contributes.
'''+ablation_table+r'''
With the blank image, all '''+str(noimage_proposals['queries'])+r''' proposals select C, the centre candidate. This variant therefore acts as a constant-centre proposal policy with the same privileged geometric checking. Its outside exposure is '''+f"{100*ab['lora_no_image']['outside_fraction']:.2f}"+r'''\%, versus '''+f"{100*ab['lora']['outside_fraction']:.2f}"+r'''\% with full input. The extra contact-free arrival in this small sample comes with greater boundary exposure; it does not establish a uniformly better policy.
Offline validation agreement is '''+f"{100*offline['results']['lora']['accuracy']:.1f}"+r'''\% for the adapted model and '''+f"{100*offline['constant_accuracy']:.1f}"+r'''\% for the constant-label comparator. Action agreement after input removal is retained in the accompanying result file. We distinguish an action-token prediction from the action actually executed after constraint checks; override rates help explain why weak proposals need not translate directly into contact.
The mean episode-level fraction of physics decisions where the held token changed after geometric revalidation is '''+f"{100*replacements['lora']:.1f}"+r'''\% for adapted guidance and '''+f"{100*replacements['vlm']:.1f}"+r'''\% for the frozen model. This measures discrete action-index changes, not a count of collision events.
'''+offline_table+r'''
Class-level checks reveal uneven learning: action D (+0.75 m relative to the reference) has zero recall on its ten validation examples. Thus the aggregate agreement cannot establish that all manoeuvres are learned. The 304 validation decisions contain 284 unique images, with no image hash shared between training and validation. The published selection metric retains the original decision sample; exact-image deduplication is a separate diagnostic, and correlated views remain a limitation.

\subsection{Training variation, transfer and execution cost}
'''+seed_table+r'''
The held-out curve adapter records '''+f"{hold['clean']}/{hold['n']}"+r''' contact-free arrivals, compared with '''+f"{curve['clean']}/{curve['n']}"+r''' for the fully trained adapter on those same curve conditions. This evaluates one excluded family within the same simulator/asset domain; it is not transfer to another city or a real robot. Holding out the family also reduces training to 432 decisions, so this comparison cannot separate layout diversity from training volume. The three training seeds share test scenes and are reported separately rather than counted as independent environments.
Across the three adapter initialisations, contact-free completion ranges from '''+str(min(seed_counts))+' to '+str(max(seed_counts))+r''' out of 120. All three remain below the geometric selector in this experiment. The spread constrains claims of stable learning under the small scene-level training set.

The mean episode-level 95th-percentile controller latency for adapted guidance is '''+f"{f['p95_wall_ms']:.1f}"+r''' ms, compared with '''+f"{rule['p95_wall_ms']:.1f}"+r''' ms for rule selection. This includes synchronous model requests on decision steps that query the model. Simulated time pauses during inference, so travel duration is not an end-to-end real-time deployment measurement. A separate batch-one probe (50 measurements per model) records adapted preprocessing/prediction median '''+f"{latency['modes']['lora']['median_ms']:.1f}"+r''' ms and 95th percentile '''+f"{latency['modes']['lora']['p95_ms']:.1f}"+r''' ms without the HTTP queue or active native rollouts. Fresh-process construction and adapter loading take '''+f"{latency['model_constructor_and_adapter_load_s']:.2f}"+r''' s with warm filesystem caches and imports excluded; this is a shared-machine measurement. Overall, the completed formal evaluation contains '''+str(total)+r''' episodes across the distinct suites; initial development and training collection are not counted as formal test evidence.

Campaign computation times include shared-server queueing and changing host load; they are not isolated hardware speed rankings.

\section{Discussion and Limitations}
The central comparison is learned versus rule selection with the same candidates and geometric execution layer. Improvement relative to a frozen instruction-tuned model establishes the value of task adaptation, but cannot by itself establish a benefit over classical planning. Likewise, introducing a different reference route, a larger action space and a model at once would confound attribution; all main methods therefore share the new route, and the rule/model pair shares candidate generation and fallback.

The selector comparison also includes an observation-design difference: the geometric teacher uses pedestrian velocity, while the model sees one image and current map outlines. A single frame may not identify the velocity-dependent teacher choice. This may constrain imitation and closed-loop performance; temporal views or velocity-annotated maps are appropriate follow-up comparisons. The present results evaluate this complete selector design rather than separating architecture from observation information.

The study links urban spatial conditions to movement decisions through explicit geometry and trajectories. Its practical value is a reproducible way to ask whether a robot should wait or use available lateral space under different street structures. It does not measure pedestrian inconvenience, perceived comfort or accessibility. Those outcomes require responsive human behaviour and suitable human-centred evaluation \cite{francis}. Native pedestrians follow simulator-generated motion, not a representative human population; controlled street-object placement is an experimental manipulation.

Several limits constrain the interpretation. The visual model receives a privileged map, the instruction is fixed, and a single current image provides no explicit temporal visual history. Training imitates a geometric teacher and uses relatively few whole-scene seeds despite many correlated decisions. Footprints, pedestrian forecasts and bicycle predictions approximate native geometry/dynamics, and a recovery rule permits transient boundary violation. The benchmark uses one asset collection, one robot morphology and three related procedural map families. None of these results proves continuous collision avoidance or real-world robustness.

\section{Conclusion}
We completed a three-scene native study with constrained local trajectories, actual multimodal adapter training and matched classical comparisons. '''+abstract_geometry+f"Adding the adapted selector produced {f['clean']}/{f['n']} contact-free arrivals, below the geometric selector."+r''' Further work should test temporal observations, better-matched supervision and broader scene coverage before inferring a benefit from visual guidance.

\paragraph{Reproducibility and AI assistance.}
Code, frozen protocols, training records, checkpoint identities, result tables and native demonstration recordings accompany this article in the project repository. Model weights are retained locally. Codex assisted with implementation, experiment orchestration, analysis and manuscript preparation under the author's research directions. The final record contains five archived pre-action simulator-initialisation faults and eighteen administratively interrupted incomplete attempts; all were resumed under the same fixed conditions, separately from completed navigation outcomes. All numerical claims in this article derive from recorded execution and independent log checks; generative street images or invented observations are not used.

\begin{thebibliography}{10}\footnotesize\setlength{\itemsep}{1pt}
\bibitem{metaurban} W. Wu et al. MetaUrban: An Embodied AI Simulation Platform for Urban Micromobility. ICLR (2025).
\bibitem{francis} A. Francis et al. Principles and Guidelines for Evaluating Social Robot Navigation Algorithms. ACM THRI 14(2), Article 34 (2025). doi:10.1145/3700599.
\bibitem{rpp} S. Macenski et al. Regulated Pure Pursuit for Robot Path Tracking. Autonomous Robots 47, 685--694 (2023). doi:10.1007/s10514-023-10097-6.
\bibitem{dwa} D. Fox, W. Burgard and S. Thrun. The Dynamic Window Approach to Collision Avoidance. IEEE Robotics \& Automation Magazine 4(1), 23--33 (1997).
\bibitem{mppi} G. Williams, A. Aldrich and E. A. Theodorou. Model Predictive Path Integral Control: From Theory to Parallel Computation. J. Guidance, Control, and Dynamics 40(2), 344--357 (2017). doi:10.2514/1.G001921.
\bibitem{vlfm} N. Yokoyama et al. VLFM: Vision-Language Frontier Maps for Zero-Shot Semantic Navigation. arXiv:2312.03275 (2023).
\bibitem{navila} A.-C. Cheng et al. NaVILA: Legged Robot Vision-Language-Action Model for Navigation. arXiv:2412.04453 (2024; revised 2025).
\bibitem{lrmcp} Z. Sun et al. Socially Aware Robot Crowd Navigation via Online Uncertainty-Driven Risk Adaptation. arXiv:2506.14305 (2025).
\bibitem{smolvlm} A. Marafioti et al. SmolVLM: Redefining small and efficient multimodal models. arXiv:2504.05299 (2025). Model: HuggingFaceTB/SmolVLM2-500M-Video-Instruct.
\bibitem{lora} E. J. Hu et al. LoRA: Low-Rank Adaptation of Large Language Models. ICLR (2022).
\end{thebibliography}\end{document}
'''
    text=text.replace(r'\\%',r'\%')
    P.mkdir(exist_ok=True);(P/'urban_vlm_navigation.tex').write_text(text)
    (P/'claims.json').write_text(json.dumps(dict(core_episodes=audit['episodes'],formal_episodes=total,adapted_clean=f['clean'],rule_clean=rule['clean'],frozen_clean=base['clean'],paired_rule=pair,conclusion=conclusion),indent=2)+'\n')
    print('PAPER_SOURCE_COMPLETE',P/'urban_vlm_navigation.tex')
if __name__=='__main__':main()
