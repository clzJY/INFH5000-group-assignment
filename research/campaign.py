"""Resumable campaign: unique episode directories, central logs, no hidden retries."""
import argparse,itertools,json,os,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=ROOT/'envs/python311/bin/python3'

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--seeds',type=int,nargs='+',required=True);p.add_argument('--methods',nargs='+',default=['lattice']);p.add_argument('--maps',nargs='+',default=['X','S','SC']);p.add_argument('--widths',nargs='+',default=['narrow','wide']);p.add_argument('--counts',type=int,nargs='+',default=[5,15]);p.add_argument('--workers',type=int,default=3);p.add_argument('--collect',action='store_true');p.add_argument('--server',default='http://127.0.0.1:18761');a=p.parse_args()
    op=Path((ROOT/'research/active_operation.txt').read_text().strip());base=ROOT/'research/runs'/a.name;base.mkdir(parents=True,exist_ok=True)
    plan=[dict(map=m,width=w,pedestrians=n,seed=s,method=b) for m,w,n,s,b in itertools.product(a.maps,a.widths,a.counts,a.seeds,a.methods)]
    f=base/'plan.json'
    if f.exists():assert json.loads(f.read_text())==plan
    else:f.write_text(json.dumps(plan,indent=2)+'\n')
    def run(row):
        name='{map}_{width}_p{pedestrians}_s{seed}_{method}'.format(**row);out=base/name
        if (out/'summary.json').exists():
            existing=json.loads((out/'summary.json').read_text())
            if existing['status'] in ('complete','invalid_task'):return dict(name=name,exit=0,existing=True)
        if out.exists():return dict(name=name,exit=99,existing_error=True)
        cmd=[str(PY),str(ROOT/'research/run_native.py'),'--output',str(out),'--stage',a.name,'--server',a.server]
        for k,v in row.items():cmd.extend(['--'+k,str(v)])
        if a.collect:cmd.append('--collect')
        with (op/'logs'/f'{a.name}_{name}.log').open('x') as log:
            try:code=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,CUDA_VISIBLE_DEVICES='3',INFH_EGL_DEVICE='3',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2'),timeout=600).returncode
            except subprocess.TimeoutExpired:code=124
        return dict(name=name,exit=code)
    results=[];started=time.monotonic()
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for future in as_completed([pool.submit(run,row) for row in plan]):
            result=future.result();results.append(result);print(json.dumps(dict(done=len(results),total=len(plan),elapsed_s=time.monotonic()-started,**result)),flush=True)
            (base/'campaign_status.json').write_text(json.dumps(dict(planned=len(plan),completed=len(results),errors=sum(r['exit']!=0 for r in results),results=results),indent=2)+'\n')
    if any(r['exit']!=0 for r in results):raise SystemExit(1)
if __name__=='__main__':main()
