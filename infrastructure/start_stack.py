"""Local stack manager. Requires psutil; never adopts existing listeners."""
import argparse,json,os,socket,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('runtime','agent-runtime','export-runtime'):sys.path.insert(0,str(ROOT/'work'/name))
import psutil

def owned(record):
 try:
  p=psutil.Process(record['pid'])
  return p if abs(p.create_time()-record['created'])<0.01 and p.cmdline()==record['command'] else None
 except (psutil.NoSuchProcess,psutil.AccessDenied):return None

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['start','status','stop','backend']);p.add_argument('--backend-port',type=int,default=8000);p.add_argument('--frontend-port',type=int,default=3000);p.add_argument('--state',default='work/stack');p.add_argument('--isolated',action='store_true');a=p.parse_args()
 state=(ROOT/a.state).resolve()
 if not state.is_relative_to(ROOT/'work'):p.error('state must be inside project work/')
 state.mkdir(parents=True,exist_ok=True);record=state/'processes.json'
 if a.action=='backend':
  sys.path.insert(0,str(ROOT/'backend'));import app,uvicorn
  app.app.state.db=app.engine()
  if a.isolated:app.app.state.tenant_root=state/'tenants'
  uvicorn.run(app.app,host='127.0.0.1',port=a.backend_port);return
 records=json.loads(record.read_text()) if record.exists() else []
 if a.action=='status':
  print(json.dumps([{**r,'running':owned(r) is not None} for r in records],indent=2));return
 if a.action=='stop':
  for r in reversed(records):
   proc=owned(r)
   if proc:
    proc.terminate()
    try:proc.wait(10)
    except psutil.TimeoutExpired:raise RuntimeError('Process did not stop; no forced kill performed')
  record.unlink(missing_ok=True);print('Stopped owned processes');return
 if records:raise RuntimeError('State exists; inspect status and stop first')
 for port in (a.backend_port,a.frontend_port):
  with socket.socket() as s:s.bind(('127.0.0.1',port))
 env=os.environ.copy()
 if a.isolated:env['DATABASE_URL']='sqlite:///'+str(state/'isolated.sqlite')
 commands=[('backend',[sys.executable,str(Path(__file__).resolve()),'backend','--backend-port',str(a.backend_port),'--state',str(state)]+(['--isolated'] if a.isolated else []),ROOT,a.backend_port,'/api/v1/ready'),('frontend',['node',str(ROOT/'frontend/next/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(a.frontend_port)],ROOT/'frontend/next',a.frontend_port,'/')]
 try:
  for name,cmd,cwd,port,path in commands:
   with (state/(name+'.log')).open('ab') as log:
    child=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
   proc=psutil.Process(child.pid);records.append(dict(name=name,pid=child.pid,created=proc.create_time(),command=proc.cmdline()));record.write_text(json.dumps(records))
   for attempt in range(100):
    if child.poll() is not None:raise RuntimeError(name+' exited; inspect log')
    try:
     with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=1) as response:
      if response.status==200:break
    except Exception:time.sleep(.2)
   else:raise RuntimeError(name+' readiness timed out')
  print('Started; frontend proxy uses the backend configured at Next build time')
 except Exception:
  for r in reversed(records):
   proc=owned(r)
   if proc:proc.terminate();proc.wait(10)
  record.unlink(missing_ok=True);raise
if __name__=='__main__':main()
