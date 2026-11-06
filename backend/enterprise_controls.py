"""Local analytical ingestion controls, not ERP posting or payment authority."""
import hashlib,json,os,re,threading
from fastapi import HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import MetaData,Table,Column,String,Integer,Text,select
from sqlalchemy.exc import IntegrityError

META=MetaData();LOCK=threading.RLock()
PERIODS=Table('metadata_control_period',META,Column('period',String,primary_key=True),Column('status',String),Column('version',Integer),Column('actor',String),Column('reason',Text),Column('updated',String))
EVENTS=Table('metadata_control_event',META,Column('sequence',Integer,primary_key=True,autoincrement=True),Column('payload',Text),Column('previous_hash',String),Column('event_hash',String))
APPROVALS=Table('metadata_import_approval',META,Column('id',String,primary_key=True),Column('run_id',String),Column('cleaning_token',String),Column('source_digest',String),Column('snapshot_hash',String),Column('maker',String),Column('reviewer',String),Column('status',String),Column('reason',Text),Column('created',String),Column('reviewed',String))
def host():
 import app
 return app
def initialize(database):META.create_all(database)
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def actor():return host().request_actor.get()
def strict():return os.getenv('FINAGENT_ERP_APPROVAL_REQUIRED')=='1'
def snapshot_hash(value):return hashlib.sha256(canonical({k:value.get(k) for k in ('cleaned_rows','quality','options','account_catalog_sha256')}).encode()).hexdigest()
def append(connection,action,resource,details=None):
 who=actor();payload=canonical(dict(action=action,resource=resource,actor=who['id'] if who else 'demo-local-operator',auth_mode=os.getenv('FINAGENT_AUTH_MODE','demo'),organization=host().request_organization.get(),created=host().now(),details=details or {}))
 previous=connection.execute(select(EVENTS.c.event_hash).order_by(EVENTS.c.sequence.desc()).limit(1)).scalar() or '0'*64
 digest=hashlib.sha256((previous+'\n'+payload).encode()).hexdigest()
 connection.execute(EVENTS.insert().values(payload=payload,previous_hash=previous,event_hash=digest));return digest
def assert_open(connection,periods):
 valid={p for p in periods if re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])',p)}
 if not valid:return
 locked=list(connection.execute(select(PERIODS.c.period).where(PERIODS.c.period.in_(valid),PERIODS.c.status=='closed')).scalars())
 if locked:raise HTTPException(409,'中台数据账期已锁定：'+','.join(sorted(locked)))
def assert_approval(connection,reference,digest,bootstrap=False,kind=None):
 if not strict():return
 if os.getenv('FINAGENT_AUTH_MODE')!='users':raise HTTPException(503,'严格复核必须启用users身份模式')
 if bootstrap and kind=='simulated':return
 if not reference:raise HTTPException(409,'严格模式禁止直接入库，请使用ERP双人复核流程')
 row=connection.execute(select(APPROVALS).where(APPROVALS.c.id==reference)).mappings().first()
 if not row or row['status']!='approved' or row['source_digest']!=digest or row['maker']==row['reviewer']:raise HTTPException(409,'缺少与当前数据快照一致的独立复核')
 from erp_imports import get
 value=get(row['run_id'])
 if value.get('cleaning_token')!=row['cleaning_token'] or value.get('cleaned_by')!=row['maker'] or snapshot_hash(value)!=row['snapshot_hash']:raise HTTPException(409,'清洗内容或制单身份已变化，须重新复核')
def approval_for(value):
 identifier=hashlib.sha256((value['id']+'|'+value['cleaning_token']).encode()).hexdigest()
 return identifier
class PeriodChange(BaseModel):
 model_config=ConfigDict(extra='forbid')
 expected_version:int=Field(ge=0)
 reason:str=Field(min_length=3,max_length=300)
class Review(BaseModel):
 model_config=ConfigDict(extra='forbid')
 decision:str
 reason:str=Field(min_length=3,max_length=300)
def change_period(period,state,body):
 if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])',period):raise ValueError('账期须YYYY-MM')
 database=host().current_db();initialize(database)
 try:
  with LOCK,database.begin() as c:
   current=c.execute(select(PERIODS).where(PERIODS.c.period==period)).mappings().first();version=current['version'] if current else 0
   if body.expected_version!=version:raise HTTPException(409,'账期版本已变化，请重新读取')
   if current and current['status']==state:return dict(current)
   value=dict(period=period,status=state,version=version+1,actor=(actor() or {'id':'demo-local-operator'})['id'],reason=body.reason,updated=host().now())
   if current:
    n=c.execute(PERIODS.update().where(PERIODS.c.period==period,PERIODS.c.version==version).values(**value)).rowcount
    if n!=1:raise HTTPException(409,'账期并发修改')
   else:c.execute(PERIODS.insert().values(**value))
   append(c,'period_'+state,period,dict(reason=body.reason,version=version+1))
   return value
 except IntegrityError:raise HTTPException(409,'账期并发修改，请重试') from None
def verify(database):
 initialize(database);previous='0'*64;count=0
 with database.connect() as c:
  for row in c.execute(select(EVENTS).order_by(EVENTS.c.sequence)).mappings():
   expected=hashlib.sha256((previous+'\n'+row['payload']).encode()).hexdigest()
   if row['previous_hash']!=previous or row['event_hash']!=expected:return dict(valid=False,checked=count,first_invalid_sequence=row['sequence'])
   previous=row['event_hash'];count+=1
 return dict(valid=True,checked=count,last_hash=previous,scope='local hash chain; no external immutable anchor')

def install(app):
 @app.get('/api/v1/enterprise/policy')
 def policy():return dict(approval_required=strict(),authentication=os.getenv('FINAGENT_AUTH_MODE','demo'),scope='middle-platform data acceptance only; no ERP posting')
 @app.get('/api/v1/enterprise/periods')
 def periods():
  initialize(host().current_db())
  with host().current_db().connect() as c:return [dict(r) for r in c.execute(select(PERIODS).order_by(PERIODS.c.period)).mappings()]
 @app.post('/api/v1/enterprise/periods/{period}/close')
 def close(period:str,body:PeriodChange):return change_period(period,'closed',body)
 @app.post('/api/v1/enterprise/periods/{period}/reopen')
 def reopen(period:str,body:PeriodChange):return change_period(period,'open',body)
 @app.post('/api/v1/erp/runs/{identifier}/request-approval',status_code=201)
 def request(identifier:str):
  if not strict() or os.getenv('FINAGENT_AUTH_MODE')!='users' or not actor():raise HTTPException(409,'仅users严格模式可发起双人复核')
  from erp_imports import get,sha
  value=get(identifier)
  if value['status']!='cleaned' or not value['quality']['valid_rows'] or value['quality']['commit_blocked']:raise HTTPException(422,'须先完成有效清洗')
  if value.get('cleaned_by')!=actor()['id']:raise HTTPException(403,'须由本次清洗操作人发起')
  database=host().current_db();initialize(database);aid=approval_for(value)
  with LOCK,database.begin() as c:
   old=c.execute(select(APPROVALS).where(APPROVALS.c.id==aid)).mappings().first()
   if old:return dict(old)
   item=dict(id=aid,run_id=identifier,cleaning_token=value['cleaning_token'],source_digest=sha(('erp-v1|'+value['ledger_id']+'|'+value['file_sha256']).encode()),snapshot_hash=snapshot_hash(value),maker=actor()['id'],reviewer=None,status='pending',reason=None,created=host().now(),reviewed=None)
   c.execute(APPROVALS.insert().values(**item));append(c,'import_review_requested',identifier,dict(approval_id=aid))
   return item
 @app.get('/api/v1/enterprise/approvals')
 def approvals():
  initialize(host().current_db())
  with host().current_db().connect() as c:return [dict(r) for r in c.execute(select(APPROVALS).order_by(APPROVALS.c.created.desc()).limit(100)).mappings()]
 @app.post('/api/v1/enterprise/approvals/{identifier}/review')
 def review(identifier:str,body:Review):
  if not actor() or actor()['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要已认证管理员复核')
  if body.decision not in ('approved','rejected'):raise ValueError('决策须approved或rejected')
  database=host().current_db();initialize(database)
  with LOCK,database.begin() as c:
   old=c.execute(select(APPROVALS).where(APPROVALS.c.id==identifier)).mappings().first()
   if not old:raise HTTPException(404,'复核记录不存在')
   if old['maker']==actor()['id']:raise HTTPException(403,'制单人与复核人必须不同')
   if old['status']!='pending':raise HTTPException(409,'已处理复核不能覆盖')
   from erp_imports import get
   value=get(old['run_id'])
   if value.get('cleaning_token')!=old['cleaning_token'] or value.get('cleaned_by')!=old['maker'] or snapshot_hash(value)!=old['snapshot_hash']:raise HTTPException(409,'清洗结果已变化，须重新发起')
   update=dict(reviewer=actor()['id'],status=body.decision,reason=body.reason,reviewed=host().now())
   if c.execute(APPROVALS.update().where(APPROVALS.c.id==identifier,APPROVALS.c.status=='pending').values(**update)).rowcount!=1:raise HTTPException(409,'复核并发处理')
   append(c,'import_'+body.decision,old['run_id'],dict(approval_id=identifier,reason=body.reason,maker=old['maker']))
   return dict(old)|update
 @app.get('/api/v1/enterprise/audit/verify')
 def audit_verify():return verify(host().current_db())
 @app.get('/api/v1/enterprise/audit')
 def events():
  initialize(host().current_db())
  with host().current_db().connect() as c:return [dict(sequence=r['sequence'],event=json.loads(r['payload']),previous_hash=r['previous_hash'],event_hash=r['event_hash']) for r in c.execute(select(EVENTS).order_by(EVENTS.c.sequence.desc()).limit(100)).mappings()]
