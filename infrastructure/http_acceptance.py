"""Real loopback HTTP acceptance using disposable users and databases."""
import os,sys,tempfile,threading,time,socket,secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import app,identity,uvicorn,httpx
os.environ['FINAGENT_AUTH_MODE']='users'
with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
 app.app.state.db=app.engine('sqlite:///'+str(Path(tmp)/'control.db'));app.app.state.tenant_root=Path(tmp)/'tenants'
 a=identity.create_org('Acceptance A');b=identity.create_org('Acceptance B');password=secrets.token_urlsafe(24)
 for name,o,role in [('accept-a',a,'org_admin'),('accept-b',b,'org_admin'),('accept-read',a,'reader')]:identity.create_user(name,password,o['id'],role)
 sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 server=uvicorn.Server(uvicorn.Config(app.app,log_level='error'));thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
 try:
  for _ in range(100):
   if server.started:break
   time.sleep(.05)
  if not server.started:raise RuntimeError('HTTP test server failed to start')
  with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as client:
   assert client.get('/api/v1/jobs').status_code==401
   login=client.post('/api/v1/auth/login',json={'username':'accept-a','password':password});assert login.status_code==200;assert 'HttpOnly' in login.headers['set-cookie']
   task=client.post('/api/v1/jobs',json={'kind':'report','input':{}});assert task.status_code==202,task.text;tid=task.json()['task_id']
   for _ in range(100):
    result=client.get('/api/v1/jobs/'+tid).json()
    if result['status'] in ('completed','failed'):break
    time.sleep(.05)
   assert result['status']=='completed',result
   assert client.post('/api/v1/auth/login',json={'username':'accept-b','password':password}).status_code==200
   assert client.get('/api/v1/jobs/'+tid).status_code==404
   assert client.post('/api/v1/auth/login',json={'username':'accept-read','password':password}).status_code==200
   assert client.post('/api/v1/jobs',json={'kind':'report','input':{}}).status_code==403
   assert client.post('/api/v1/auth/logout').status_code==200
   assert client.get('/api/v1/jobs').status_code==401
  print('PASS: real HTTP cookie login, durable job, organization isolation, reader denial, logout')
 finally:
  server.should_exit=True;thread.join(5);sock.close()
  for key,e in list(identity.engines.items()):
   if key.startswith(tmp):e.dispose();identity.engines.pop(key)
  app.app.state.db.dispose()
