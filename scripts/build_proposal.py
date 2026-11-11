#!/usr/bin/env python3
"""Build an editable, four-page OOXML proposal without downloading packages."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'report'
OUT.mkdir(exist_ok=True)
NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

class Doc:
    def __init__(self):
        self.parts = []
        self.media = {}
    def p(self, text='', style=None, size=None, bold=False):
        props = f'<w:pStyle w:val="{style}"/>' if style else ''
        rp = ('<w:b/>' if bold else '') + (f'<w:sz w:val="{size}"/>' if size else '')
        self.parts.append(f'<w:p><w:pPr>{props}</w:pPr><w:r><w:rPr>{rp}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>')
    def page(self):
        self.parts.append('<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:rPr><w:sz w:val="2"/></w:rPr></w:pPr><w:r><w:br w:type="page"/></w:r></w:p>')
    def table(self, rows, widths):
        s='<w:tbl><w:tblPr><w:tblW w:w="9906" w:type="dxa"/><w:tblBorders>'
        s+=''.join(f'<w:{e} w:val="single" w:sz="4" w:color="CED8DF"/>' for e in ['top','left','bottom','right','insideH','insideV'])
        s+='</w:tblBorders><w:tblCellMar><w:top w:w="65" w:type="dxa"/><w:bottom w:w="65" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'
        s+=''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)+'</w:tblGrid>'
        for i,row in enumerate(rows):
            s+='<w:tr><w:trPr><w:cantSplit/></w:trPr>'
            for text,w in zip(row,widths):
                s+=f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>' + ('<w:shd w:fill="E6EFF1"/>' if i==0 else '') + '</w:tcPr><w:p><w:pPr><w:spacing w:after="15" w:line="220" w:lineRule="auto"/></w:pPr><w:r><w:rPr><w:sz w:val="20"/>' + ('<w:b/>' if i==0 else '') + f'</w:rPr><w:t>{escape(str(text))}</w:t></w:r></w:p></w:tc>'
            s+='</w:tr>'
        self.parts.append(s+'</w:tbl>')
        self.p('',size=4)
    def image(self,path,width=6.75):
        path=Path(path); key=f'image{len(self.media)+1}.png';rid=f'rIdImage{len(self.media)+1}'
        self.media[key]=(rid,path.read_bytes())
        with Image.open(path) as im:height=width*im.height/im.width
        cx,cy=int(width*914400),int(height*914400)
        n=len(self.media)
        self.parts.append(f'''<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="15"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="{key}"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="{n}" name="{key}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>''')
    def save(self,path):
        namespaces=f'xmlns:w="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
        sect='<w:sectPr><w:headerReference w:type="default" r:id="rIdHeader"/><w:footerReference w:type="default" r:id="rIdFooter"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="1000" w:bottom="1000" w:left="1000" w:header="420" w:footer="420"/></w:sectPr>'
        document=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {namespaces}><w:body>'+''.join(self.parts)+sect+'</w:body></w:document>'
        styles=f'''<w:styles xmlns:w="{NS}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="90" w:line="255" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:keepNext/><w:spacing w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="34"/><w:color w:val="163F50"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading"><w:name w:val="Heading 1"/><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="65"/></w:pPr><w:rPr><w:b/><w:sz w:val="25"/><w:color w:val="163F50"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/><w:pPr><w:spacing w:after="75" w:line="220" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="19"/><w:color w:val="354753"/></w:rPr></w:style></w:styles>'''
        rels=[('rIdStyles','styles','styles.xml'),('rIdHeader','header','header1.xml'),('rIdFooter','footer','footer1.xml')]
        rels += [(rid,'image','media/'+key) for key,(rid,data) in self.media.items()]
        relationships='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{kind}" Target="{target}"/>' for rid,kind,target in rels)+'</Relationships>'
        types='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
        for part,kind in [('document','document.main'),('styles','styles'),('header1','header'),('footer1','footer')]:types+=f'<Override PartName="/word/{part}.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{kind}+xml"/>'
        types+='</Types>'
        header=f'<w:hdr xmlns:w="{NS}"><w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:sz w:val="17"/><w:color w:val="6B7A83"/></w:rPr><w:t>UCMP-MB  |  Week 3  |  Mini Research Proposal</w:t></w:r></w:p></w:hdr>'
        footer=f'<w:ftr xmlns:w="{NS}"><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'
        with ZipFile(path,'w',ZIP_DEFLATED) as z:
            for name,data in {'[Content_Types].xml':types,'_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>','word/document.xml':document,'word/styles.xml':styles,'word/_rels/document.xml.rels':relationships,'word/header1.xml':header,'word/footer1.xml':footer}.items():z.writestr(name,data)
            for key,(rid,data) in self.media.items():z.writestr('word/media/'+key,data)

def proposal():
    d=Doc()
    d.p('Clearance-aware navigation for urban service robots', 'Title')
    d.p('A mini research proposal with a reproducible simulation pilot',size=24)
    d.p('Option 1 · Individual assignment · 2 November 2026', 'Caption')
    d.p('1. Research question and urban relevance','Heading')
    d.p('How does adding a fixed or short-horizon predictive clearance buffer to a robot navigation policy change goal completion, pedestrian proximity and travel time in simulated pedestrian crossings? The proposed application is an urban service robot travelling to an inspection waypoint across a pedestrian area. The present task ends at waypoint arrival; inspection imaging, manipulation and humanoid locomotion remain future capabilities.')
    d.p('Public-space deployment creates a problem of shared access: an efficient robot trajectory can still bring a machine unacceptably close to a pedestrian. Human-aware navigation therefore evaluates the relationship between task progress and encounters, rather than travel time alone [2,5]. In urban informatics terms, local trajectories are spatial interaction data: their temporal resolution, sensing assumptions and aggregation determine what an apparent improvement actually means. A collision count cannot establish comfort, and a short completion time is difficult to interpret when other episodes end early in collision.')
    d.p('The theoretical lens is human-aware navigation in shared space [2]. Personal distance is socially and contextually dependent, so a universal comfort radius is not assumed. Instead, this proposal treats geometric clearance as an explicit, limited proxy and tests its operational consequences. A robot crossing a plaza also differs from one traversing a constrained pavement; the spatial support of the simulation must be stated before drawing urban conclusions.')
    d.p('2. Research gap and contribution','Heading')
    d.p('ORCA selects velocities under reciprocal collision-avoidance assumptions [3], while CrowdNav provides reproducible crowd-navigation scenarios [4]. Richer urban simulation is possible with MetaUrban [1]. This project uses the official CrowdNav simulator because its small public assets support a complete local experiment without the pending password for the originally planned MetaUrban static assets. The substitute represents crossing interactions in an open plane; it does not reproduce a mapped street, buildings or kerbs.')
    d.p('The contribution is a small, inspectable comparison: retain the original policy, add a constant buffer inside its velocity optimization, and compare a buffer driven by predicted encounters. No network is trained and no novel navigation algorithm is claimed. A development-stage attempt to cap speed after optimization failed and is retained in the supplementary record. That failure motivates changing the optimization geometry instead of modifying a solved velocity afterwards.')
    d.p('The pilot suggests a useful next question: when does predictive buffering justify its added complexity relative to a strong fixed-buffer control? The proposed follow-up tests that question across crowd density and pedestrian responsiveness, with collision avoidance and completion jointly determining whether a method is useful.')
    d.page()
    d.p('3. Data, spatial units and analytical design','Heading')
    d.p('Data are generated by the public CrowdNav CrowdSim implementation [4], pinned to commit 20d6780, with Python-RVO2 pinned to c2c46ba. Each observation contains exact simulator positions, velocities and radii. The spatial unit is one robot–pedestrian encounter within a time step; outcomes are aggregated first by episode, then by matched scenario instance. These are synthetic coordinates in metres, without a geographic reference system, census population or sampled urban neighbourhood.')
    d.table([['Component','Implemented pilot specification'],['Spatial patterns','Official circle crossing (4 m radius) and square crossing (10 m initialization square); open plane, no walls'],['Actors and motion','One robot and five pedestrians; physical radius 0.30 m; nominal speed limit 1 m/s; holonomic motion'],['Task and timing','Robot (0, −4) → (0, 4) m; goal tolerance 0.30 m; 0.25 s step; native termination, configured 25 s limit'],['Information and response','Exact positions and velocities. Pedestrians use ORCA but do not observe or respond to the robot (official invisible-robot setting).'],['Matched evaluation','5 development cases per pattern; disjoint 10 test cases per pattern; 3 methods × 20 test instances = 60 rollouts']],[2200,7706])
    d.p('Methods. Original ORCA is the baseline. The fixed method adds b = 0.15 m to each agent’s optimization radius, while physical collision radii remain unchanged. The native 0.01 m per-agent allowance is retained. Thus 0.15 m is a per-agent optimization increment, not an observed minimum robot–pedestrian gap. Both modified methods rebuild the ORCA optimization at every step to apply the current radius.')
    d.p('The predictive method computes a closest approach over the next 2 s using the robot’s straight-to-goal desired velocity and each pedestrian’s current velocity. Let d* be the minimum predicted boundary clearance. Its target is b = 0.15 × clip((0.60 − d*) / 0.60, 0, 1) m. Buffer increases take effect immediately; decreases are limited to 0.15 m/s. The 0.60 m trigger, 2 s horizon and maximum buffer were frozen before test cases were inspected. Both buffered methods execute the resulting ORCA velocity directly.')
    d.p('Measurements. Native goal, collision and timeout outcomes are retained. Minimum boundary clearance and physical overlap are independently checked along the continuous linear motion within each step. Close-proximity exposure is the time spent within 0.20 m of any pedestrian’s physical boundary, divided by observed episode duration; overlapping encounters are counted once. This is a benchmark proximity proxy, not measured comfort. Path length, actions, duration and every agent state are also logged.')
    d.p('Analysis. All three methods share initial states for each case. Because pedestrians cannot see the robot, their trajectories also match up to the earliest termination. Outcomes and proximity are reported over all 20 instances per method. Travel-time differences use only the same jointly successful cases, avoiding direct comparison of different survivor sets. Collision truncation still affects exposure; both exposure and outcomes must be read together. Configuration, source hashes and raw traces accompany the figures.')
    d.page()
    d.p('4. Preliminary evidence from the frozen test','Heading')
    d.table([['Method','Goals / 20','Collisions','Near time¹','Paired delay²'],['Original ORCA','12','8','17.74%','Reference'],['Fixed buffer','20','0','1.45%','+0.875 s'],['Predictive buffer','18','2','3.08%','+0.563 s']],[2500,1600,1600,2000,2206])
    d.p('¹ Mean of episode-level proximity fractions; 0.20 m boundary threshold. ² Mean difference from baseline on the same 12 jointly successful instances. No timeouts occurred. Native collisions and independently measured swept overlap agreed in all 60 rollouts.','Caption')
    d.image(ROOT/'outputs/figures/outcomes.png')
    d.p('Figure 1. Measured outcomes for 20 matched instances per method (10 per crossing pattern). These are descriptive results for a small deterministic benchmark; bars do not express a real-world population estimate.','Caption')
    d.image(ROOT/'outputs/figures/paired_paths.png')
    d.p('Figure 2. Actual trajectories for circle-crossing test case 100, the lowest test ID. Coloured lines show the robot; pale lines show pedestrians; the star marks the goal. The baseline terminates in collision at 2.50 s; fixed and predictive buffers reach the goal at 12.75 and 12.00 s. Different path lengths shown include different termination times.','Caption')
    d.p('Fixed buffering achieved 10/10 goals in each pattern, compared with 4/10 and 8/10 for the baseline. Predictive buffering achieved 9/10 in each. The fixed method therefore provides the strongest pilot result. Its extra completion time on matched successes is a cost, while the predictive method’s smaller paired delay accompanies two collisions. It did not dominate the fixed control. Supplementary videos include case 105, where predictive buffering also collides.')
    d.page()
    d.p('5. Proposed extension and expected findings','Heading')
    d.p('The next stage will evaluate two crossing patterns × three crowd sizes (3, 5 and 8) × two response settings (robot visible or invisible to pedestrians) × 30 new case IDs: 360 matched instances and 1,080 rollouts across the same three methods. Cases 200–229 will be reserved before execution. The existing buffer parameters will remain fixed for this primary comparison. Any later tuning will use a separate development set and require a new locked test set. The small, training-free pilot establishes local CPU feasibility; no cloud GPU is required.')
    d.p('The primary hypothesis is that fixed buffering improves collision-free completion over the original policy in non-responsive crowds. A second hypothesis is that predictive buffering reduces paired travel-time cost without reducing completion relative to fixed buffering. The present pilot does not support that second claim. The follow-up will report results by density and response setting, with paired differences and uncertainty intervals obtained by resampling matched cases within conditions. Completion, collision, proximity and time will remain separate outcomes; a failed episode will never be rewarded for ending quickly.')
    d.p('6. Uncertainty, ethics and transferability','Heading')
    d.p('Twenty instances per method cannot establish rare-event safety. Synthetic circular agents omit children, wheelchairs, group behaviour, distraction, perception errors and local walking conventions. Exact state access favours the controller, while invisible-robot pedestrians create a specific non-cooperative stress test. This setting violates the reciprocity premise behind an informal collision-free interpretation of ORCA. A zero-collision pilot result is therefore not a guarantee. The solver also produced a maximum speed of 1.000119 m/s against its nominal 1 m/s setting; this numerical deviation is recorded rather than silently corrected.')
    d.p('No personal or street-image data are collected in this experiment. Future field work would require consent or an appropriate observation protocol, minimal image retention and accessibility review. Moving to real urban sites would first require walls and pavement geometry, uncertain sensing, different pedestrian responses, and consultation about acceptable passing distances. The practical output is a reproducible decision aid for selecting a conservative navigation setting, with explicit evidence about its costs and limitations; humanoid or vision-language-action deployment is outside the present evidence.')
    d.p('References','Heading')
    refs=[
      '[1] Wu, W., et al. (2025). MetaUrban: An Embodied AI Simulation Platform for Urban Micromobility. ICLR. https://arxiv.org/abs/2407.08725',
      '[2] Kruse, T., Pandey, A. K., Alami, R., & Kirsch, A. (2013). Human-aware robot navigation: A survey. Robotics and Autonomous Systems, 61(12), 1726–1743. doi:10.1016/j.robot.2013.05.007',
      '[3] van den Berg, J., Guy, S. J., Lin, M., & Manocha, D. (2011). Reciprocal n-body collision avoidance. Robotics Research, 3–19. doi:10.1007/978-3-642-19457-3_1',
      '[4] Chen, C., Liu, Y., Kreiss, S., & Alahi, A. (2019). Crowd-Robot Interaction: Crowd-aware Robot Navigation with Attention-based Deep Reinforcement Learning. ICRA, 6015–6022. doi:10.1109/ICRA.2019.8794134',
      '[5] Francis, A., et al. (2023). Principles and Guidelines for Evaluating Social Robot Navigation Algorithms. arXiv:2306.16740.'
    ]
    for text in refs:d.p(text,'Caption')
    d.save(OUT/'Week3_Mini_Research_Proposal.docx')

if __name__=='__main__':proposal()
