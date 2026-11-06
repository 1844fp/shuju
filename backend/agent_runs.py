"""Organization-bound Harness HTTP adapter; deterministic read-only tools."""
import json, os
from pathlib import Path
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict
from sqlalchemy import MetaData,Table,Column,String,Text,select
import app as core
meta=MetaData();approvals=Table('metadata_agent_run_approval',meta,Column('id',String,primary_key=True),Column('organization',String),Column('maker',String),Column('reviewer',String),Column('decision',String),Column('reason',Text));runs=Table('metadata_agent_run',meta,Column('id',String,primary_key=True),Column('organization',String),Column('query',Text),Column('result',Text))
class Start(BaseModel):
 model_config=ConfigDict(extra='forbid')
 start_period:str='2026-01'
 end_period:str='2026-12'
 currency:str='CNY'
 intent:str|None=None
def scope():
 db=core.current_db();meta.create_all(db);return db,core.request_organization.get()
def execute(jid,query):
 from agents.harness import Harness
 from integrations import budget_report
 from finance_workbench import rows
 from finance_risk_engine import evaluate
 db,org=scope();query=dict(query);intent=query.pop('intent',None)
 def metrics(q,previous):return core.finance(**q)
 def audit(q,previous):
  from risk_adapters import review
  return review(**q)
 def data(q,previous):
  batches=core.batch_list()
  return {'metric_version':'1.0','batches':batches,'batch_ids':[b['batch_id'] for b in batches],'scope':'all authorized organization imports; quality includes all periods'}
 def report(q,previous):
  return {'markdown':core.report(**q),'mode':'deterministic','evidence':previous,'sources':{'batch_ids':previous.get('data',{}).get('batch_ids',[]),'risk_rule_version':previous.get('audit',{}).get('rule_version')},'limitations':['quarantined ERP rows excluded from committed vouchers; inspect data quality; missing rule inputs remain not_evaluated','risk leads require human review']}
 tools={'data':data,'analysis':metrics,'budget':lambda q,p:budget_report(q['start_period'],q['end_period'],q['currency']),'audit':audit,'report':report}
 with db.connect() as c:approval=c.execute(select(approvals).where(approvals.c.id==jid,approvals.c.organization==org)).mappings().first()
 if not approval or approval['decision']=='rejected':raise HTTPException(409,'运行审批不存在或已拒绝')
 harness=Harness(Path(os.getenv('FINAGENT_HARNESS_PATH',str(Path(core.ROOT)/'work'/'harness'/'checkpoints.sqlite'))))
 if intent:
  from agents.task_memory import TaskMemory
  def authorized_refs():
   refs={}
   with db.connect() as c:
    for row in c.execute(select(core.batches)).mappings():
     if row['kind']!='simulated':raise HTTPException(409,'任务记忆仅允许经授权模拟证据')
     refs[row['id']]=row['sha256']
   for row in rows():
    if json.loads(row['payload'])['data_kind']!='simulated':raise HTTPException(409,'任务记忆仅允许模拟工作台记录')
    refs[row['id']]=row['snapshot_hash']
   from integrations import register_rows
   if register_rows():raise HTTPException(409,'任务记忆尚未授权台账原文')
   return refs
  current=authorized_refs()
  memory=TaskMemory(harness.path.with_name('task-memory.sqlite'));prior=memory.load(org,jid)
  references=prior['references'] if prior else [{'id':k,'sha256':v} for k,v in current.items()]
  result=memory.run(harness,jid,org,query,tools,intent=intent,data_kind='simulated',references=references,resolve_source=lambda organization,key:authorized_refs().get(key) if organization==org else None,approved=approval['decision']=='approved')
  if any(authorized_refs().get(r['id'])!=r['sha256'] for r in references):raise HTTPException(409,'执行中来源变化')
 else:result=harness.run(jid,org,query,tools,approved=approval['decision']=='approved')
 with db.begin() as c:c.execute(runs.update().where(runs.c.id==jid,runs.c.organization==org).values(result=json.dumps(result,ensure_ascii=False)))
 return result
def install(app):
 @app.post('/api/v1/agent-runs',status_code=201)
 def create(body:Start):
  q=body.model_dump();intent=q.pop('intent');core.finance(**q)
  if intent is not None and intent not in ('finance','budget','risk','full'):raise HTTPException(422,'未授权计划')
  if intent:q['intent']=intent
  db,org=scope();jid=core.uid()
  who=core.request_actor.get()
  if not who:raise HTTPException(401,'需要用户身份')
  with db.begin() as c:
   c.execute(runs.insert().values(id=jid,organization=org,query=json.dumps(q)))
   c.execute(approvals.insert().values(id=jid,organization=org,maker=who['id'],decision='pending'))
  return execute(jid,q)
 @app.get('/api/v1/agent-runs')
 def listing():
  db,org=scope()
  with db.connect() as c:return [{'task_id':r['id'],'query':json.loads(r['query']),'result':json.loads(r['result']) if r['result'] else None} for r in c.execute(select(runs).where(runs.c.organization==org)).mappings()]
 @app.get('/api/v1/agent-runs/{jid}')
 def detail(jid:str):
  for r in listing():
   if r['task_id']==jid:return r
  raise HTTPException(404,'运行不存在')
 @app.post('/api/v1/agent-runs/{jid}/resume')
 def resume(jid:str):return execute(jid,detail(jid)['query'])

 @app.post('/api/v1/agent-runs/{jid}/review')
 def review(jid:str,body:dict):
  detail(jid);db,org=scope();who=core.request_actor.get()
  if not who or who['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要独立管理员')
  if set(body)!={'decision','reason'} or body['decision'] not in ('approved','rejected') or not str(body['reason']).strip():raise HTTPException(422,'审批参数无效')
  with db.begin() as c:
   r=c.execute(select(approvals).where(approvals.c.id==jid,approvals.c.organization==org)).mappings().first()
   if not r or r['maker']==who['id']:raise HTTPException(403,'禁止自审')
   n=c.execute(approvals.update().where(approvals.c.id==jid,approvals.c.organization==org,approvals.c.decision=='pending').values(reviewer=who['id'],decision=body['decision'],reason=str(body['reason']))).rowcount
   if not n:raise HTTPException(409,'审批已处理')
  return {'task_id':jid,'decision':body['decision']}

