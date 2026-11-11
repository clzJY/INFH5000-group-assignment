#!/usr/bin/env python3
"""Unchanged five-page proposal with combined AI-use statement, review dialogue and screenshots."""
import argparse,json,re,xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.sax.saxutils import escape
from build_proposal import Doc,ROOT

URI='http://schemas.openxmlformats.org/wordprocessingml/2006/main';NS={'w':URI}
W=lambda n:'{'+URI+'}'+n

def two_decimals(value):
 return str(Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))

def prop(parent,name,**attrs):
 e=parent.find('w:'+name,NS)
 if e is None:e=ET.SubElement(parent,W(name))
 for k,v in attrs.items():e.set(W(k),str(v))
 return e

class CourseDoc(Doc):
 def __init__(self):super().__init__();self.blocks=[]
 def p(self,text='',style=None,size=None,bold=False):
  self.blocks.append(dict(type='paragraph',style=style or 'Normal',text=text))
  super().p(text,style,size,bold)
 def table(self,rows,widths):
  self.blocks.append(dict(type='table',rows=rows));widths=list(widths);widths[-1]+=9746-sum(widths)
  s='<w:tbl><w:tblPr><w:tblW w:w="9746" w:type="dxa"/><w:tblBorders><w:top w:val="single" w:sz="7" w:color="355366"/><w:bottom w:val="single" w:sz="7" w:color="355366"/></w:tblBorders><w:tblCellMar><w:top w:w="55" w:type="dxa"/><w:bottom w:w="55" w:type="dxa"/><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'+''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)+'</w:tblGrid>'
  for i,row in enumerate(rows):
   s+='<w:tr><w:trPr><w:cantSplit/>'+('<w:tblHeader/>' if i==0 else '')+'</w:trPr>'
   for j,(text,width) in enumerate(zip(row,widths)):
    numeric=bool(re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',str(text)))
    border='<w:tcBorders><w:bottom w:val="single" w:sz="4" w:color="7D939D"/></w:tcBorders>' if i==0 else ''
    s+=f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{border}<w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr>'+('<w:keepNext/>' if i==0 else '')+f'<w:keepLines/><w:spacing w:before="0" w:after="10" w:line="235" w:lineRule="auto"/><w:jc w:val="{"center" if numeric else "left"}"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/>'+('<w:b/>' if i==0 else '')+f'</w:rPr><w:t>{escape(str(text))}</w:t></w:r></w:p></w:tc>'
   s+='</w:tr>'
  self.parts.append(s+'</w:tbl>')
 def image(self,path,width=6.65):
  self.blocks.append(dict(type='image',path=str(Path(path).relative_to(ROOT))))
  super().image(path,width)
 def save(self,path):
  assert not path.exists(),'Preserve existing documents; use a new output directory.'
  super().save(path)
  with ZipFile(path) as z:parts={n:z.read(n) for n in z.namelist()}
  ET.register_namespace('w',URI)
  root=ET.fromstring(parts['word/document.xml']);body=root.find('w:body',NS)
  in_appendix=False
  for p in body.findall('w:p',NS):
   pp=prop(p,'pPr');text=''.join(p.itertext()).strip()
   if text.startswith('Appendix.'):in_appendix=True
   if p.find('.//w:drawing',NS) is not None:prop(pp,'keepNext',val=0 if in_appendix else 1);prop(pp,'spacing',before=50,after=30)
   if text.startswith('Table '):prop(pp,'keepNext',val=1)
  children=list(body)
  for i,x in enumerate(children[:-1]):
   if x.tag==W('tbl') and children[i+1].tag==W('p'):prop(prop(children[i+1],'pPr'),'spacing',before=80)
  sect=body.find('w:sectPr',NS);prop(sect,'pgMar',top=1050,bottom=1050,left=1080,right=1080,header=420,footer=420)
  styles=ET.fromstring(parts['word/styles.xml']);defaults=styles.find('w:docDefaults',NS)
  rp=defaults.find('w:rPrDefault/w:rPr',NS);prop(rp,'sz',val=22)
  pp=defaults.find('w:pPrDefault/w:pPr',NS);prop(pp,'spacing',before=0,after=80,line=268,lineRule='auto');prop(pp,'jc',val='both');prop(pp,'widowControl',val=1)
  specs={'Title':(36,0,80,245),'Heading':(26,150,70,245),'Caption':(19,50,75,230),'Subheading':(23,110,45,240),'Reference':(19,0,55,225),'Metadata':(20,0,55,235),'AIQuote':(20,35,65,250),'AIResponse':(21,0,55,250)}
  for sid,(size,before,after,line) in specs.items():
   st=next((s for s in styles.findall('w:style',NS) if s.get(W('styleId'))==sid),None)
   if st is None:st=ET.SubElement(styles,W('style'),{W('type'):'paragraph',W('styleId'):sid});prop(st,'name',val=sid)
   pp=prop(st,'pPr');prop(pp,'spacing',before=before,after=after,line=line,lineRule='auto');prop(pp,'jc',val='left');prop(pp,'keepLines',val=1)
   if sid in ['Title','Heading','Subheading','Metadata']:prop(pp,'keepNext',val=1)
   if sid=='Reference':prop(pp,'ind',left=280,hanging=280)
   rp=prop(st,'rPr');prop(rp,'sz',val=size)
   if sid in ['Title','Heading','Subheading']:prop(rp,'b');prop(rp,'color',val='000000')
  # Black document headings and text; retain data colours inside figures.
  prop(styles.find('w:docDefaults/w:rPrDefault/w:rPr',NS),'rFonts',eastAsia='Noto Serif CJK SC')
  for color in styles.findall('.//w:color',NS):color.set(W('val'),'000000')
  for header_name in ['word/header1.xml','word/footer1.xml']:
   header=ET.fromstring(parts[header_name])
   for color in header.findall('.//w:color',NS):color.set(W('val'),'000000')
   parts[header_name]=ET.tostring(header,encoding='utf-8',xml_declaration=True)
  parts['word/document.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True);parts['word/styles.xml']=ET.tostring(styles,encoding='utf-8',xml_declaration=True)
  # Rewrite only the newly generated file, never a previous report version.
  with ZipFile(path,'w',ZIP_DEFLATED) as z:
   for n,data in parts.items():z.writestr(n,data)
  path.with_suffix('.content.json').write_text(json.dumps(self.blocks,indent=2,ensure_ascii=False)+'\n')


def build(operation,output,include_ai_appendix=False):
 audit=json.loads((operation/'evidence_audit.json').read_text());assert audit['passed'] and audit['episodes']==160
 G=audit['random'];pair={r['control']:r for r in audit['paired']};F=G['forecast'];Z=G['forecast_static'];P=G['pp'];A=pair['rpp'];V=pair['forecast_static'];D=pair['dwa']
 assert (F['strict'],F['contact_free'],F['pedestrian_contacts'])==(Z['strict'],Z['contact_free'],Z['pedestrian_contacts'])==(16,13,3)
 d=CourseDoc();d.p('Predictive and Reactive Robot Navigation in Shared Urban Pedestrian Spaces','Title');d.p('Evidence from a MetaUrban Pilot',size=23)
 d.p('Chenglong Zhang | 50068179','Metadata');d.p('UCMP-MB · Week 3 · Option 1: Mini Research Proposal','Metadata')
 d.p('1. Introduction and Research Question','Heading')
 d.p('1.1 Urban Context and Theoretical Motivation','Subheading')
 d.p('A service robot travelling to an inspection point must share crossings and pavements with people. Its arrival time alone cannot describe whether that journey fits the public space. Street furniture can constrain movement, while pedestrian motion changes when two users compete for the same location.')
 d.p('Urban informatics connects spatial data and movement records with analytical methods to examine shared public space. A network perspective on cities emphasises movement and interaction [1]. At pavement scale, this motivates examining street form together with time-varying encounters. Here, spatial structure constrains possible actions; recorded trajectories reveal interactions; comparisons inform robot movement decisions. Accessibility motivates evaluating task completion alongside the spatial and temporal costs of sharing pavements.')
 d.p('Social-navigation research also distinguishes physical safety, comfort and understandable behaviour [3]. A robot may avoid recorded contact yet remain close to someone or obstruct their passage. Consequently, this study assesses arrival, contact, waiting and proximity separately to describe different aspects of sharing space.')
 d.p('1.2 Research Question and Objective','Subheading')
 d.p('How does short-horizon motion prediction affect contact-free arrival and robot waiting in shared urban pedestrian spaces, and which encounter or layout conditions limit its usefulness?',bold=True)
 d.p('Reactive control responds to current conditions; prediction estimates how encounters may change over the next few seconds. We test that added information with a shared route in one intersection family, without claiming general effects of street design.')
 d.p('1.3 Pilot Work and Proposed Follow-up','Subheading')
 d.p('The completed pilot implemented a route-conditioned forecast and speed-selection module, adapted comparison methods, and evaluated 160 formal runs after 68 development runs. The matched comparisons characterise completion, contact and waiting across pedestrian encounters and identify conditions for further testing. The proposed follow-up is to test a bounded-detour trigger when waiting cannot resolve static blockage. That extension is not yet implemented.')
 d.image(ROOT/'outputs/classical/figures/mission_scene_pair.png')
 d.p('Figure 1. MetaUrban views at departure and after arrival and physical stopping in a development case. Crossings, pavement and street objects locate the inspection task. RGB images document execution; controllers use numerical states.','Caption')
 d.p('2. Urban Simulation Data and Spatial Units','Heading')
 d.p('2.1 Data Source and Urban Scenarios','Subheading')
 d.p('MetaUrban provides three-dimensional urban micromobility settings [2]. We use its public small asset set, an intersection, street furniture and a wheelchair-shaped wheeled model with native wheel physics. Controllers use simulator states and a supplied reference route; evaluation focuses on wheeled navigation.')
 d.p('The main test combines ten newly evaluated scenes with two pedestrian counts, five and fifteen, giving twenty matched conditions for each of six methods. A separate diagnostic suite tests crossing, receding, approaching and stationary pedestrians, with two new conditions per encounter and five methods. These forty single-person runs are not pooled with the 120 main runs. Sixty-eight development runs preceded both tests.')
 d.p('Native crowd paths use Optimal Reciprocal Collision Avoidance (ORCA), an approach based on shared avoidance responsibility [7]. Their realised motion here does not establish responsive human behaviour. Diagnostic pedestrians instead follow prescribed trajectories. Controllers observe their current positions and derived velocities, not the future scripts.')
 d.p('2.2 Variables, Spatial Units and Data Boundaries','Subheading')
 d.p('The data connect urban conditions to measurable decisions as follows. A footprint is the ground-plane area of an actor’s collision box. Crowd size is an agent count, not a density in people per square metre. Pavement and crossing context is visible in the scene, but their widths were not systematically varied or evaluated as causal factors.')
 d.p('Table 1. Urban context, recorded variables and analytical roles.','Caption')
 d.table([['Urban attribute','Recorded variable and unit','Role in the study'],['Route and task location','Reference polyline, robot position and endpoint distance (m)','Identify progress and actual waypoint arrival'],['Street furniture','Static object footprints and predicted gap (m)','Inspect persistent stops near the reference route'],['Pedestrian movement','Position (m), derived velocity (m/s), count and encounter type','Describe where and when trajectories conflict'],['Sharing a location','Contacts, stop-command time (s), proximity exposure (%)','Compare progress with observable interaction costs']],[2300,3850,3596])
 d.p('Coordinates are local metres without a geographic reference. One 0.1-second decision is the observation unit; one episode is the outcome unit. Scene identity and crowd count define a matched comparison. Both crowd conditions share the same scene identity, so twenty conditions do not represent twenty independent urban layouts.')
 d.image(ROOT/'outputs/editorial_v5_20261111/figures/recorded_scene_plan.png')
 d.p('Figure 2. Recorded development crossing encounter. A shows the reference route, executed forecast trajectory, target and static footprints. B shows observed positions and commands, the pedestrian’s first eight seconds and body outlines at 4.1 seconds. The figure uses local simulator coordinates and recorded object geometry.','Caption')
 d.p('3. Methodology and Evaluation Design','Heading')
 d.p('3.1 Pilot Module and Comparison Methods','Subheading')
 d.p('The pilot modification is the measured-velocity forecast module. It selects speed while a common tracker follows the route. We also implemented the controls and local baseline adaptations in Table 2. All receive the same full route, robot state, pedestrian positions and derived velocities, and static footprints, with shared motion limits, braking and static protection.')
 d.p('Pure Pursuit (PP) chooses steering towards a point ahead on the route [4]. Regulated Pure Pursuit (RPP) adds speed regulation around curves and obstacles [5]. The Dynamic Window Approach (DWA) searches locally achievable motion commands [6]. The RPP-inspired and DWA-style versions below are local adaptations, not full reproductions of the published controllers.')
 d.p('Table 2. Roles in our completed pilot. The final column explains what each comparison tests.','Caption')
 d.table([['Method','Study role','Decision and comparison purpose'],['Forecast: measured velocity','Pilot modification','Predict bodies along candidate route motions; extrapolate measured pedestrian velocity and choose speed or stopping.'],['PP + static guard','Baseline','Track the route with basic static protection; test a simple backbone [4].'],['RPP-inspired','Baseline','Regulate speed using curves and nearby objects; compare a regulated tracker [5].'],['DWA-style','Baseline','Search local speed and steering choices; test lateral flexibility [6].'],['Distance yield','Simple control','Slow using current pedestrian gap; test whether prediction is needed.'],['Forecast: zero velocity','Ablation control','Same module with predicted pedestrian velocity set to zero; isolate that input. Actual people still move.']],[2500,1900,5346])
 d.p('Our module compares normal progress, slower motion and stopping over 1.5 seconds, following the reference route in each prediction. Oriented body footprints test whether a robot and a person may share space at similar times. This speed-selection layer is the implemented modification; it does not introduce a new global route.')
 d.p('The zero-velocity ablation changes only pedestrian-velocity input. It tests that input’s value, whereas comparison with RPP also includes other controller choices. Because a prescribed person may approach a stationary robot, stopping is evaluated alongside forward-motion candidates. ORCA generates crowd motion; it is not an additional robot baseline here.')
 d.p('3.2 Outcomes and Fair Comparisons','Subheading')
 d.p('Strict arrival requires both the simulator’s arrival flag and an endpoint distance of at most 2 m. Contact-free arrival additionally excludes simulator-reported contacts with pedestrians, objects, buildings and sidewalk boundaries. Pedestrian-contact counts are reported separately because an episode can reach the goal after contact. Stop-command duration measures robot waiting decisions, not pedestrian delay.')
 d.p('Proximity exposure is the observed time fraction with a planar robot–pedestrian footprint gap below 1 m, sampled every 0.1 seconds. This geometric proxy is not measured comfort. Its denominator ends when the episode ends, so exposure must be interpreted alongside completion and contact outcomes.')
 d.p('Each method starts from the same physical scene and has the same sixty-second budget. Routes and start-to-goal distances must both be at least 5 m; invalid tasks would be retained without replacement. All twenty main conditions passed this check. Parameters were fixed after development and before either test, with failed and contact episodes retained.')
 d.p('Analysis uses descriptive paired counts and compares travel time only on conditions completed by both methods. Shared scene identities are respected when interpreting repeated crowd conditions. No significance or equivalence claim is made. Detailed software versions, scene identifiers, engineering thresholds and supplementary uncertainty calculations are documented separately.')
 d.p('4. Preliminary Results and Interpretation','Heading')
 d.p('4.1 Preliminary Comparison and the Velocity Ablation','Subheading')
 d.p('Table 3 summarises the main test. The measured-velocity forecast and its zero-velocity ablation each recorded sixteen strict arrivals, thirteen contact-free arrivals and three pedestrian-contact episodes. This pilot therefore found no aggregate completion or contact-free benefit from the velocity input itself.')
 d.p('Table 3. Completed main test: twenty matched conditions per method. Our module is the measured-velocity row; comparison roles are in Table 2. Counts are episodes; time and exposure are episode means.','Caption')
 names=[('pp','PP + static guard'),('rpp','RPP-inspired'),('distance','Distance yield'),('forecast_static','Forecast: zero velocity'),('forecast','Forecast: measured velocity'),('dwa','DWA-style')]
 table=[['Method','Strict','Contact-free','Ped. contact','Wait (s)','Near (%)']]
 for method,name in names:
  x=G[method];table.append([name,x['strict'],x['contact_free'],x['pedestrian_contacts'],two_decimals(x['mean_wait_s']),two_decimals(100*x['mean_near_fraction'])])
 d.table(table,[3050,1030,1450,1380,1400,1436])
 d.p(f"Against RPP-inspired control, forecasting was {abs(A['mean_joint_delay_s']):.2f} seconds faster across the same {A['joint_n']} successful conditions. However, it added {V['mean_joint_delay_s']:.2f} seconds relative to the zero-velocity ablation on those same conditions. The difference from RPP is specific to that comparison; it establishes neither a general time advantage nor a benefit from pedestrian velocity input.")
 d.p('PP with the common static guard matched the same arrival counts and had lower mean waiting and proximity exposure. Thus, increased predictive complexity was not justified as a default by this sample. None of these comparisons measures people’s perceived comfort or rare-event safety.')
 d.p('4.2 Failure Patterns and Lateral Flexibility','Subheading')
 d.p('All five route-tracking variants timed out in the same four scene–crowd conditions. Their moving predictions failed the static-footprint buffer while stopping passed. DWA-style completed all four, three without contact, but failed six other conditions completed by forecasting. This indicates a trade-off in lateral control, not universal superiority.')
 d.p(f"In paired strict-arrival terms, forecast gained {D['strict_rescued']} conditions and lost {D['strict_lost']} relative to DWA-style, a net gain of {D['strict_net']}. The contact-free total changed separately from twelve to thirteen, a gain of {D['contact_free_net']}. The two comparisons show why reaching the goal and doing so without contact must be evaluated separately.")
 d.p('Table 4. Separate scripted diagnostics: contact-free arrivals out of two conditions per encounter. One pedestrian is present in each episode.','Caption')
 methods=['rpp','distance','forecast_static','forecast','dwa'];t=[['Encounter','RPP-inspired','Distance','Zero velocity','Measured velocity','DWA-style']]
 for kind in ['crossing','receding','approaching','stationary']:
  t.append([kind,*[sum(x['contact_free_goal'] for x in audit['controlled'] if x['density']==kind and x['method']==method) for method in methods]])
 d.table(t,[2100,1500,1300,1600,1850,1396])
 d.p('In crossing diagnostics, forecasting averaged no waiting against one second for regulated tracking, but proximity exposure rose from zero to 2.42%. All methods completed both receding cases without contact. The four speed-only methods contacted both approaching pedestrians; DWA-style achieved one contact-free arrival. No method finished either stationary-person task. Waiting alone therefore did not resolve every encounter.')
 d.p('5. Discussion and Proposed Next Study','Heading')
 d.p('5.1 What the Preliminary Results Support','Subheading')
 d.p('The pilot supports a focused follow-up on spatial alternatives. Velocity input left aggregate strict and contact-free arrival unchanged, while persistent stops indicate limits of speed adjustment along a fixed route. Timing differences depend on the comparison method. Static-buffer rejections identify controller-level constraints; assessing physical passability also requires validating geometry and feasible motion.')
 d.p('The urban implication is a conditional design question: when should a public-service robot keep waiting, and when should it consider another nearby path? A faster robot journey is insufficient justification if the alternative transfers obstruction or risk to pedestrians. Those human consequences require additional evaluation.')
 d.p('5.2 Proposed Extension and Follow-up Experiment','Subheading')
 d.p('Our proposed bounded-detour trigger has not been implemented. It would extend the existing module after a persistent stop caused by static checks, considering left and right waypoint offsets inside a limited local area. Candidates must remain in validated walkable space and preserve footprint buffers; otherwise the robot would keep waiting.')
 d.p('Our follow-up would compare three groups: RPP-inspired tracking (baseline), our existing forecast module (reference), and our module plus the new trigger (proposed variant). Only the third adds the detour. Ten new scene identities, two validated layout families and two crowd sizes give 120 new runs across those groups. The hypothesis is more strict arrivals without fewer contact-free arrivals.')
 d.p('We would first develop the trigger on separate scenes, fix its settings and protocol, then run the matched test and review failures by layout and crowd count. Existing local simulation makes this feasible without training. These 120 runs and any detour benefit are future work; they are not part of the completed 160-run evidence.')
 d.p('5.3 Uncertainty, Ethics and Transferability','Subheading')
 d.p('The pilot covers one intersection family, a small asset set and ideal simulator states. Simplified wheel dynamics, sampled planar footprints and prescribed pedestrian motion limit transfer. Scene variation does not represent neighbourhood demographics or diverse mobility needs. No causal estimate of pavement width or street design is available.')
 d.p('No real personal observations were collected. Future street-image recording would require appropriate consent or observation procedures, limited retention and accessibility review with affected users. Comfort, predictability and pedestrian inconvenience should be assessed directly [3]. The practical contribution is a reproducible framework for examining urban interaction trade-offs and identifying requirements for further evaluation.')
 d.p('References','Heading')
 refs=[
 '[1] Batty, M. (2013). The New Science of Cities. MIT Press.',
 '[2] Wu, W., et al. (2025). MetaUrban: An Embodied AI Simulation Platform for Urban Micromobility. International Conference on Learning Representations (ICLR).',
 '[3] Francis, A., et al. (2025). Principles and Guidelines for Evaluating Social Robot Navigation Algorithms. ACM Transactions on Human-Robot Interaction 14(2), Article 34, 1–65. https://doi.org/10.1145/3700599',
 '[4] Coulter, R. C. (1992). Implementation of the Pure Pursuit Path Tracking Algorithm. CMU-RI-TR-92-01, Carnegie Mellon University.',
 '[5] Macenski, S., Singh, S., Martín, F. & Ginés, J. (2023). Regulated Pure Pursuit for Robot Path Tracking. Autonomous Robots 47, 685–694. https://doi.org/10.1007/s10514-023-10097-6',
 '[6] Fox, D., Burgard, W. & Thrun, S. (1997). The Dynamic Window Approach to Collision Avoidance. IEEE Robotics & Automation Magazine 4(1), 23–33.',
 '[7] van den Berg, J., Guy, S. J., Lin, M. & Manocha, D. (2011). Reciprocal n-body collision avoidance. Robotics Research, 3–19. https://doi.org/10.1007/978-3-642-19457-3_1'
 ]
 for ref in refs:d.p(ref,'Reference')
 if include_ai_appendix:
  from ai_use_appendix_v12 import append_ai_record
  append_ai_record(d,operation)
 output.parent.mkdir(parents=True,exist_ok=True);d.save(output)
 text='\n\n'.join(b['text'] for b in d.blocks if b['type']=='paragraph');output.with_suffix('.txt').write_text(text+'\n')
 print(json.dumps(dict(output=str(output),paragraph_words=len(text.split()),subsections=sum(b.get('style')=='Subheading' for b in d.blocks),references=len(refs)),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--operation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--include-ai-appendix',action='store_true');a=p.parse_args();build(a.operation,a.output,a.include_ai_appendix)
