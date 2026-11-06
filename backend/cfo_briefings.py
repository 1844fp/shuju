"""Deterministic CFO snapshot and durable idempotent daily briefing ticks."""
import json
from datetime import date
from decimal import Decimal
from sqlalchemy import MetaData,Table,Column,String,Text,select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
import app as core
meta=MetaData()
schedules=Table('metadata_briefing_schedule',meta,Column('id',String,primary_key=True),Column('organization',String),Column('payload',Text))
briefs=Table('metadata_daily_briefing',meta,Column('id',String,primary_key=True),Column('organization',String),Column('payload',Text))
def shift(p,n):
 y,m=map(int,p.split('-'));v=y*12+m-1+n;return f'{v//12:04d}-{v%12+1:02d}'
def overview(period,currency):
 current=core.finance(period,period,currency);previous=core.finance(shift(period,-1),shift(period,-1),currency);year=core.finance(shift(period,-12),shift(period,-12),currency)
 changes={}
 for label,prior in [('mom',previous),('yoy',year)]:
  changes[label]={}
  for k in ('revenue','cost','expense','operating_profit'):
   a=Decimal(current[0][k]) if current else None;b=Decimal(prior[0][k]) if prior else None
   changes[label][k]={'value':str((a-b)/abs(b)) if a is not None and b else None,'reason':None if a is not None and b else 'missing_period_or_zero_denominator'}
 totals={};sources={}
 with core.current_db().connect() as c:
  for r in c.execute(select(core.facts).where(core.facts.c.period==period,core.facts.c.currency==currency,core.facts.c.category=='expense')).mappings():
   department=json.loads(r['payload']).get('department_code','');totals[department]=totals.get(department,0)+r['debit_cents']-r['credit_cents'];sources.setdefault(department,set()).add(r['batch_id'])
 result={'period':period,'currency':currency,'metrics':current,'changes':changes,'department_top5':[{'department':k,'expense':core.money(v),'batch_ids':sorted(sources[k])} for k,v in sorted(totals.items(),key=lambda x:(-x[1],x[0]))[:5]],'unavailable':{k:'missing_complete_balance_tax_average_or_capex_inputs' for k in ('net_profit','net_margin','roe','current_ratio','quick_ratio','debt_ratio','receivable_turnover','inventory_turnover','free_cash_flow')},'metric_version':'1.0'}
 # Existing balance model explicitly labels completeness unverified. Return
 # a scoped observed ratio, never imply an audited complete balance sheet.
 from financial_statements import balance
 import calendar
 as_of=period+'-'+str(calendar.monthrange(*map(int,period.split('-')))[1])
 try:
  snapshot=balance(as_of,currency);assets=Decimal(snapshot['assets']);liabilities=Decimal(snapshot['liabilities'])
  result['balance_evidence']=snapshot
  result['ratios']={'debt_ratio':{'value':str(liabilities/assets) if assets else None,'reason':None if assets else 'zero_assets','scope':'provided_opening_and_mapped_journal','completeness':snapshot['completeness']}}
  result['unavailable'].pop('debt_ratio',None)
 except HTTPException as ex:
  if ex.status_code!=422:raise
  result['ratios']={'debt_ratio':{'value':None,'reason':'missing_balanced_opening_or_mapping'}}
 return result

class Schedule(BaseModel):
 model_config=ConfigDict(extra='forbid')
 id:str=Field(min_length=1,max_length=80)
 currency:str='CNY'
 hour:int=Field(default=9,ge=0,le=23)
class Tick(BaseModel):
 model_config=ConfigDict(extra='forbid')
 date:str
def scope():
 db=core.current_db();meta.create_all(db);return db,core.request_organization.get()
def install(app):
 @app.get('/api/v1/cfo/overview')
 def cfo(period:str='2026-11',currency:str='CNY'):return overview(period,currency)
 @app.get('/api/v1/briefing-schedules')
 def listing():
  db,org=scope()
  with db.connect() as c:return [json.loads(x) for x in c.execute(select(schedules.c.payload).where(schedules.c.organization==org)).scalars()]
 @app.post('/api/v1/briefing-schedules',status_code=201)
 def create(body:Schedule):
  core.finance('2026-01','2026-01',body.currency);db,org=scope();key=org+'|'+body.id;p=body.model_dump()
  with db.begin() as c:
   old=c.execute(select(schedules.c.payload).where(schedules.c.id==key,schedules.c.organization==org)).scalar()
   if old:
    if json.loads(old)!=p:raise HTTPException(409,'调度编号内容冲突')
    return p
   c.execute(schedules.insert().values(id=key,organization=org,payload=json.dumps(p)))
  return p
 @app.post('/api/v1/briefing-schedules/{sid}/tick')
 def tick(sid:str,body:Tick):
  day=date.fromisoformat(body.date);db,org=scope();key=org+'|'+sid+'|'+body.date
  with db.connect() as c:
   s=c.execute(select(schedules.c.payload).where(schedules.c.id==org+'|'+sid,schedules.c.organization==org)).scalar();old=c.execute(select(briefs.c.payload).where(briefs.c.id==key,briefs.c.organization==org)).scalar()
  if not s:raise HTTPException(404,'调度不存在')
  if old:return json.loads(old)
  p={'id':key,'date':body.date,'status':'completed','notification':'not_configured','snapshot':overview(body.date[:7],json.loads(s)['currency'])}
  try:
   with db.begin() as c:c.execute(briefs.insert().values(id=key,organization=org,payload=json.dumps(p)))
  except IntegrityError:
   with db.connect() as c:return json.loads(c.execute(select(briefs.c.payload).where(briefs.c.id==key)).scalar_one())
  return p
