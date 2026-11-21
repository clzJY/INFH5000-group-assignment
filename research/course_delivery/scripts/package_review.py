"""Create review materials, excluding model files and copyrighted lecture slides."""
import argparse,hashlib,json,zipfile,datetime
from pathlib import Path
D=Path(__file__).resolve().parents[1];ROOT=D.parents[1]
p=argparse.ArgumentParser();p.add_argument('--records',type=Path,required=True);a=p.parse_args();a.records.mkdir(parents=True,exist_ok=True)
out=D/'delivery';out.mkdir(exist_ok=True)
files={}
for folder,name in [('report','INFH5000_Group_Report.pdf'),('presentation','INFH5000_Urban_Navigation.pptx'),('presentation','INFH5000_Narrated_Rehearsal.mp4'),('presentation','INFH5000_Urban_Navigation.pdf'),('presentation','English_Speaker_Script.pdf')]:files[name]=D/folder/name
for name in ['English_Speaker_Script.md','中文逐页讲解提示.md','INFH5000_Rehearsal.en.srt','rehearsal_metadata.json']:files['notes/'+name]=D/'presentation'/name
for name in ['README.md','REQUIREMENTS_AUDIT_zh.md','RECORDING_GUIDE_zh.md','TECHNICAL_SUPPLEMENT.md','FORWARD_TO_GROUP_zh.md']:files[name]=D/name
files['latex_source/report/INFH5000_Group_Report.tex']=D/'report/INFH5000_Group_Report.tex'
for f in (D/'assets').iterdir():
 if f.is_file():files['latex_source/assets/'+f.name]=f
files['metadata/group_metadata.json']=D/'source/group_metadata.json'
for family in ('X','S','SC'):files[f'native_videos/native_{family}_comparison.mp4']=ROOT/f'research/results/videos/native_{family}_comparison.mp4'
assert all(f.is_file() for f in files.values());assert not any(f.suffix.lower() in ('.pt','.pth','.bin','.safetensors','.ckpt','.onnx') for f in files.values())
target=out/'INFH5000_Review_Materials_20261121.zip';inventory=[]
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,f in sorted(files.items()):
  z.write(f,name);inventory.append(dict(path=name,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 for row in inventory:
  blob=z.read(row['path']);assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256']
manifest=dict(archive_file=target.name,archive_bytes=target.stat().st_size,archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),files=len(inventory),all_members_verified=True,model_weights_included=False,course_lecture_pdf_included=False,review_only=True,team_metadata_pending=True,inventory=inventory)
(a.records/('review_bundle_manifest_'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')).write_text(json.dumps(manifest,indent=2)+'\n')
assets=[target,*[files[n] for n in ['INFH5000_Group_Report.pdf','INFH5000_Urban_Navigation.pptx','INFH5000_Narrated_Rehearsal.mp4','English_Speaker_Script.pdf']]]
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in assets))
print(json.dumps({k:v for k,v in manifest.items() if k!='inventory'}))
