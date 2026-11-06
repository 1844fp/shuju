"""Real users-cookie HTTP -> workbench publish -> isolated PostgreSQL acceptance."""
import os,secrets,socket,threading,time,uuid,hashlib
from pathlib import Path
import app as core,identity,uvicorn,httpx,psycopg
root=Path(__file__).resolve().parents[1];base=root/'work/redesign'/('http-pg-'+uuid.uuid4().hex);base.mkdir()
old_db=getattr(core.app.state,'db',None);old_root=getattr(core.app.state,'tenant_root',None)
core.app.state.db=core.engine('sqlite:///'+str(base/'control.sqlite'));core.app.state.tenant_root=base/'tenants'
os.environ['FINAGENT_AUTH_MODE']='users';os.environ['FINAGENT_WAREHOUSE_URL']=os.environ['DATABASE_URL']
a=identity.create_org('Simulated HTTP A');b=identity.create_org('Simulated HTTP B');password=secrets.token_urlsafe(30)
for name,org in [('http-a',a),('http-b',b)]:identity.create_user(name,password,org['id'],'org_admin')
batch=uuid.uuid4()
with psycopg.connect(os.environ['DATABASE_URL']) as c:
 c.execute("INSERT INTO metadata.data_batch(id,organization_id,source_name,sha256,status,data_kind) VALUES(%s,%s,'simulated-http',%s,'completed','simulated')",(batch,a['id'],secrets.token_hex(32)))
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
server=uvicorn.Server(uvicorn.Config(core.app,log_level='error',access_log=False));thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
try:
 for _ in range(100):
  if server.started:break
  time.sleep(.05)
 assert server.started
 with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as client:
  path='/api/v1/finance-workbench/documents'
  assert client.get(path).status_code==401
  login=client.post('/api/v1/auth/login',json={'username':'http-a','password':password});assert login.status_code==200;assert 'HttpOnly' in login.headers['set-cookie']
  created=client.post(path,json={'external_id':'SIM-HTTP','kind':'invoice','date':'2026-01-01','amount':'25.50','data_kind':'simulated'});assert created.status_code==201,created.text
  row=created.json();jid=row['id'];raw=row['payload'].encode()
  for _ in range(2):
   published=client.post(path+'/'+jid+'/publish',json={'batch_id':str(batch)});assert published.status_code==200,published.text
  with psycopg.connect(os.environ['DATABASE_URL']) as c:
   rows=c.execute('SELECT original_content,source_sha256,original_payload FROM ods.workbench_evidence WHERE organization_id=%s AND document_id=%s',(a['id'],jid)).fetchall()
   assert len(rows)==1 and bytes(rows[0][0])==raw and rows[0][1]==hashlib.sha256(raw).hexdigest()
   assert rows[0][2]['data_kind']=='simulated'
  assert client.post('/api/v1/auth/login',json={'username':'http-b','password':password}).status_code==200
  assert client.post(path+'/'+jid+'/publish',json={'batch_id':str(batch)}).status_code==404
  own=client.post(path,json={'external_id':'SIM-B','kind':'invoice','date':'2026-01-01','amount':'1.00','data_kind':'simulated'});assert own.status_code==201
  assert client.post(path+'/'+own.json()['id']+'/publish',json={'batch_id':str(batch)}).status_code==404
 print('PASS R05: real loopback HTTP users cookie login -> create -> publish twice -> PostgreSQL exact bytes/hash/simulated label; foreign document and foreign batch 404')
finally:
 server.should_exit=True;thread.join(10);sock.close()
 assert not thread.is_alive(),'HTTP server did not stop'
 for key,e in list(identity.engines.items()):
  if str(base) in key:e.dispose();identity.engines.pop(key)
 core.app.state.db.dispose();core.app.state.db=old_db
 if old_root is not None:core.app.state.tenant_root=old_root

