"""Complete committed voucher lines plus explicit department-period evidence."""
import json
from sqlalchemy import select
import app as core
from finance_risk_engine import evaluate
from finance_workbench import rows
from integrations import budget_report
from cfo_briefings import shift

def review(start_period,end_period,currency):
 records=[dict(json.loads(r['payload']),id=r['id']) for r in rows() if json.loads(r['payload'])['currency']==currency and start_period<=json.loads(r['payload'])['date'][:7]<=end_period]
 from supplier_registry import registrations
 registered=registrations()
 for record in records:
  supplier=registered.get(record.get('supplier'))
  if supplier:record['supplier_created']=supplier['registered_date'];record['supplier_source_reference']=supplier['source_reference']
 with core.current_db().connect() as c:
  for r in c.execute(select(core.facts).where(core.facts.c.period>=start_period,core.facts.c.period<=end_period,core.facts.c.currency==currency)).mappings():
   p=json.loads(r['payload']);records.append({'id':'journal:'+r['id'],'date':p['posting_date'],'currency':currency,'voucher_id':json.dumps([r['batch_id'],p['voucher_no'],p['posting_date']]),'debit':core.money(r['debit_cents']),'credit':core.money(r['credit_cents'])})
 prior={(r['period'],r['department']):r for r in budget_report(shift(start_period,-12),shift(end_period,-12),currency)}
 for r in budget_report(start_period,end_period,currency):
  p={'id':'department:'+r['period']+':'+r['department'],'date':r['period']+'-01','currency':currency,'department':r['department'],'amount':r['actual']}
  if not r['budget_missing']:p['budget']=r['budget']
  old=prior.get((shift(r['period'],-12),r['department']))
  if old:p['previous_amount']=old['actual']
  records.append(p)
 result=evaluate(records,currency);result['scope']='workbench claims + complete committed voucher groups + department-period actual/budget and prior-year expense; quarantined ERP excluded, see batch quality';return result
