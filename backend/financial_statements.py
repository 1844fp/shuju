"""Explicit accounting mappings, opening balances and sales analytical records."""
import json
from datetime import date
from decimal import Decimal,InvalidOperation
from collections import defaultdict
from fastapi import HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import MetaData,Table,Column,String,Text,select
import app as core
meta=MetaData();items=Table('finance_statement_input',meta,Column('id',String,primary_key=True),Column('kind',String),Column('payload',Text))
MAP={'1002':('asset','asset'),'1122':('asset','asset'),'1405':('asset','asset'),'1601':('asset','asset'),'2001':('liability','liability'),'2202':('liability','liability'),'4001':('equity','equity'),'4103':('equity','equity'),'6001':('revenue','revenue'),'6051':('revenue','revenue'),'6401':('cost','cost'),'6601':('expense','selling_expense'),'6602':('expense','administrative_expense'),'6603':('expense','finance_expense'),'6111':('other','investment_gain'),'6301':('other','nonoperating_income'),'6711':('other','nonoperating_expense'),'6801':('other','income_tax')}
core.ACCOUNTS.update({k:v[0] for k,v in MAP.items()})
def records(kind):
 meta.create_all(core.current_db())
 with core.current_db().connect() as c:return [json.loads(x) for x in c.execute(select(items.c.payload).where(items.c.kind==kind)).scalars()]
def store(kind,key,value):
 meta.create_all(core.current_db())
 with core.current_db().begin() as c:
  old=c.execute(select(items.c.payload).where(items.c.id==key)).scalar()
  if old:
   if json.loads(old)!=value:raise HTTPException(409,'相同业务编号已有不同内容')
   return value
  c.execute(items.insert().values(id=key,kind=kind,payload=json.dumps(value,ensure_ascii=False)))
 return value
class Opening(BaseModel):
 account_code:str
 as_of:date
 currency:str='CNY'
 debit:str='0'
 credit:str='0'
 source_reference:str=Field(min_length=1,max_length=160)
 data_kind:str='uploaded'
class Sale(BaseModel):
 external_id:str=Field(min_length=1,max_length=80)
 posting_date:date
 customer:str=Field(min_length=1,max_length=100)
 product:str=Field(min_length=1,max_length=100)
 amount:str
 currency:str='CNY'
 direction:str='sale'
 data_kind:str='uploaded'
def valid_currency(c):
 from agents.runtime import Query
 Query(currency=c)
def journal(start,end,currency):
 with core.current_db().connect() as c:entries=c.execute(select(core.facts).where(core.facts.c.period>=start[:7],core.facts.c.period<=end[:7],core.facts.c.currency==currency)).mappings().all()
 return [(f,json.loads(f['payload'])) for f in entries if start<=json.loads(f['payload'])['posting_date']<=end]
def kinds_for_batches(ids):
 with core.current_db().connect() as c:return sorted(set(c.execute(select(core.batches.c.kind).where(core.batches.c.id.in_(ids))).scalars())) if ids else []
def income(start,end,currency):
 date.fromisoformat(start);date.fromisoformat(end);valid_currency(currency)
 if start>end:raise ValueError('开始日期晚于结束日期')
 values=defaultdict(int);sources=set()
 for f,p in journal(start,end,currency):
  _,line=MAP[p['account_code']];signed=f['credit_cents']-f['debit_cents'] if line in ('revenue','investment_gain','nonoperating_income') else f['debit_cents']-f['credit_cents'];values[line]+=signed;sources.add(f['batch_id'])
 gross=values['revenue']-values['cost'];operating=gross-sum(values[x] for x in ('selling_expense','administrative_expense','finance_expense'))+values['investment_gain'];pretax=operating+values['nonoperating_income']-values['nonoperating_expense']
 return {'currency':currency,'start_date':start,'end_date':end,'lines':{k:core.money(values[k]) for k in ('revenue','cost','selling_expense','administrative_expense','finance_expense','investment_gain','nonoperating_income','nonoperating_expense','income_tax')},'gross_profit':core.money(gross),'operating_profit':core.money(operating),'profit_before_tax':core.money(pretax),'net_profit':core.money(pretax-values['income_tax']),'batch_ids':sorted(sources),'data_kind':kinds_for_batches(sources),'metric_version':'statement-1.0','basis':'显式科目映射的简化利润表；未列项目不自动推定已完整，需财务人员核对范围','completeness':'unverified'}
def balance(as_of,currency):
 date.fromisoformat(as_of);valid_currency(currency);opening=[x for x in records('opening') if x['currency']==currency]
 if not opening:raise HTTPException(422,'须先提供完整且平衡的期初余额，不能仅凭期间流水宣称资产负债表完整')
 start=opening[0]['as_of']
 if as_of<start:raise ValueError('查询日早于期初日')
 balances={x['account_code']:core.cents(x['debit'])-core.cents(x['credit']) for x in opening};opening_sum=sum(balances.values())
 if opening_sum:raise HTTPException(422,'期初余额借贷不平衡')
 sources=set();period_pnl=0
 for f,p in journal(start,as_of,currency):
  category,_=MAP[p['account_code']];delta=f['debit_cents']-f['credit_cents'];sources.add(f['batch_id'])
  if category in ('asset','liability','equity'):balances[p['account_code']]=balances.get(p['account_code'],0)+delta
  else:period_pnl-=delta
 assets=sum(v for k,v in balances.items() if MAP[k][0]=='asset');liabilities=-sum(v for k,v in balances.items() if MAP[k][0]=='liability');equity=-sum(v for k,v in balances.items() if MAP[k][0]=='equity')+period_pnl
 return {'as_of':as_of,'currency':currency,'assets':core.money(assets),'liabilities':core.money(liabilities),'equity_including_current_result':core.money(equity),'current_result':core.money(period_pnl),'balanced':assets==liabilities+equity,'difference':core.money(assets-liabilities-equity),'opening_data_kind':sorted({x['data_kind'] for x in opening}),'opening_sources':[x['source_reference'] for x in opening],'batch_ids':sorted(sources),'data_kind':kinds_for_batches(sources),'metric_version':'statement-1.0','basis':'期初日开始前余额+截至查询日分录；简化显式科目映射，非审计报告','completeness':'unverified'}
def install(app):
 @app.post('/api/v1/finance/opening-balances',status_code=201)
 def add_opening(body:Opening):
  valid_currency(body.currency)
  if body.account_code not in MAP or MAP[body.account_code][0] not in ('asset','liability','equity'):raise ValueError('期初余额仅支持明确映射的资产负债权益科目')
  d,c=core.cents(body.debit),core.cents(body.credit)
  if d and c:raise ValueError('期初余额不能借贷同时非零')
  if body.data_kind not in ('uploaded','simulated'):raise ValueError('来源标记无效')
  old=[x for x in records('opening') if x['currency']==body.currency]
  if old and any(x['as_of']!=body.as_of.isoformat() for x in old):raise HTTPException(409,'同币种期初日期必须一致')
  value=body.model_dump(mode='json');value.update(debit=core.money(d),credit=core.money(c));return store('opening','opening:'+body.currency+':'+body.account_code,value)
 @app.get('/api/v1/finance/statements/income')
 def profit(start_date:str,end_date:str,currency:str='CNY'):return income(start_date,end_date,currency)
 @app.get('/api/v1/finance/statements/balance')
 def sheet(as_of:str,currency:str='CNY'):return balance(as_of,currency)
 @app.post('/api/v1/sales',status_code=201)
 def add_sale(body:Sale):
  valid_currency(body.currency);amount=core.cents(body.amount)
  if body.direction not in ('sale','refund') or body.data_kind not in ('uploaded','simulated'):raise ValueError('销售方向或来源无效')
  value=body.model_dump(mode='json');value['amount']=core.money(amount);return store('sale','sale:'+body.external_id,value)
 @app.get('/api/v1/sales/summary')
 def sales(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'):
  from agents.runtime import Query
  Query(start_period=start_period,end_period=end_period,currency=currency);group=defaultdict(lambda:{'amount':0,'ids':[],'kinds':set()})
  for x in records('sale'):
   if x['currency']==currency and start_period<=x['posting_date'][:7]<=end_period:
    g=group[(x['posting_date'][:7],x['customer'])];g['amount']+=core.cents(x['amount'])*(1 if x['direction']=='sale' else -1);g['ids'].append(x['external_id']);g['kinds'].add(x['data_kind'])
  return {'rows':[{'period':p,'customer':c,'currency':currency,'net_sales':core.money(v['amount']),'source_ids':v['ids'],'data_kind':sorted(v['kinds'])} for (p,c),v in sorted(group.items())],'basis':'销售登记口径，不自动等同会计确认收入','metric_version':'sales-1.0'}
class BankReconciliation(BaseModel):
 external_id:str=Field(min_length=1,max_length=80)
 as_of:date
 currency:str='CNY'
 bank_closing:str
 book_closing:str
 deposits_in_transit:str='0'
 outstanding_payments:str='0'
 bank_credits_not_booked:str='0'
 bank_debits_not_booked:str='0'
 source_reference:str=Field(min_length=1,max_length=160)
 data_kind:str='uploaded'
def install_bank_worksheet(app):
 @app.post('/api/v1/finance/bank-balance-reconciliation')
 def worksheet(body:BankReconciliation):
  valid_currency(body.currency)
  def signed(v):
   try:value=Decimal(v)
   except InvalidOperation:raise ValueError('余额金额格式无效') from None
   if not value.is_finite() or value!=value.quantize(Decimal('.01')) or abs(value)>Decimal('999999999999.99'):raise ValueError('余额须为有效的两位小数金额')
   return int(value*100)
  if body.data_kind not in ('uploaded','simulated'):raise ValueError('来源标记无效')
  bank=signed(body.bank_closing)+core.cents(body.deposits_in_transit)-core.cents(body.outstanding_payments)
  book=signed(body.book_closing)+core.cents(body.bank_credits_not_booked)-core.cents(body.bank_debits_not_booked)
  value=body.model_dump(mode='json');value.update(adjusted_bank=core.money(bank),adjusted_book=core.money(book),difference=core.money(book-bank),balanced=bank==book,metric_version='bank-worksheet-1.0',basis='人工提供的银行与账簿余额及未达项调节试算，不自动核实对账单、不入账、不支付')
  return store('bank_worksheet','bank-worksheet:'+body.external_id,value)
