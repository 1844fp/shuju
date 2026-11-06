import json, hashlib
import enterprise_controls as controls
from sqlalchemy.exc import IntegrityError
from datetime import date
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import inspect,text
from sqlalchemy import Table,Column,String,Text,MetaData,select
import app as core
from finance_risk_engine import money,evaluate
meta=MetaData()
t=Table('metadata_workbench_document',meta,Column('id',String,primary_key=True),Column('organization',String),Column('maker',String),Column('status',String),Column('payload',Text),Column('review',Text),Column('draft',Text),Column('external_id',String,unique=True),Column('snapshot_hash',String))
class Document(BaseModel):
 model_config=ConfigDict(extra='forbid')
 external_id:str
 kind:str
 date:str
 currency:str='CNY'
 amount:str
 invoice:str=''
 employee:str=''
 supplier:str=''
 department:str=''
 data_kind:str='uploaded'
class Review(BaseModel):
 model_config=ConfigDict(extra='forbid')
 decision:str
 reason:str

def scope():
 db=core.current_db();meta.create_all(db)
 with controls.LOCK,db.begin() as c:
  columns={x['name'] for x in inspect(c).get_columns(t.name)}
  for name in ('external_id','snapshot_hash'):
   if name not in columns:c.execute(text('ALTER TABLE metadata_workbench_document ADD COLUMN '+name+' VARCHAR'))
  for r in c.execute(select(t)).mappings().all():
   if not r['snapshot_hash']:
    digest=hashlib.sha256(r['payload'].encode()).hexdigest()
    c.execute(t.update().where(t.c.id==r['id']).values(snapshot_hash=digest,external_id='legacy-'+r['id']))
  c.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS workbench_external_unique ON metadata_workbench_document(external_id)'))
 controls.initialize(db);return db,core.request_organization.get()
def rows():
 db,org=scope()
 with db.connect() as c:return [dict(r) for r in c.execute(select(t).where(t.c.organization==org)).mappings()]
def item(jid):
 for r in rows():
  if r['id']==jid:return r
 raise HTTPException(404,'记录不存在')
def actor(request):
 u=getattr(request.state,'identity',None)
 if not u:raise HTTPException(401,'需要用户会话')
 return u

def install(app):
 @app.get('/api/v1/finance-workbench/documents')
 def listing():return [{**r,'payload':json.loads(r['payload'])} for r in rows()]
 @app.post('/api/v1/finance-workbench/documents',status_code=201)
 def create(body:Document,request:Request):
  u=actor(request);p=body.model_dump();date.fromisoformat(p['date'])
  if p['kind'] not in ('invoice','expense') or p['data_kind'] not in ('simulated','uploaded') or money(p['amount'])<=0 or len(p['currency'])!=3 or not p['currency'].isupper():raise HTTPException(422,'输入无效')
  if not body.external_id.strip() or len(body.external_id)>100:raise HTTPException(422,'外部编号无效')
  p['amount']=format(money(p['amount']),'.2f');db,org=scope();jid=core.uid()
  encoded=controls.canonical(p);digest=hashlib.sha256(encoded.encode()).hexdigest();external=hashlib.sha256((org+'|'+body.external_id).encode()).hexdigest()
  try:
   with controls.LOCK,db.begin() as c:
    old=c.execute(select(t).where(t.c.external_id==external,t.c.organization==org)).mappings().first()
    if old:
     if old['snapshot_hash']!=digest:raise HTTPException(409,'外部编号内容冲突')
     return dict(old)
    controls.assert_open(c,[p['date'][:7]])
    c.execute(t.insert().values(id=jid,organization=org,maker=u['id'],status='pending',payload=encoded,external_id=external,snapshot_hash=digest))
    controls.append(c,'workbench_created',jid,dict(snapshot_hash=digest))
  except IntegrityError:raise HTTPException(409,'外部编号并发冲突，请重试') from None
  return item(jid)
 @app.get('/api/v1/finance-workbench/risks')
 def risks(currency:str='CNY',start_period:str='2000-01',end_period:str='2099-12'):
  from risk_adapters import review
  core.metrics(core.current_db(),start_period,end_period,currency)
  return review(start_period,end_period,currency)
 @app.post('/api/v1/finance-workbench/documents/{jid}/review')
 def review(jid:str,body:Review,request:Request):
  u=actor(request);r=item(jid)
  if u['role'] not in ('org_admin','platform_admin') or r['maker']==u['id']:raise HTTPException(403,'需要独立审批人')
  if body.decision not in ('approved','rejected') or not body.reason.strip():raise HTTPException(422,'审批参数无效')
  db,org=scope()
  with controls.LOCK,db.begin() as c:
   controls.assert_open(c,[json.loads(r['payload'])['date'][:7]])
   if hashlib.sha256(r['payload'].encode()).hexdigest()!=r['snapshot_hash']:raise HTTPException(409,'原始快照已变化')
   n=c.execute(t.update().where(t.c.id==jid,t.c.organization==org,t.c.status=='pending').values(status=body.decision,review=json.dumps(dict(body.model_dump(),reviewer=u['id'])))).rowcount
   if not n:raise HTTPException(409,'状态已改变')
   controls.append(c,'workbench_'+body.decision,jid,dict(snapshot_hash=r['snapshot_hash'],reason=body.reason))
  return item(jid)
 @app.post('/api/v1/finance-workbench/documents/{jid}/voucher-draft')
 def draft(jid:str,request:Request):
  actor(request);r=item(jid);p=json.loads(r['payload']);db,org=scope()
  v={'status':'draft_only','source_id':jid,'currency':p['currency'],'data_kind':p['data_kind'],'lines':[{'account':'expense_pending_mapping','debit':p['amount'],'credit':'0.00'},{'account':'payable_pending_mapping','debit':'0.00','credit':p['amount']}]}
  with controls.LOCK,db.begin() as c:
   controls.assert_open(c,[p['date'][:7]])
   if hashlib.sha256(r['payload'].encode()).hexdigest()!=r['snapshot_hash']:raise HTTPException(409,'原始快照已变化')
   n=c.execute(t.update().where(t.c.id==jid,t.c.organization==org,t.c.status=='approved').values(status='drafted',draft=json.dumps(v))).rowcount
   if not n:raise HTTPException(409,'仅已批准记录可生成草稿')
   controls.append(c,'workbench_voucher_drafted',jid,dict(snapshot_hash=r['snapshot_hash']))
  return v


 @app.post('/api/v1/finance-workbench/documents/{jid}/publish')
 def publish(jid:str,body:dict,request:Request):
  u=actor(request)
  if u['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要管理员')
  if set(body)!={'batch_id'}:raise HTTPException(422,'仅接受batch_id')
  import warehouse
  r=item(jid);org=core.request_organization.get();raw=r['payload'].encode();digest=hashlib.sha256(raw).hexdigest()
  if digest!=r['snapshot_hash']:raise HTTPException(409,'快照已变化')
  p=json.loads(r['payload'])
  with warehouse.connection() as c:
   if not c.execute('SELECT id FROM metadata.data_batch WHERE organization_id=%s AND id=%s',(org,body['batch_id'])).fetchone():raise HTTPException(404,'同组织发布批次不存在')
   c.execute('INSERT INTO ods.workbench_evidence(organization_id,batch_id,document_id,document_kind,source_sha256,original_content,original_payload,validation_status,quality_errors,schema_version) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s) ON CONFLICT DO NOTHING',(org,body['batch_id'],jid,'invoice' if p['kind']=='invoice' else 'reimbursement',digest,raw,r['payload'],'quarantined' if r['status']=='rejected' else 'accepted',json.dumps(['human_rejected'] if r['status']=='rejected' else []),'workbench-v1'))
  return {'status':'published','document_id':jid,'source_sha256':digest,'organization_id':org}
