"""Build a course-template report from frozen results; never invent team identities."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'research/course_delivery';P=D/'report';P.mkdir(exist_ok=True)
data=json.loads((D/'source/audited_content.json').read_text());group=json.loads((D/'source/group_metadata.json').read_text())
names={'rpp':'RPP-inspired','forecast':'Speed forecast','dwa':'DWA-style','mppi':'MPPI-style','lattice':'Geometric selector','vlm':'Frozen VLM','lora':'Adapted VLM','lora_s1':'Adapted, seed 1','lora_s2':'Adapted, seed 2','lora_no_rgb':'No RGB','lora_no_image':'No image','lora_no_language':'Minimal instruction'}
def esc(v):
 if v is None:return 'To be confirmed'
 s=str(v)
 for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:s=s.replace(a,b)
 return s
rows={r['method']:r for r in data['core'] if r['map']=='all'}
core_table='\n'.join(f"{names[m]} & {rows[m]['strict']}/120 & {rows[m]['clean']}/120 & {rows[m]['waiting_s']:.1f} & {100*rows[m]['outside_fraction']:.2f}"+r' \\' for m in names if m in rows)
seedrows=[rows['lora']]+[r for r in data['variation'] if r['map']=='all']
seed_table='\n'.join(f"{i} & {r['strict']}/120 & {r['clean']}/120 & {r['waiting_s']:.1f}"+r' \\' for i,r in enumerate(seedrows))
abrows=[r for r in data['ablations'] if r['map']=='all']
ab_table='\n'.join(f"{names[r['method']]} & {r['strict']}/24 & {r['clean']}/24 & {100*r['outside_fraction']:.2f}"+r' \\' for r in abrows)
team='\n'.join(f"{esc(r['name'])} & {esc(r['thrust'])} & {esc(r['contribution_percent'])} & {esc(r['actual_work'])}"+r' \\' for r in group['members'])
body=r'''\documentclass[a4paper,12pt]{article}
% Adapted from Ma Wanqin, HKUST Lab Report Template (CC BY 4.0).
% https://www.overleaf.com/latex/templates/hkust-lab-report-template/wypwcqnrmhqj
\usepackage[T1]{fontenc}\usepackage{lmodern}
\usepackage{graphicx,amsmath,amssymb,geometry,fancyhdr,setspace,titlesec}
\usepackage{booktabs,tabularx,array,microtype,caption,placeins,enumitem}
\usepackage[hidelinks]{hyperref}
\geometry{margin=1in}\setstretch{1.5}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small INFH5000: Urban Robot Navigation}\fancyhead[R]{\thepage}
\setlength{\headheight}{15pt}\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}
\setlength{\textfloatsep}{12pt plus 2pt minus 2pt}
\titleformat{\section}{\normalfont\Large\bfseries}{\thesection}{.8em}{}
\titleformat{\subsection}{\normalfont\large\bfseries}{\thesubsection}{.8em}{}
\captionsetup{font={small,stretch=1.08},labelfont=bf}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\hypersetup{pdftitle={Constrained Local Planning and Vision-Language Guidance for Urban Robot Navigation},pdfauthor={INFH5000 group information pending}}
\begin{document}
\begin{titlepage}
\centering
\IfFileExists{../assets/hkust_logo.png}{\includegraphics[width=.48\textwidth]{../assets/hkust_logo.png}\\[8mm]}{{\Large Hong Kong University of Science and Technology\\[5mm]}}
{\LARGE\bfseries Constrained Local Planning and\\[2mm] Vision--Language Guidance for\\[2mm] Urban Robot Navigation\par}
\vspace{7mm}
{\large INFH5000 Group Project Report\\21 November 2026\par}
\vspace{6mm}
\textbf{Group ID: '''+esc(group['group_id'])+r'''}\par
\vspace{4mm}
\begin{spacing}{1.12}\small
\begin{tabularx}{\textwidth}{YYYY}\toprule
Member & Thrust & Work share (\%) & Actual work\\\midrule
'''+team+r'''
\bottomrule\end{tabularx}
\end{spacing}
\vspace{4mm}
\begin{minipage}{.96\textwidth}\small
Group identities, actual tasks and contribution percentages require the team's confirmation. Shares must total 100\%; four or five members and the course's thrust-composition rule must be checked before submission. No member or contribution is inferred from the experiment logs.
\end{minipage}
\vfill
{\small AI \quad $\times$ \quad Data Science \quad $\times$ \quad Computational Media\\A completed simulation study with explicit negative findings}
\end{titlepage}
\setcounter{page}{1}
\begin{spacing}{1.05}\tableofcontents\end{spacing}
\vspace{3mm}
\section*{Executive Summary}
\addcontentsline{toc}{section}{Executive Summary}
\begin{spacing}{1.2}
Service robots must reach destinations while sharing pedestrian space. We evaluate constrained local planning and vision--language guidance in native MetaUrban. On 120 matched natural conditions per method, geometric selection achieves 79 contact-free arrivals versus 62 for route-constrained speed forecasting. A trained visual selector achieves 68 and remains unstable across training seeds. The full campaign contains 1,384 formal episodes with separately reported diagnostics. The results support geometric selection in this simulator but do not establish an additional benefit from the single-frame model or real-world deployment safety.
\end{spacing}
\newpage

\section{Objective}
A robot on a sidewalk may need to wait for a pedestrian, turn within limited clearance or pass a local obstruction. A controller that only slows along its reference cannot always use available lateral space. Conversely, adding a pretrained visual model may increase complexity without improving completion. Our research question is: \emph{under different simulated street structures, clear widths and pedestrian counts, does constrained local trajectory selection improve navigation, and does vision--language guidance add value beyond geometric selection?}

The project connects three course areas through concrete work. Artificial intelligence contributes multimodal action-token adaptation. Data science contributes matched experiments, spatial stratification, input ablations and uncertainty analysis. Computational media and arts contribute procedural three-dimensional urban scenes and recorded visual demonstrations. The observe--decide--act loop also relates conceptually to the Internet of Things (IoT), but no physical sensor network or communication system was implemented.

The practical objective is to understand completion/contact trade-offs in shared pedestrian space. We do not measure people's comfort or accessibility, which require additional human-centred evidence \cite{francis}. The project extends an earlier single-scene pilot; Table~\ref{tab:new} distinguishes the extensions from inherited work.

\begin{table}[ht]\centering\small\begin{spacing}{1.08}
\caption{What is new in this project relative to the retained pilot. Existing algorithms and simulator assets remain attributed to their sources.}\label{tab:new}
\begin{tabularx}{\linewidth}{p{.22\linewidth}YY}\toprule
Component & Inherited foundation & Completed extension\\\midrule
Urban scenes & Single-scene street pilot & Intersection, straight and curved families; width/crowd factors\\
Navigation & Route following and speed prediction & Five lateral candidates, footprint constraints and fallback\\
Learning & No multimodal adaptation & Vision/text LoRA, three training seeds and a curve-excluded model\\
Evidence & Original pilot comparisons & 1,384 formal episodes, paired audits, ablations and stress tests\\\bottomrule
\end{tabularx}\end{spacing}\end{table}

\section{Problem Description and Background}
MetaUrban provides procedural urban micromobility scenes and native pedestrian simulation \cite{metaurban}. Our robot is a wheeled, wheelchair-shaped model navigating to an inspection point; reaching it is the evaluated task. Route-following, local collision prediction and vision--language guidance address different parts of that task.

Regulated Pure Pursuit (RPP) regulates tracking speed \cite{rpp}. The Dynamic Window Approach (DWA) searches local motion commands \cite{dwa}, while Model Predictive Path Integral (MPPI) control weights sampled sequences \cite{mppi}. These established approaches motivate the classical comparisons. Our implementations are project adaptations, not complete official reproductions.

Vision--Language Frontier Maps (VLFM) uses semantic guidance for exploration \cite{vlfm}; NaVILA separates navigation guidance from learned locomotion \cite{navila}. Risk-aware candidate control is also established \cite{lrmcp}. We therefore position the project as a comparison of hierarchical design choices. We use SmolVLM2 \cite{smolvlm} with Low-Rank Adaptation (LoRA) \cite{lora}, not a new foundation architecture or full end-to-end vision--language--action (VLA) system.

\section{Methodology}
\subsection{Scenes, Data and Spatial Units}
The natural test contains three map families, two nominal clear-width bands (2.6/4.6 m), two pedestrian counts (5/15), and ten fresh scene seeds:
\[
3\ \mathrm{families}\times2\ \mathrm{widths}\times2\ \mathrm{counts}\times10\ \mathrm{seeds}=120\ \mathrm{conditions}.
\]
These are local simulator coordinates in metres. Agent counts are not people per square metre, and these scenes are not a representative geographic sample. Scene family--seed is the grouped unit for uncertainty analysis; decisions within an episode are correlated. Furniture density is fixed at 0.15, although occupied footprints vary.

\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{../assets/scene_atlas.png}
\caption{Native three-dimensional views and corresponding local spatial layouts. Illustration: wide band, five pedestrians, seed 1600. Maps show the shared reference and the geometric selector's actual trajectory; they are not real-city maps.}\label{fig:scenes}\end{figure}

All execution layers use simulator robot state, pedestrian positions/velocities and static footprints. The model selector instead receives one current camera image, a privileged local-map rendering and a fixed instruction. It has no explicit velocity labels or visual history. This observation difference limits an architecture-only interpretation of model/rule comparisons.

\subsection{Reference and Local Decisions}
A shared A* reference is planned over native walkable polygons after subtracting furniture footprints. The declared region includes a 0.05 m expansion; route construction uses a 0.4 m grid and 0.78 m erosion. All main methods use this reference, so it cannot alone explain differences between them.

The new local library contains lateral offsets of $-1.5,-0.75,0,0.75,1.5$ m and stopping. A bounded bicycle model predicts three seconds of motion, with constant-velocity pedestrian forecasts and sampled rectangular clearances. The geometric selector ranks feasible choices. A model proposal passes the same checks and falls back to the geometric choice if infeasible. If none is feasible, the robot brakes. An explicit recovery rule allows a partly outside footprint to return inside without increasing initial outside area by more than 0.005 m$^2$. Actual boundary exposure is still reported.

\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{../assets/pipeline.png}
\caption{Tested action hierarchy. The model proposes a token at 1 Hz; geometric revalidation and native steering/throttle/brake decisions run at 10 Hz. Sampled checks do not guarantee continuous collision avoidance.}\label{fig:flow}\end{figure}

The simulator's Bullet physics updates position and velocity; the controller never teleports the robot. MPPI-style control separately samples 96 bounded control sequences, validates the weighted result and otherwise uses its best feasible sample.

\subsection{Actual Multimodal Training}
SmolVLM2-500M receives a 640$\times$320 composite of native colour (RGB) images and a privileged local map, plus a fixed English task instruction. The map shows current bodies, geometry, reference and candidate labels, without teacher scores or explicit velocity arrows. Next-token probabilities are restricted to A--F, corresponding to five trajectories and stopping.

Supervision comes from geometric predictive ranking, not native execution of every counterfactual action or human feedback. The final data contain 598 training and 304 validation decisions with disjoint whole-scene seeds. These are decision samples, not hundreds of independent tasks. Query/value LoRA adapters in vision and language attention train 1,114,112 parameters; the backbone is frozen. Three seeds train for ten epochs. Checkpoints are selected using the mean of validation accuracy and six-class recall, without formal test outcomes. A fourth model excludes curves from training and validation.

The primary adapter reaches 77.3\% validation label accuracy and 47.5\% class-balanced recall; a constant-majority label reaches 54.6\% accuracy. Label agreement is distinct from closed-loop navigation success.

\subsection{Comparisons and Evaluation Protocol}
Seven methods run on the same 120 natural conditions. RPP-inspired tracking tests regulated reference following; speed forecasting tests route-constrained timing; DWA-style tests local command search; MPPI-style tests sampled sequences; the geometric selector tests lateral candidates/constraints; frozen and adapted VLMs test pretrained action use and task adaptation. Proximal Policy Optimization (PPO) is not the principal comparison because an available pretrained policy was not trained for these matched conditions.

The first three controllers retain their original static-body guard and do not receive the new walkable-candidate filter. Their contrast with the new planner evaluates a package of changes. The rule/model pair shares candidates and fallback, but differs in the observation information supplied to its selector. The prior pilot's zero-velocity ablation remains separate.

Every episode has a 120 s simulated budget and maximum target speed of 2 m/s. \textbf{Strict arrival} requires the native flag and endpoint distance at most 2 m. \textbf{Contact-free arrival} additionally excludes any recorded human, object, building or sidewalk contact. Failures and timeouts remain in the denominator. Waiting commands, physical standstill and sampled full-footprint exposure outside the declared region are separate metrics.

Travel-time differences use only jointly successful conditions and state that denominator. Paired 95\% bootstrap intervals resample scene family--seed clusters 10,000 times, retaining width/crowd variants together. A seed-only sensitivity analysis additionally groups families sharing a seed. These are exploratory simulation estimates, not population safety rates.

\FloatBarrier
\section{Measurement and Results}
\subsection{Natural Scenes: Local Geometry Helps}
Table~\ref{tab:main} reports the main comparison. Geometric selection yields 79/120 contact-free arrivals versus 62/120 for speed forecasting: a difference of $+14.17$ percentage points, with a grouped 95\% interval of $[6.67,21.67]$. Pedestrian-contact episodes decrease from 49 to 31. On 93 jointly successful conditions, it changes simulated travel time by $+0.45$ s (geometric minus forecasting). The gain concerns contact-free completion, not faster travel, and cannot yet be assigned to one submodule.

\begin{table}[ht]\centering\small\begin{spacing}{1.08}
\caption{Natural-scene outcomes, 120 matched conditions per method. Outside is mean sampled full-footprint exposure outside the declared region.}\label{tab:main}
\begin{tabular}{lrrrr}\toprule
Method & Strict & Contact-free & Wait (s) & Outside (\%)\\\midrule
'''+core_table+r'''
\bottomrule\end{tabular}\end{spacing}\end{table}

\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{../assets/main_results.png}
\caption{Overall outcomes and family-level variation. Each family contains 40 natural conditions per method. An aggregate ranking does not imply superiority in every layout or individual demonstration.}\label{fig:results}\end{figure}

Geometric contact-free completions are 32/40 at intersections, 12/40 on straight streets and 35/40 on curves. The straight family is therefore hardest in this generated set. Width, furniture exposure and encounter patterns interact; these counts do not show that curves are intrinsically easier or identify causal effects of urban design.

\subsection{Task Adaptation Does Not Beat the Geometric Selector}
The adapted primary model records 68/120 contact-free arrivals, compared with 79/120 for geometric selection and 0/120 for the frozen model. Its model-minus-geometric difference is $-9.17$ percentage points, with primary 95\% interval $[-16.67,-2.50]$. It is $12.23$ s slower on 80 jointly successful conditions. Against speed forecasting it has six additional contact-free arrivals, but the paired interval for that difference includes zero; the execution structures also differ.

The native flag alone would count 103 geometric and 97 adapted arrivals, versus 99 and 83 under the strict criterion. Every recorded entry within 2 m also satisfied the native flag. The distance check removes broad-flag positives in these trajectories. This is a recorded-trajectory diagnostic, not a rerun under alternative termination rules.

\subsection{Training Variation, Inputs and Generalisation}
The three adapter seeds produce 68, 18 and 58 contact-free arrivals out of 120 (Table~\ref{tab:seeds}). All fall below geometry. The primary seed was fixed in advance; the results do not support stable learning from this small scene-level dataset.

\begin{table}[ht]\centering\small\begin{spacing}{1.08}
\caption{Adapter variation on identical natural test conditions.}\label{tab:seeds}
\begin{tabular}{lrrr}\toprule
Training seed & Strict & Contact-free & Wait (s)\\\midrule
'''+seed_table+r'''
\bottomrule\end{tabular}\end{spacing}\end{table}

\begin{table}[ht]\centering\small\begin{spacing}{1.08}
\caption{Inference-time input removals on 24 additional matched conditions. These are not separately retrained models.}\label{tab:ablation}
\begin{tabular}{lrrr}\toprule
Input & Strict & Contact-free & Outside (\%)\\\midrule
'''+ab_table+r'''
\bottomrule\end{tabular}\end{spacing}\end{table}

Without an image, all 1,795 model proposals choose the centre candidate; the geometric execution layer remains active. Its one extra contact-free arrival comes with greater outside exposure (8.46\% versus 4.68\%). This does not establish that vision is unnecessary. Minimal instruction tests wording sensitivity rather than general language understanding. One lateral class has zero validation recall on ten examples, exposing uneven learning.

The curve-excluded adapter achieves 3/40 contact-free curve arrivals versus 32/40 for the fully trained adapter. Exclusion also reduces training to 432 decisions, so layout diversity and data volume are confounded. In a separate post-planning blockage suite, geometry, adapted VLM and MPPI-style achieve 11/24, 4/24 and 7/24 contact-free arrivals. The same existing object is relocated after reference planning in all matched methods; pedestrian paths are not regenerated. These tests remain separate from the natural headline result.

\FloatBarrier
\section{Analysis and Discussion}
\subsection{Evidence, Cost and Feasibility}
The completed campaign comprises 840 main episodes, 240 additional-seed episodes, 96 input-removal episodes, 40 curve-holdout episodes and 168 blockage episodes: 1,384 total. Independent checks cover 1,306,599 decision steps and 69,172 model queries, matching initial conditions, source/checkpoint routing and all 24 blockage placements. Five pre-action setup faults and eighteen administratively interrupted incomplete attempts are archived separately and resumed at their fixed conditions. Completed navigation failures are retained.

Native videos illustrate nine additional fixed-seed episodes, including failures; they are excluded from formal statistics. Their purpose is to make behaviour visible, not to replace matched evaluation. Playback is twice simulated speed, and finished windows hold their final view.

Direct batch-one adapted inference has median 39.2 ms and 95th percentile 46.6 ms over 50 shared-machine measurements. Campaign latency includes queueing and changing host load; mean episode-level controller p95 is 134.7 ms for adaptation and 3.5 ms for geometric selection. Simulation pauses during requests, so simulated travel time does not demonstrate end-to-end deployment responsiveness.

\subsection{What the Results Mean}
The supported improvement is the local planning package: it can exploit lateral space rather than only regulate speed on a fixed route. The learned selector is an exploratory extension whose added benefit is not established. A single image lacks explicit pedestrian motion used by the teacher, labels are correlated and imbalanced, and imitation does not inherently improve on the teacher. These are plausible constraints, not separately proven causal explanations.

The study connects AI decisions to spatial geometry through measurable trajectories and uncertainty analysis. It offers a reproducible computational-media testbed for examining shared-space navigation. It does not demonstrate new IoT hardware, a calibrated digital twin, or improved pedestrian experience.

\subsection{Uncertainty, Ethics and Transferability}
Privileged simulator states bypass real perception errors. Constant-velocity forecasts, bicycle predictions and sampled rectangle checks approximate native dynamics. Boundary recovery permits transient outside exposure; contact-free completion does not imply complete compliance. Three related map families, one robot morphology and a tiny asset collection cannot establish transfer to real cities.

No real-person images or participant data were collected in this study. Real deployment would require consent-aware sensing, privacy protection, accessible-space assessment and human-centred evaluation. Temporal observations, better-matched supervision and broader scene training are future work, not completed improvements.

\section{Conclusions}
The project completes an interdisciplinary three-scene simulation study with constrained local trajectories, actual multimodal adapter training and audited comparisons. Geometric selection improves contact-free completion from 62/120 to 79/120 relative to route-constrained speed prediction. Adapted VLM guidance achieves 68/120 and remains unstable across training seeds. These findings support the local planning design within the tested simulator and bound the present learning claim.

\paragraph{AI assistance and material availability.}
Codex assisted with implementation, orchestration, analysis and document preparation under the project owner's research directions. All reported numbers derive from recorded execution. The presentation uses native simulator media; its optional rehearsal narration is explicitly synthetic. Code, input data, logs and model identities are public; VLM backbone and adapter weights stay local. Team identities and actual work shares must be confirmed before submission.

\FloatBarrier
'''
old=(ROOT/'research/paper/urban_vlm_navigation.tex').read_text();refs=old[old.index(r'\begin{thebibliography}'):old.index(r'\end{thebibliography}')+len(r'\end{thebibliography}')];refs=refs.replace(r'\footnotesize\setlength{\itemsep}{1pt}',r'\small\setstretch{1.1}\setlength{\itemsep}{3pt}')
body+=r'\addcontentsline{toc}{section}{References}'+'\n'+refs+r'''
\paragraph{Technical supplement.}
\begin{spacing}{1.1}\small
Exact environments, hyperparameters, template attribution and reproduction commands are provided in the accompanying technical supplement and repository. The report adapts Ma Wanqin's HKUST Lab Report Template (CC BY 4.0); source URL and unchanged template settings are documented with the submission materials.
\end{spacing}
\end{document}
'''
(P/'INFH5000_Group_Report.tex').write_text(body)
print('COURSE_REPORT_SOURCE_READY',len(body.split()))
