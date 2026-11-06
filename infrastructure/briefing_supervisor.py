"""Trusted local briefing supervision; see docs/BRIEFING_SUPERVISOR.md."""
import argparse,json,os,sys,time,subprocess,uuid,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for n in ('runtime','agent-runtime','export-runtime','document-runtime'):sys.path.insert(0,str(ROOT/'work'/n))
import psutil

def inside(value,work=False):
 p=(ROOT/value).resolve()
 if Path(value).is_absolute() or not p.is_relative_to((ROOT/'work') if work else ROOT):raise ValueError('path must be project relative and within allowed root')
 return p

def config(path):
 p=inside(path,True);c=json.loads(p.read_text(encoding='utf-8-sig'))
 allowed={'database','organization','state_dir','interval_seconds','heartbeat_seconds','backoff_seconds','max_backoff_seconds','stop_timeout_seconds'}
 if set(c)-allowed or not isinstance(c.get('organization'),str) or not c['organization'].strip() or len(c['organization'])>100:raise ValueError('explicit organization and known configuration fields required')
 db=inside(c['database']);state=inside(c['state_dir'],True)
 if not db.is_file() or db==state or db.is_relative_to(state):raise ValueError('existing SQLite database required outside state directory')
 for k,default,low,high in [('interval_seconds',30,1,3600),('heartbeat_seconds',1,.1,10),('backoff_seconds',1,.1,30),('max_backoff_seconds',30,.1,300),('stop_timeout_seconds',10,1,60)]:
  v=c.get(k,default)
  if type(v) not in (int,float) or not low<=v<=high:raise ValueError('invalid '+k)
  c[k]=v
 if c['max_backoff_seconds']<c['backoff_seconds']:raise ValueError('invalid backoff range')
 c.update(database_path=str(db),state_path=str(state));return c

def read(p):
 for attempt in range(40):
  try:return json.loads(p.read_text(encoding='utf-8'))
  except FileNotFoundError:return {}
  except PermissionError:
   if attempt==39:raise
   time.sleep(.025)
def write(p,x):
 tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
 try:
  tmp.write_text(json.dumps(x,ensure_ascii=False),encoding='utf-8')
  for attempt in range(40):
   try:os.replace(tmp,p);return
   except PermissionError:
    if attempt==39:raise
    time.sleep(.025)
 finally:tmp.unlink(missing_ok=True)
def record(pid):
 p=psutil.Process(pid);return dict(pid=pid,created=p.create_time(),command=p.cmdline())
def owned(r):
 try:
  p=psutil.Process(r['pid'])
  return p if abs(p.create_time()-r['created'])<.01 and p.cmdline()==r['command'] and p.is_running() and p.status()!=psutil.STATUS_ZOMBIE else None
 except (KeyError,psutil.NoSuchProcess,psutil.AccessDenied):return None

def request(p,token):write(p,{'token':token})
def requested(p,token):return read(p).get('token')==token

def event(state,kind,**kw):
 with (state/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(time=time.time(),event=kind,**kw))+'\n')

def terminate(r,timeout):
 p=owned(r)
 if not p:return False
 p.terminate()
 try:p.wait(timeout)
 except psutil.TimeoutExpired:raise RuntimeError('owned process did not stop; manual review required')
 return True

class Lock:
 def __init__(self,p):self.p=p
 def __enter__(self):
  self.f=self.p.open('a+b');self.f.seek(0);self.f.write(b'0');self.f.flush();self.f.seek(0)
  try:
   if os.name=='nt':
    import msvcrt;msvcrt.locking(self.f.fileno(),msvcrt.LK_NBLCK,1)
   else:
    import fcntl;fcntl.flock(self.f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except OSError:self.f.close();raise RuntimeError('supervisor state is already locked')
  return self
 def __exit__(self,*args):self.f.close()

def child(c,state,token,parent):
 sys.path.insert(0,str(ROOT/'backend'));worker=runpy.run_path(str(ROOT/'backend/briefing_worker.py'))
 while not requested(state/'child-stop.json',token) and owned(parent):
  write(state/'child-heartbeat.json',dict(token=token,time=time.time(),phase='tick'))
  sys.argv=['briefing_worker','--database','sqlite:///'+c['database_path'],'--organization',c['organization'],'--once']
  worker['main']()
  write(state/'child-heartbeat.json',dict(token=token,time=time.time(),phase='waiting'))
  deadline=time.monotonic()+c['interval_seconds']
  while time.monotonic()<deadline:
   if requested(state/'child-stop.json',token) or not owned(parent):return
   time.sleep(min(.1,max(0,deadline-time.monotonic())))

def supervise(c,config_arg):
 state=Path(c['state_path']);state.mkdir(parents=True,exist_ok=True)
 with Lock(state/'owner.lock'):
  old=read(state/'state.json')
  if owned(old.get('supervisor',{})):raise RuntimeError('supervisor already running')
  if owned(old.get('child',{})):
   request(state/'child-stop.json',old['token']);time.sleep(.2);terminate(old['child'],c['stop_timeout_seconds'])
  token=uuid.uuid4().hex;me=record(os.getpid());info=dict(token=token,supervisor=me,child={},status='starting',restarts=0,heartbeat=time.time(),forced=False)
  write(state/'state.json',info);event(state,'supervisor_started')
  proc=None;delay=c['backoff_seconds'];next_start=0;started=0
  try:
   while not requested(state/'stop.json',token):
    now=time.monotonic()
    if proc is not None and proc.poll() is not None:
     event(state,'worker_exited',returncode=proc.returncode,backoff_seconds=delay);info['restarts']+=1;info['status']='backoff';next_start=now+delay;delay=min(delay*2,c['max_backoff_seconds']);proc=None;info['child']={}
    if proc is None and now>=next_start:
     cmd=[sys.executable,str(Path(__file__).resolve()),'child','--config',config_arg,'--token',token]
     with (state/'worker.log').open('ab') as f:proc=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=f,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
     info['child']=record(proc.pid);info['status']='running';started=now;event(state,'worker_started',pid=proc.pid)
    if proc is not None and now-started>=c['interval_seconds']:delay=c['backoff_seconds']
    info['heartbeat']=time.time();write(state/'state.json',info);time.sleep(c['heartbeat_seconds'])
  finally:
   request(state/'child-stop.json',token)
   info['status']='stopping'
   try:write(state/'state.json',info)
   except OSError:event(state,'state_write_failed')
   if proc:
    try:proc.wait(c['stop_timeout_seconds'])
    except subprocess.TimeoutExpired:info['forced']=terminate(info['child'],c['stop_timeout_seconds']);proc.wait(c['stop_timeout_seconds'])
   info.update(status='stopped',heartbeat=time.time());write(state/'state.json',info);event(state,'supervisor_stopped',forced=info['forced'])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['start','run','status','stop','child']);p.add_argument('--config',required=True);p.add_argument('--token',help=argparse.SUPPRESS);a=p.parse_args();c=config(a.config);state=Path(c['state_path'])
 if a.action=='run':supervise(c,a.config);return
 if a.action=='child':
  info=read(state/'state.json')
  if info.get('token')!=a.token or not owned(info.get('supervisor',{})):raise RuntimeError('unowned child')
  child(c,state,a.token,info['supervisor']);return
 info=read(state/'state.json')
 if a.action=='status':
  print(json.dumps(dict(**info,supervisor_running=bool(owned(info.get('supervisor',{}))),worker_running=bool(owned(info.get('child',{}))),worker_heartbeat=read(state/'child-heartbeat.json'))));return
 if a.action=='stop':
  if not owned(info.get('supervisor',{})):raise RuntimeError('no matching supervisor; no stop sent')
  request(state/'stop.json',info['token']);deadline=time.monotonic()+c['stop_timeout_seconds']*2+3
  while owned(info['supervisor']) and time.monotonic()<deadline:time.sleep(.1)
  if owned(info['supervisor']):raise RuntimeError('supervisor stop timed out; no unverified termination')
  print('stopped');return
 if owned(info.get('supervisor',{})):raise RuntimeError('supervisor already running')
 state.mkdir(parents=True,exist_ok=True)
 with (state/'supervisor.log').open('ab') as f:proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'run','--config',a.config],cwd=ROOT,stdout=f,stderr=f,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  if proc.poll() is not None:raise RuntimeError('supervisor startup failed; inspect supervisor.log')
  new=read(state/'state.json')
  if new.get('supervisor',{}).get('pid')==proc.pid and owned(new['supervisor']):print('started');return
  time.sleep(.1)
 raise RuntimeError('startup timeout; inspect status')
if __name__=='__main__':main()
