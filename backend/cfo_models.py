import json,hashlib
from decimal import Decimal,InvalidOperation
from typing import Literal
from sqlalchemy import MetaData,Table,Column,String,Text,select
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
import app as core
import enterprise_controls as controls
from cfo_briefings import shift
meta=MetaData();inputs=Table('metadata_cfo_approved_input',meta,Column('id',String,primary_key=True),Column('organization',String),Column('maker',String),Column('reviewer',String),Column('status',String),Column('payload',Text),Column('hash',String));calculations=Table('metadata_cfo_calculation',meta,Column('id',String,primary_key=True),Column('organization',String),Column('payload',Text))
FIELDS=set('revenue net_profit equity_open equity_close current_assets current_liabilities inventory_close liabilities assets receivables_open receivables_close inventory_open cost credit_sales operating_cash_flow capex expense'.split())
def dec(x):
 if not isinstance(x,str):raise ValueError('金额必须是十进制字符串')
 try:d=Decimal(x)
 except InvalidOperation:raise ValueError('金额无效') from None
 if not d.is_finite() or abs(d)>Decimal('999999999999999999.99') or d!=d.quantize(Decimal('.01')):raise ValueError('金额精度或范围无效')
 return d
def scope():
 db=core.current_db();meta.create_all(db);controls.initialize(db);return db,core.request_organization.get()
def actor():
 u=core.request_actor.get()
 if not u or u['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要已认证管理员')
 return u
class Input(BaseModel):
 model_config=ConfigDict(extra='forbid')
 period:str
 currency:str='CNY'
 source_reference:str=Field(min_length=1,max_length=300)
 version:str=Field(min_length=1,max_length=80)
 data_kind:str='uploaded'
 values:dict[str,str]
class Approval(BaseModel):
 model_config=ConfigDict(extra='forbid')
 reason:str=Field(default='independent review',min_length=3,max_length=300)
class Scenario(BaseModel):
 model_config=ConfigDict(extra='forbid')
 revenue_change:str='0'
 cost_change:str='0'
 expense_change:str='0'
class Backtest(BaseModel):
 metric:Literal['revenue','expense','operating_cashflow']='revenue'
 model_config=ConfigDict(extra='forbid')
 start_period:str
 end_period:str
 currency:str='CNY'
 window:int=Field(default=3,ge=2,le=12)
def fetch(jid):
 db,org=scope()
 with db.connect() as c:r=c.execute(select(inputs).where(inputs.c.id==jid,inputs.c.organization==org)).mappings().first()
 if not r:raise HTTPException(404,'输入不存在')
 if r['status']!='approved':raise HTTPException(409,'输入尚未独立核准')
 p=json.loads(r['payload'])
 if hashlib.sha256(controls.canonical(p).encode()).hexdigest()!=r['hash']:raise HTTPException(409,'快照变化')
 return p
def save(value):
 db,org=scope();value=dict(value,id=core.uid(),algorithm_version='cfo-decimal-1.0')
 with db.begin() as c:c.execute(calculations.insert().values(id=value['id'],organization=org,payload=json.dumps(value)))
 return value
def ratios(p):
 v={k:dec(x) for k,x in p['values'].items()};out={}
 formulas={'net_margin':(['net_profit','revenue'],lambda: v['net_profit']/v['revenue']),'roe':(['net_profit','equity_open','equity_close'],lambda:v['net_profit']/((v['equity_open']+v['equity_close'])/2)),'current_ratio':(['current_assets','current_liabilities'],lambda:v['current_assets']/v['current_liabilities']),'quick_ratio':(['current_assets','inventory_close','current_liabilities'],lambda:(v['current_assets']-v['inventory_close'])/v['current_liabilities']),'debt_ratio':(['liabilities','assets'],lambda:v['liabilities']/v['assets']),'receivable_turnover':(['credit_sales','receivables_open','receivables_close'],lambda:v['credit_sales']/((v['receivables_open']+v['receivables_close'])/2)),'inventory_turnover':(['cost','inventory_open','inventory_close'],lambda:v['cost']/((v['inventory_open']+v['inventory_close'])/2)),'free_cash_flow':(['operating_cash_flow','capex'],lambda:v['operating_cash_flow']-v['capex'])}
 for key,(required,fn) in formulas.items():
  missing=sorted(set(required)-v.keys())
  try:out[key]={'value':str(fn()) if not missing else None,'reason':'missing:'+','.join(missing) if missing else None}
  except (ZeroDivisionError,InvalidOperation):out[key]={'value':None,'reason':'zero_denominator'}
 return out

def install(app):
 @app.post('/api/v1/cfo/inputs',status_code=201)
 def create(body:Input):
  u=actor();core.finance(body.period,body.period,body.currency)
  if body.data_kind not in ('simulated','uploaded'):raise HTTPException(422,'来源类型无效')
  if set(body.values)-FIELDS:raise HTTPException(422,'未知字段')
  for v in body.values.values():dec(v)
  p=body.model_dump();db,org=scope();jid=core.uid()
  with controls.LOCK,db.begin() as c:
   controls.assert_open(c,[body.period]);c.execute(inputs.insert().values(id=jid,organization=org,maker=u['id'],status='pending',payload=controls.canonical(p),hash=hashlib.sha256(controls.canonical(p).encode()).hexdigest()));controls.append(c,'cfo_input_created',jid)
  return {'id':jid,'status':'pending'}
 @app.post('/api/v1/cfo/inputs/{jid}/approve')
 def approve(jid:str,body:Approval=Approval()):
  u=actor();db,org=scope()
  with controls.LOCK,db.begin() as c:
   r=c.execute(select(inputs).where(inputs.c.id==jid,inputs.c.organization==org)).mappings().first()
   if not r:raise HTTPException(404,'输入不存在')
   if r['maker']==u['id']:raise HTTPException(403,'禁止自审')
   controls.assert_open(c,[json.loads(r['payload'])['period']])
   if hashlib.sha256(r['payload'].encode()).hexdigest()!=r['hash']:raise HTTPException(409,'原始快照变化')
   if c.execute(inputs.update().where(inputs.c.id==jid,inputs.c.status=='pending').values(status='approved',reviewer=u['id'])).rowcount!=1:raise HTTPException(409,'已处理')
   controls.append(c,'cfo_input_approved',jid,{'reason':body.reason,'source_hash':r['hash']})
  return {'id':jid,'status':'approved'}
 @app.get('/api/v1/cfo/inputs/{jid}/ratios')
 def calculate(jid:str):
  p=fetch(jid);return {'source_id':jid,'source':p,'ratios':ratios(p),'algorithm_version':'cfo-decimal-1.0','units':'ratios as fractions; turnover times per supplied period; FCF source currency','basis':'quick ratio=(current assets-inventory)/current liabilities, simplified; ROE/turnover not annualized'}
 @app.post('/api/v1/cfo/inputs/{jid}/scenario')
 def scenario(jid:str,body:Scenario):
  p=fetch(jid);v=p['values'];required={'revenue','cost','expense'}
  if not required<=v.keys():return save({'source_id':jid,'value':None,'reason':'missing_revenue_cost_expense'})
  factors=[dec(x) for x in (body.revenue_change,body.cost_change,body.expense_change)]
  if any(x< -1 or x>10 for x in factors):raise HTTPException(422,'变化率范围-1到10')
  adjusted={k:format((dec(v[k])*(1+x)).quantize(Decimal('.01')),'.2f') for k,x in zip(('revenue','cost','expense'),factors)}
  return save({'source_id':jid,'source':p,'parameters':body.model_dump(),'adjusted':adjusted,'operating_profit':str(dec(adjusted['revenue'])-dec(adjusted['cost'])-dec(adjusted['expense'])),'basis':'operating only; taxes not inferred'})
 @app.post('/api/v1/cfo/backtests')
 def backtest(body:Backtest):
  core.metrics(core.current_db(),body.start_period,body.end_period,body.currency)
  if body.metric=='operating_cashflow':
   db,org=scope();data=[];seen=set()
   with db.connect() as c:approved=list(c.execute(select(inputs).where(inputs.c.organization==org,inputs.c.status=='approved')).mappings())
   for r in approved:
    p=json.loads(r['payload'])
    if p['currency']!=body.currency or not body.start_period<=p['period']<=body.end_period or 'operating_cash_flow' not in p['values']:continue
    if hashlib.sha256(controls.canonical(p).encode()).hexdigest()!=r['hash']:raise HTTPException(409,'核准现金流快照变化')
    if p['period'] in seen:raise HTTPException(409,'同月多份核准现金流，需显式消歧版本')
    seen.add(p['period']);value=dec(p['values']['operating_cash_flow'])
    data.append({'period':p['period'],'operating_cashflow':str(value),'source_id':r['id'],'source_hash':r['hash'],'source_reference':p['source_reference'],'version':p['version'],'data_kind':p.get('data_kind','unspecified'),'currency':body.currency})
   data.sort(key=lambda x:x['period'])
  else:data=core.finance(body.start_period,body.end_period,body.currency)
  expected=[];period=body.start_period
  while period<=body.end_period:
   expected.append(period)
   if period==body.end_period:break
   period=shift(period,1)
  if [x['period'] for x in data]!=expected:raise HTTPException(422,'请求区间历史缺月，包括起止月')
  if len(data)<=body.window:raise HTTPException(422,'历史样本不足')
  predictions=[]
  for i in range(body.window,len(data)):
   forecast=sum((Decimal(x[body.metric]) for x in data[i-body.window:i]),Decimal(0))/body.window;actual=Decimal(data[i][body.metric]);predictions.append({'period':data[i]['period'],'training_periods':[x['period'] for x in data[i-body.window:i]],'forecast':str(forecast),'actual':str(actual),'absolute_error':str(abs(forecast-actual)),'naive_forecast':data[i-1][body.metric],'naive_absolute_error':str(abs(Decimal(data[i-1][body.metric])-actual))})
  return save({'parameters':body.model_dump(),'sources':data,'predictions':predictions,'mae':str(sum((Decimal(x['absolute_error']) for x in predictions),Decimal(0))/len(predictions)),'method':'baseline_rolling_mean_one_step_'+body.metric,'naive_mae':str(sum((Decimal(x['naive_absolute_error']) for x in predictions),Decimal(0))/len(predictions)),'training':'no trained model; naive=last month','forecast_next':str(sum((Decimal(x[body.metric]) for x in data[-body.window:]),Decimal(0))/body.window)})
