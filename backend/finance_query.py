"""Bounded Chinese query templates over organization-scoped accepted facts."""
import json,re
from fastapi import HTTPException
from sqlalchemy import select
from agents.runtime import Query
VERSION='department-expense-1.0'

def parse(question):
 text=re.sub(r'\s+','',question)
 match=re.fullmatch(r'(?:查询|查看)?(\d{4})年(?:(\d{1,2})月|第([一二三四1234])季度|全年)(销售费用|费用)最高的(?:五|5)个部门[。？?]?',text)
 if not match:raise HTTPException(422,'暂支持：查询2026年第三季度费用最高的五个部门；不会执行任意SQL或猜测查询范围')
 year,month,quarter,metric=match.groups()
 if month:start=end=int(month)
 elif quarter:start=3*('一二三四'.index(quarter) if quarter in '一二三四' else int(quarter)-1)+1;end=start+2
 else:start,end=1,12
 return Query(start_period=f'{year}-{start:02d}',end_period=f'{year}-{end:02d}'),metric

def execute(question,currency='CNY'):
 import app as core
 query,metric=parse(question);query=Query(**{**query.model_dump(),'currency':currency})
 allowed=None;mapping={}
 if metric=='销售费用':
  from financial_statements import account_mapping
  mapping=account_mapping();allowed={code for code,(_,line) in mapping.items() if line=='selling_expense'}
 totals={};batches={};codes={}
 with core.current_db().connect() as c:
  rows=c.execute(select(core.facts).where(core.facts.c.period>=query.start_period,core.facts.c.period<=query.end_period,core.facts.c.currency==currency,core.facts.c.category=='expense')).mappings()
  unmapped=[]
  for row in rows:
   payload=json.loads(row['payload']);code=payload['account_code']
   if allowed is not None:
    if code not in mapping:unmapped.append(code)
    if code not in allowed:continue
   department=payload.get('department_code') or '未分配部门'
   totals[department]=totals.get(department,0)+row['debit_cents']-row['credit_cents']
   batches.setdefault(department,set()).add(row['batch_id']);codes.setdefault(department,set()).add(code)
  if unmapped:raise HTTPException(422,'费用科目尚未明确映射，不能完整识别销售费用：'+','.join(sorted(set(unmapped))))
  kinds=dict(c.execute(select(core.batches.c.id,core.batches.c.kind)).all())
 result=[dict(department=d,amount=core.money(amount),batch_ids=sorted(batches[d]),account_codes=sorted(codes[d]),data_kind=sorted({kinds[b] for b in batches[d]})) for d,amount in sorted(totals.items(),key=lambda item:(-item[1],item[0]))[:5]]
 return dict(mode='controlled_template',metric=metric,metric_version=VERSION,query=query.model_dump(),rows=result,scope='accepted_facts_only',explanation='按期间与币种汇总已接收费用借方减贷方；销售费用仅使用明确核准的报表映射。')

def install(app):
 @app.get('/api/v1/finance-query')
 def query(q:str,currency:str='CNY'):
  if len(q)>200:raise HTTPException(422,'查询过长')
  return execute(q,currency)
