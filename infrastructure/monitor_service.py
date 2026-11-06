"""Manage only the owned background readiness monitor; never adopt other processes."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/runtime'));sys.path.insert(0,str(ROOT))
import psutil
BASE=ROOT/'work/operations'

def owned(record):
    try:
        process=psutil.Process(record['pid'])
        if abs(process.create_time()-record['created'])<.01 and process.cmdline()==record['command']:return process
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['start','status','stop']);a=p.parse_args()
    BASE.mkdir(parents=True,exist_ok=True);path=BASE/'monitor-process.json'
    record=json.loads(path.read_text()) if path.exists() else None
    process=owned(record) if record else None
    if a.action=='status':
        state=json.loads((BASE/'alerts-state.json').read_text()) if (BASE/'alerts-state.json').exists() else None
        print(json.dumps(dict(running=process is not None,pid=process.pid if process else None,state=state)));return
    if a.action=='stop':
        if process:process.terminate();process.wait(timeout=10)
        path.unlink(missing_ok=True);print('Owned monitor stopped');return
    if process:print('Owned monitor already running');return
    command=[sys.executable,'-m','infrastructure.production.alerts','--state',str(BASE/'alerts-state.json'),'--events',str(BASE/'alerts.jsonl'),'--interval','15']
    with (BASE/'monitor.log').open('ab') as log:
        child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
    time.sleep(.3)
    if child.poll() is not None:raise RuntimeError('monitor exited; inspect work/operations/monitor.log')
    process=psutil.Process(child.pid)
    path.write_text(json.dumps(dict(pid=process.pid,created=process.create_time(),command=process.cmdline())),encoding='utf-8')
    print(json.dumps(dict(running=True,pid=process.pid,event_file=str(BASE/'alerts.jsonl'))))
if __name__=='__main__':main()
