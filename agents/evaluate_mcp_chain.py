"""External SDK stdio client -> unmodified MCP tools -> real users HTTP backend."""
import asyncio,os,sys,json,tempfile,threading,socket,time,csv,io,hashlib
from pathlib import Path
from urllib.request import Request,urlopen
from http.cookies import SimpleCookie
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
async def exercise(base,token,batch,scope):
 from mcp import ClientSession,StdioServerParameters
 from mcp.client.stdio import stdio_client
 env=dict(os.environ,FINAGENT_API_BASE=base,FINAGENT_TOKEN=token)
 results=[]
 async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','mcp_servers.finance'],env=env,cwd=str(ROOT))) as streams:
  async with ClientSession(*streams) as session:
   await session.initialize();tools=await session.list_tools()
   results.append({'check':scope+'_eight_tools','passed':len(tools.tools)==8})
   q={'start_period':'2026-01','end_period':'2026-12','currency':'CNY'}
   for name,args in [('get_report_evidence',q),('get_budget_execution',q),('review_financial_risks',q),('get_data_quality',{'batch_id':batch})]:
    response=await session.call_tool(name,args)
    if scope=='wrong':valid=bool(response.is_error);payload=None
    elif scope=='B':
     if name=='get_data_quality':valid=bool(response.is_error);payload=None
     else:
      payload=json.loads(response.content[0].text) if response.content else getattr(response,'structured_content',None)
      if payload is None:payload=[]
      if isinstance(payload,dict) and set(payload)=={'result'}:payload=payload['result']
      valid=not response.is_error and (payload.get('metrics')==[] if name=='get_report_evidence' else payload==[] if name=='get_budget_execution' else payload.get('items')==[])
    else:
     payload=json.loads(response.content[0].text) if response.content else getattr(response,'structured_content',None)
     if payload is None:payload=[]
     if isinstance(payload,dict) and set(payload)=={'result'}:payload=payload['result']
     valid=not response.is_error and (bool(payload.get('metrics')) and bool(payload.get('sources')) if name=='get_report_evidence' else bool(payload) if name=='get_budget_execution' else bool(payload.get('items')) if name=='review_financial_risks' else payload.get('accepted_rows',0)>0)
    results.append({'check':scope+'_'+name,'passed':valid,'is_error':bool(response.is_error),'public_simulated_payload':payload})
 return results

def main():
 import app as core,identity,integrations,uvicorn
 checks=[];start=time.monotonic();old=getattr(core.app.state,'db',None);oldroot=getattr(core.app.state,'tenant_root',None)
 with tempfile.TemporaryDirectory(dir=ROOT/'work') as temp:
  core.app.state.db=core.engine('sqlite:///'+str(Path(temp)/'control.sqlite'));core.app.state.tenant_root=Path(temp)/'tenants'
  with patch.dict(os.environ,{'FINAGENT_AUTH_MODE':'users'}):
   a=identity.create_org('MCP A');b=identity.create_org('MCP B')
   for username,org in [('mcp-user-a',a),('mcp-user-b',b)]:identity.create_user(username,'Test-only-MCP-129!',org['id'],'org_admin')
   db=identity.tenant_engine(a['id']);data=list(csv.DictReader(io.StringIO((ROOT/'data_platform/sample_vouchers.csv').read_text(encoding='utf-8-sig'))));batch=core.ingest(db,data,'r03-external-mcp','sample.csv',kind='simulated')
   # Deliberately tiny simulated budget ensures a nonempty risk response.
   integrations.ledger.create(db,checkfirst=True)
   with db.begin() as c:c.execute(integrations.ledger.insert().values(id='budget-r03',kind='budget',business_key='budget:r03',payload=json.dumps({'id':'budget-r03','kind':'budget','period':'2026-01','department':'D01','currency':'CNY','amount':'1.00','data_kind':'simulated'})))
   sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];base=f'http://127.0.0.1:{port}'
   server=uvicorn.Server(uvicorn.Config(core.app,lifespan='off',log_level='error'));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
   try:
    for _ in range(200):
     if server.started:break
     time.sleep(.01)
    def login(name):
     req=Request(base+'/api/v1/auth/login',data=json.dumps({'username':name,'password':'Test-only-MCP-129!'}).encode(),headers={'Content-Type':'application/json'})
     with urlopen(req,timeout=5) as response:cookie=SimpleCookie(response.headers['Set-Cookie'])
     return cookie['finagent_session'].value
    for scope,token in [('A',login('mcp-user-a')),('B',login('mcp-user-b')),('wrong','invalid-test-only')]:checks.extend(asyncio.run(exercise(base,token,batch['batch_id'],scope)))
   finally:
    server.should_exit=True;thread.join(5);sock.close()
    for key,engine in list(identity.engines.items()):
     if key.startswith(str(Path(temp))):engine.dispose();identity.engines.pop(key)
    core.app.state.db.dispose();core.app.state.db=old
    if oldroot is None:del core.app.state.tenant_root
    else:core.app.state.tenant_root=oldroot
 out=ROOT/'work/public-company/mcp-evaluation';out.mkdir(parents=True,exist_ok=True)
 result={'method':'actual SDK MCP stdio -> Bearer urllib -> real users TCP backend','seconds':round(time.monotonic()-start,3),'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'checks':checks,'external_model_calls':0}
 (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
 if result['failed']:raise SystemExit(1)
if __name__=='__main__':main()


