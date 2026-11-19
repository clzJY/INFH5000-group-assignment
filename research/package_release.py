"""Package recorded research data without model weights or runtime asset symlinks."""
import argparse,gzip,hashlib,json,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUITES=['main_classical_v1','main_visual_v1','model_seed_variation_v1','input_ablations_v1','holdout_curve_v1','challenge_test_v1','native_demonstrations']

def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['training','evaluation']);p.add_argument('--output',type=Path,required=True);p.add_argument('--records',type=Path,required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.parent.mkdir(parents=True,exist_ok=True);assert not a.output.exists()
    if a.kind=='training':
        files=sorted(p for p in (ROOT/'research/training_data').rglob('*') if p.is_file() and not p.is_symlink() and 'adapters' not in p.relative_to(ROOT/'research/training_data').parts and p.suffix.lower() not in ('.pt','.pth','.bin','.safetensors','.ckpt','.onnx'))
    else:
        files=[]
        for suite in SUITES:
            base=ROOT/'research/runs'/suite;plan=json.loads((base/'plan.json').read_text());files.append(base/'plan.json')
            for row in plan:
                case=base/('{map}_{width}_p{pedestrians}_s{seed}_{method}'.format(**row))
                summary=json.loads((case/'summary.json').read_text());assert summary['status'] in ('complete','invalid_task')
                for name in ('config.json','summary.json','scene.json','steps.jsonl','vlm_queries.json','first_frame.png','rollout.mp4'):
                    path=case/name
                    if path.is_file():files.append(path)
        files=sorted(files)
    assert files
    inventory=[];temporary=a.output.with_suffix(a.output.suffix+'.partial');assert not temporary.exists();started=time.monotonic()
    with temporary.open('xb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as compressed:
            with tarfile.open(fileobj=compressed,mode='w') as archive:
                for path in files:
                    relative=str(path.relative_to(ROOT));info=archive.gettarinfo(str(path),arcname=relative)
                    info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;info.mode=0o644
                    with path.open('rb') as source:archive.addfile(info,source)
                    inventory.append(dict(path=relative,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    temporary.replace(a.output)
    result=dict(kind=a.kind,archive=str(a.output),archive_bytes=a.output.stat().st_size,archive_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),files=len(files),source_bytes=sum(r['bytes'] for r in inventory),elapsed_s=time.monotonic()-started,
        packaging='Regular recorded files only; no asset links, environment, backbone, adapter tensors or optimizer state. Archive ownership/timestamps normalized; file contents unchanged.',inventory=inventory)
    a.records.mkdir(parents=True,exist_ok=True)
    (a.records/(a.kind+'_package_'+time.strftime('%Y%m%d-%H%M%S')+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inventory'},indent=2))

if __name__=='__main__':main()
