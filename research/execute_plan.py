"""Portable execution of a saved condition plan, with explicit external records.

This coordinator does not change the frozen scientific runner. Existing failed
or incomplete directories are reported rather than silently replaced.
"""
import argparse,json,os,subprocess,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--records',type=Path,required=True,help='Unique storage_management operation directory')
    p.add_argument('--python',type=Path,default=ROOT/'envs/python311/bin/python3')
    p.add_argument('--runner',choices=['run_native.py','run_challenge.py'],default='run_native.py')
    p.add_argument('--server',default='http://127.0.0.1:18762')
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--cuda-device',default='3')
    p.add_argument('--egl-device',default='3',help='EGL enumeration need not equal physical CUDA enumeration')
    p.add_argument('--timeout',type=float,default=600)
    p.add_argument('--runtime-cache',type=Path,help='Optional fast temporary/cache root, e.g. a private directory on /dev/shm')
    p.add_argument('--collect',action='store_true')
    p.add_argument('--video',action='store_true')
    a=p.parse_args()
    plan=json.loads(a.plan.read_text());assert plan and a.workers>0
    assert len(plan)==len({tuple(sorted(row.items())) for row in plan})
    a.output=a.output.resolve();a.records=a.records.resolve()
    if a.runtime_cache:
        a.runtime_cache=a.runtime_cache.resolve();a.runtime_cache.mkdir(parents=True,exist_ok=True,mode=0o700)
        for name in ('cache','nvidia'):(a.runtime_cache/name).mkdir(exist_ok=True,mode=0o700)
    a.output.mkdir(parents=True,exist_ok=True);(a.records/'logs').mkdir(parents=True,exist_ok=True)
    stored=a.output/'plan.json'
    if stored.exists():assert json.loads(stored.read_text())==plan
    else:stored.write_text(json.dumps(plan,indent=2)+'\n')
    def execute(row):
        name='{map}_{width}_p{pedestrians}_s{seed}_{method}'.format(**row)
        out=a.output/name
        if out.exists():
            summary=out/'summary.json'
            if summary.is_file():
                status=json.loads(summary.read_text())['status']
                return dict(name=name,exit=0 if status in ('complete','invalid_task') else 98,existing=True)
            return dict(name=name,exit=99,existing_incomplete=True)
        cmd=[str(a.python.resolve()),str(ROOT/'research'/a.runner),'--output',str(out),'--stage',a.output.name,'--server',a.server]
        for k,v in row.items():cmd.extend(['--'+k,str(v)])
        if a.collect:cmd.append('--collect')
        if a.video:cmd.append('--video')
        env=dict(os.environ,PYTHONHASHSEED=str(row['seed']),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2')
        # Respect job-local CUDA allocation when a scheduler has assigned it.
        if 'SLURM_JOB_ID' not in env:env['CUDA_VISIBLE_DEVICES']=a.cuda_device
        env['INFH_EGL_DEVICE']=a.egl_device
        if a.runtime_cache:
            env.update(TMPDIR=str(a.runtime_cache),XDG_CACHE_HOME=str(a.runtime_cache/'cache'),
                       __GL_SHADER_DISK_CACHE_PATH=str(a.runtime_cache/'nvidia'))
        started=time.monotonic()
        with (a.records/'logs'/(a.output.name+'_'+name+'.log')).open('x') as log:
            try:code=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout).returncode
            except subprocess.TimeoutExpired:code=124
        return dict(name=name,exit=code,wall_s=time.monotonic()-started)
    results=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for future in as_completed([pool.submit(execute,row) for row in plan]):
            result=future.result();results.append(result)
            print(json.dumps(dict(done=len(results),total=len(plan),**result)),flush=True)
            (a.records/(a.output.name+'_status.json')).write_text(json.dumps(dict(planned=len(plan),completed=len(results),errors=sum(r['exit']!=0 for r in results),results=results),indent=2)+'\n')
    if any(r['exit']!=0 for r in results):raise SystemExit(1)

if __name__=='__main__':main()
