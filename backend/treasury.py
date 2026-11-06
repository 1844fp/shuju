"""Bank analysis ledger. Records and reconciles data; never executes transfers."""
import json,re
from datetime import date
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
from fastapi import HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import MetaData,Table,Column,String,Text,select
import app as core
meta=MetaData();bank=Table('finance_bank_transaction',meta,Column('id',String,primary_key=True),Column('external_id',String,unique=True),Column('payload',Text))
class Transaction(BaseModel):
    model_config=ConfigDict(extra='forbid')
    external_id:str=Field(min_length=1,max_length=80)
    posting_date:date
    account:str='1002'
    reference:str=Field(min_length=1,max_length=100)
    currency:str='CNY'
    inflow:str='0'
    outflow:str='0'
    category:str='unclassified'
    data_kind:str='uploaded'
def rows():
    meta.create_all(core.current_db())
    with core.current_db().connect() as c:return [json.loads(x) for x in c.execute(select(bank.c.payload)).scalars()]
def validate(start,end,currency,account):
    from agents.runtime import Query
    Query(start_period=start,end_period=end,currency=currency)
    if account!='1002':raise ValueError('本期仅支持明确映射到银行存款科目1002的账户，不自动匹配其他账户')
def selected(start,end,currency,account):
    validate(start,end,currency,account)
    return [r for r in rows() if start<=r['posting_date'][:7]<=end and r['currency']==currency and r['account']==account]
def create(body):
    validate(body.posting_date.strftime('%Y-%m'),body.posting_date.strftime('%Y-%m'),body.currency,body.account)
    incoming,outgoing=core.cents(body.inflow),core.cents(body.outflow)
    if (incoming>0)==(outgoing>0):raise ValueError('流水须且仅须一方有金额')
    if body.category not in ('operating','investing','financing','unclassified') or body.data_kind not in ('uploaded','simulated'):raise ValueError('现金流分类或来源标记无效')
    value=body.model_dump(mode='json');value.update(inflow=core.money(incoming),outflow=core.money(outgoing))
    meta.create_all(core.current_db())
    import enterprise_controls as controls
    controls.initialize(core.current_db())
    with core.current_db().begin() as c:
        old=c.execute(select(bank.c.payload).where(bank.c.external_id==body.external_id)).scalar()
        if old:
            previous=json.loads(old)
            if any(previous[k]!=v for k,v in value.items()):raise HTTPException(409,'相同外部编号已有不同内容')
            return previous
        controls.assert_open(c,{value['posting_date'][:7]})
        value.update(id=core.uid(),created_at=core.now(),raw_payload=body.model_dump(mode='json'));c.execute(bank.insert().values(id=value['id'],external_id=body.external_id,payload=json.dumps(value,ensure_ascii=False)))
        c.execute(core.audit.insert().values(id=core.uid(),action='bank_register',resource=value['id'],created=core.now()))
        controls.append(c,'bank_register',value['id'])
    return value

def reconcile(start,end,currency,account):
    entries=selected(start,end,currency,account);left=defaultdict(list);right=defaultdict(list)
    for r in entries:left[(r['posting_date'],r['reference'],core.cents(r['inflow'])-core.cents(r['outflow']))].append(r)
    with core.current_db().connect() as c:details=c.execute(select(core.facts).where(core.facts.c.period>=start,core.facts.c.period<=end,core.facts.c.currency==currency)).mappings().all()
    groups={}
    for f in details:
        p=json.loads(f['payload'])
        if p['account_code']!=account:continue
        source_system=json.loads(f['business_key'])[0]
        k=(p['posting_date'],p['voucher_no'],source_system);g=groups.setdefault(k,{'net':0,'entry_ids':[],'batch_ids':set()});g['net']+=f['debit_cents']-f['credit_cents'];g['entry_ids'].append(f['id']);g['batch_ids'].add(f['batch_id'])
    for (d,ref,source_system),g in groups.items():right[(d,ref,g['net'])].append({'posting_date':d,'reference':ref,'net':core.money(g['net']),'entry_ids':g['entry_ids'],'batch_ids':sorted(g['batch_ids'])})
    result={'matches':[],'unmatched_bank':[],'unmatched_ledger':[],'ambiguous':[],'metric_version':'treasury-1.0','rule':'日期、凭证引用、账户、币种及金额精确且一对一；不进行模糊或自动余额调整'}
    for key in sorted(set(left)|set(right)):
        a,b=left[key],right[key]
        if len(a)==len(b)==1:result['matches'].append({'bank':a[0],'ledger':b[0]})
        elif a and b:result['ambiguous'].append({'bank':a,'ledger':b,'reason':'多个候选，需人工核对'})
        else:result['unmatched_bank'].extend(a);result['unmatched_ledger'].extend(b)
    return result

def cashflow(start,end,currency,account):
    groups=defaultdict(lambda:{'inflow':0,'outflow':0,'ids':[],'kinds':set()})
    for r in selected(start,end,currency,account):
        g=groups[(r['posting_date'][:7],r['category'])];g['inflow']+=core.cents(r['inflow']);g['outflow']+=core.cents(r['outflow']);g['ids'].append(r['id']);g['kinds'].add(r['data_kind'])
    return {'metric_version':'treasury-1.0','rows':[{'period':p,'currency':currency,'category':cat,'inflow':core.money(v['inflow']),'outflow':core.money(v['outflow']),'net':core.money(v['inflow']-v['outflow']),'transaction_ids':v['ids'],'data_kind':sorted(v['kinds'])} for (p,cat),v in sorted(groups.items())],'basis':'按人工明确分类的银行流水统计；unclassified不推定为经营活动，不代表完整会计准则现金流量表'}
def shift(period,delta):
    y,m=map(int,period.split('-'));index=y*12+m-1+delta;return f'{index//12:04}-{index%12+1:02}'
def forecast(currency,account,months,history_end):
    if not 1<=months<=12:raise ValueError('预测月数须为1至12')
    validate(history_end,history_end,currency,account)
    periods=[shift(history_end,-2),shift(history_end,-1),history_end];history=selected(periods[0],history_end,currency,account);totals=defaultdict(int)
    for x in history:totals[x['posting_date'][:7]]+=core.cents(x['inflow'])-core.cents(x['outflow'])
    missing=[p for p in periods if p not in totals]
    if missing:return {'method':'trailing_three_calendar_month_mean','scenario_only':True,'metric_version':'treasury-1.0','data_kind':sorted({x['data_kind'] for x in history}),'history_periods':periods,'missing_periods':missing,'rows':[],'sources':[],'note':'历史月份缺少流水，不把缺失视为零，不生成预测'}
    mean=int((Decimal(sum(totals.values()))/3).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    return {'method':'trailing_three_calendar_month_mean','scenario_only':True,'metric_version':'treasury-1.0','data_kind':sorted({x['data_kind'] for x in history}),'history_periods':periods,'rows':[{'period':shift(history_end,n),'forecast_net':core.money(mean)} for n in range(1,months+1)],'sources':[x['id'] for x in history],'currency':currency,'note':'仅将过去三个月平均银行净流量平移，非承诺、非资金余额预测，未纳入季节性和未来合同'}
def install(app):
    @app.post('/api/v1/bank/transactions',status_code=201)
    def register(body:Transaction):return create(body)
    @app.get('/api/v1/bank/transactions')
    def listing():return rows()
    @app.get('/api/v1/bank/reconcile')
    def reconciliation(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY',account:str='1002'):return reconcile(start_period,end_period,currency,account)
    @app.get('/api/v1/finance/cashflow')
    def flow(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY',account:str='1002'):return cashflow(start_period,end_period,currency,account)
    @app.get('/api/v1/finance/cashflow/forecast')
    def prediction(currency:str='CNY',account:str='1002',months:int=3,history_end:str|None=None):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return forecast(currency,account,months,history_end or datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m'))
