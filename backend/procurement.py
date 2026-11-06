"""Evidence-only five-document procurement matching; no payment capability."""
import json,hashlib,re
from datetime import date
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import MetaData,Table,Column,String,Text,select
from sqlalchemy.exc import IntegrityError
import app as core
import enterprise_controls as controls
from finance_risk_engine import money
KINDS={'contract','purchase_order','receipt','invoice','payment'}
VERSION='five-document-exact-1.0'
meta=MetaData();table=Table('metadata_procurement_evidence',meta,Column('id',String,primary_key=True),Column('organization',String),Column('case_id',String),Column('currency',String),Column('kind',String),Column('payload',Text),Column('sha256',String),Column('maker',String))
class Evidence(BaseModel):
 model_config=ConfigDict(extra='forbid')
 case_id:str=Field(min_length=1,max_length=100)
 kind:str
 external_id:str=Field(min_length=1,max_length=100)
 version:str=Field(min_length=1,max_length=50)
 date:str
 currency:str='CNY'
 amount:str
 supplier:str=Field(min_length=1,max_length=100)
 quantity:str
 source_reference:str=Field(min_length=1,max_length=300)
 data_kind:str
 workbench_document_id:str|None=None

def scope():
 db=core.current_db();meta.create_all(db);controls.initialize(db);return db,core.request_organization.get()
def register(body):
 who=core.request_actor.get()
 if not who or who['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要管理员证据登记权限')
 p=body.model_dump();date.fromisoformat(p['date'])
 if body.kind not in KINDS or body.data_kind not in ('simulated','uploaded') or not re.fullmatch('[A-Z]{3}',body.currency):raise HTTPException(422,'证据类型或币种无效')
 amount=money(body.amount)
 if amount<0:raise HTTPException(422,'金额不得为负')
 try:q=Decimal(body.quantity)
 except InvalidOperation:raise HTTPException(422,'数量无效') from None
 if not q.is_finite() or q<=0 or q>Decimal('999999999999') or q!=q.quantize(Decimal('.000001')):raise HTTPException(422,'数量范围或精度无效')
 p['amount']=format(amount,'.2f');p['quantity']=format(q,'f')
 if body.workbench_document_id:
  from finance_workbench import item
  r=item(body.workbench_document_id);v=json.loads(r['payload'])
  if body.kind!='invoice' or v['kind']!='invoice' or v['currency']!=body.currency or money(v['amount'])!=amount or v['supplier']!=body.supplier or v['data_kind']!=body.data_kind:raise HTTPException(409,'工作台发票证据不一致')
 db,org=scope();raw=controls.canonical(p);sha=hashlib.sha256(raw.encode()).hexdigest();key=hashlib.sha256(controls.canonical([org,body.case_id,body.currency,body.kind]).encode()).hexdigest()
 try:
  with controls.LOCK,db.begin() as c:
   old=c.execute(select(table).where(table.c.id==key,table.c.organization==org)).mappings().first()
   if old:
    if old['sha256']!=sha:raise HTTPException(409,'证据槽已有不同版本，请建立新case')
    return {'id':key,'sha256':sha,'status':'already_registered'}
   controls.assert_open(c,[body.date[:7]]);c.execute(table.insert().values(id=key,organization=org,case_id=body.case_id,currency=body.currency,kind=body.kind,payload=raw,sha256=sha,maker=who['id']));controls.append(c,'procurement_evidence_registered',key,{'kind':body.kind,'sha256':sha})
 except IntegrityError:raise HTTPException(409,'并发证据冲突，请重试') from None
 return {'id':key,'sha256':sha,'status':'registered'}
def match(case_id,currency):
 if not re.fullmatch('[A-Z]{3}',currency):raise HTTPException(422,'币种无效')
 db,org=scope()
 with db.connect() as c:rs=c.execute(select(table).where(table.c.organization==org,table.c.case_id==case_id,table.c.currency==currency)).mappings().all()
 if not rs:raise HTTPException(404,'本组织币种下case不存在')
 evidence={};issues=[]
 for r in rs:
  if hashlib.sha256(r['payload'].encode()).hexdigest()!=r['sha256']:raise HTTPException(409,'原始证据变化')
  evidence[r['kind']]={'id':r['id'],'sha256':r['sha256'],'maker':r['maker'],'source':json.loads(r['payload'])}
 missing=sorted(KINDS-evidence.keys())
 for field in ('amount','quantity','supplier'):
  values={Decimal(e['source'][field]) if field in ('amount','quantity') else e['source'][field] for e in evidence.values()}
  if len(values)>1:issues.append({'field':field,'code':'mismatch','evidence_ids':sorted(e['id'] for e in evidence.values())})
 return {'case_id':case_id,'currency':currency,'status':'quarantined' if missing or issues else 'matched','missing':missing,'differences':issues,'evidence':evidence,'rule_version':VERSION,'basis':'exact whole-document totals; no partial delivery, tax or exchange tolerances; no payment/posting/approval action'}
def install(app):
 @app.post('/api/v1/finance-workbench/procurement/evidence',status_code=201)
 def create(body:Evidence):return register(body)
 @app.get('/api/v1/finance-workbench/procurement/{case_id}/match')
 def review(case_id:str,currency:str='CNY'):return match(case_id,currency)
