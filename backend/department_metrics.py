import json
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
import app as core
from cfo_briefings import shift

def ranking(start,end,currency,metric,limit):
 if metric not in ('revenue','cost','expense') or not 1<=limit<=100:raise HTTPException(422,'指标或条数无效')
 core.metrics(core.current_db(),start,end,currency)
 def collect(a,b):
  out={}
  with core.current_db().connect() as c:
   kinds=dict(c.execute(select(core.batches.c.id,core.batches.c.kind)).all())
   for r in c.execute(select(core.facts).where(core.facts.c.period>=a,core.facts.c.period<=b,core.facts.c.currency==currency,core.facts.c.category==metric)).mappings():
    department=json.loads(r['payload']).get('department_code') or '未分配部门';v=out.setdefault(department,{'cents':0,'batch_ids':set(),'data_kind':set()});v['cents']+=r['credit_cents']-r['debit_cents'] if metric=='revenue' else r['debit_cents']-r['credit_cents'];v['batch_ids'].add(r['batch_id']);v['data_kind'].add(kinds[r['batch_id']])
  return out
 current=collect(start,end);prior=collect(shift(start,-12),shift(end,-12));result=[]
 for d,v in sorted(current.items(),key=lambda x:(-x[1]['cents'],x[0]))[:limit]:
  p=prior.get(d);den=p['cents'] if p else None
  result.append({'department':d,'amount':core.money(v['cents']),'prior_amount':core.money(den) if den is not None else None,'yoy':str(Decimal(v['cents']-den)/abs(Decimal(den))) if den else None,'yoy_reason':None if den else 'missing_prior_or_zero_denominator','batch_ids':sorted(v['batch_ids']),'data_kind':sorted(v['data_kind']),'prior_batch_ids':sorted(p['batch_ids']) if p else [],'prior_data_kind':sorted(p['data_kind']) if p else []})
 return {'rows':result,'metric':metric,'currency':currency,'start_period':start,'end_period':end,'prior_start_period':shift(start,-12),'prior_end_period':shift(end,-12),'metric_version':'department-1.0','scope':'accepted_facts_only'}
def install(app):
 @app.get('/api/v1/finance/departments')
 def departments(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY',metric:str='expense',limit:int=5):return ranking(start_period,end_period,currency,metric,limit)
