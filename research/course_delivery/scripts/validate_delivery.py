"""Check course constraints and media integrity; fail closed for missing team data."""
import argparse,json,re,subprocess,zipfile,xml.etree.ElementTree as ET,collections
from pathlib import Path
D=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--require-team',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
g=json.loads((D/'source/group_metadata.json').read_text());missing=[]
if not g.get('group_id'):missing.append('group_id')
ms=g['members'];assert 4<=len(ms)<=5
for i,m in enumerate(ms):
 for field in ('name','thrust','actual_work','contribution_percent'):
  if m.get(field) is None or m.get(field)=='':missing.append(f'members[{i}].{field}')
 if m.get('contribution_percent') is not None:assert 0<=m['contribution_percent']<=100
complete=not missing
if complete:
 assert abs(sum(m['contribution_percent'] for m in ms)-100)<1e-6,'Work shares must sum to 100%'
 assert len({m['name'].strip().lower() for m in ms})==len(ms),'Duplicate members'
 counts=collections.Counter('NEW_RBM' if m.get('new_rbm_student') else m['thrust'].strip().lower() for m in ms)
 assert max(counts.values())<=3,'More than 3 members from one effective thrust; clarify RBM treatment with course staff if applicable'
info=subprocess.check_output(['pdfinfo',str(D/'report/INFH5000_Group_Report.pdf')],text=True);pages=int(re.search(r'Pages:\s+(\d+)',info)[1]);assert pages-2>=6
tex=(D/'report/INFH5000_Group_Report.tex').read_text();assert r'\documentclass[a4paper,12pt]' in tex and r'\geometry{margin=1in}' in tex and r'\setstretch{1.5}' in tex
ppt=D/'presentation/INFH5000_Urban_Navigation.pptx';ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(ppt) as z:
 assert z.testzip() is None
 slidefiles=sorted(n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n));assert len(slidefiles)==17
 videos=[n for n in z.namelist() if n.startswith('ppt/media/') and n.endswith('.mp4')];assert len(videos)==3
 assert len([n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)])==17
 textcounts=[]
 for name in slidefiles:
  tree=ET.fromstring(z.read(name));textcounts.append(len(tree.findall('.//a:t',ns)))
  for obj in tree.findall('.//p:sp',ns)+tree.findall('.//p:pic',ns)+tree.findall('.//p:graphicFrame',ns):
   xf=obj.find('.//a:xfrm',ns)
   if xf is None:continue
   off=xf.find('a:off',ns);ext=xf.find('a:ext',ns)
   if off is not None:assert int(off.attrib['x'])>=0 and int(off.attrib['y'])>=0
   if ext is not None:assert int(ext.attrib['cx'])>0 and int(ext.attrib['cy'])>0
meta=json.loads((D/'presentation/rehearsal_metadata.json').read_text());assert meta['duration_s']<=600 and meta['native_video_excerpt_count']==3 and meta['synthetic_narration']
weights=[str(x) for x in D.rglob('*') if x.is_file() and x.suffix.lower() in ('.pt','.pth','.bin','.safetensors','.ckpt','.onnx')];assert not weights
result=dict(technical_checks_passed=True,report_pages=pages,course_template_checked=True,ppt_slides=len(slidefiles),embedded_native_videos=len(videos),speaker_note_pages=17,all_slides_have_editable_text=all(textcounts),rehearsal_duration_s=meta['duration_s'],mp4_under_10_minutes=True,model_weights_in_delivery=0,group_metadata_complete=complete,missing_group_fields=missing,submission_ready=False,submission_caveat='The supplied video is an explicitly synthetic rehearsal; team must decide/record the formal presentation and verify its real duration and identity.',group_rule_note='New RBM students grouped separately in this conservative check; ambiguous cases require course confirmation.')
if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(2 if a.require_team and not complete else 0)
