import unittest,json
from pathlib import Path
from decimal import Decimal
import test_identity as fixture
import identity,app as core
class R11BacktestQA(unittest.TestCase):
 def setUp(self):
  self.f=fixture.IdentityTests();self.f.setUp();self.addCleanup(self.f.tearDown);identity.create_user('reviewer-a','Test-password-123',self.f.a['id'],'org_admin')
 def request(self,metric,end='2026-04',start='2026-01'):
  return self.f.client.post('/api/v1/cfo/backtests',json=dict(start_period=start,end_period=end,currency='CNY',window=2,metric=metric))
 def check(self,result,first,second):
  p=result['predictions'];self.assertEqual([x['period'] for x in p],['2026-03','2026-04']);self.assertEqual(Decimal(p[0]['forecast']),Decimal(first));self.assertEqual(Decimal(p[1]['forecast']),Decimal(second))
  for x in p:self.assertTrue(all(t<x['period'] for t in x['training_periods']));self.assertEqual(x['training_periods'][-1],{'2026-03':'2026-02','2026-04':'2026-03'}[x['period']])
 def test_expense_revenue_exact_and_missing_edges(self):
  db=identity.tenant_engine(self.f.a['id'])
  for month,expense in [('01','0.10'),('02','0.20'),('03','0.30'),('04','1000.00')]:
   rows=[]
   for n,code in ((1,'6602'),(2,'1002')):rows.append(dict(posting_date='2026-'+month+'-01',voucher_no=month,line_no=str(n),account_code=code,department_code='D',currency='CNY',debit=expense if n==1 else '0',credit=expense if n==2 else '0'))
   self.assertEqual(core.ingest(db,rows,month,month,kind='simulated')['accepted_rows'],2)
  self.f.login('admin-a');r=self.request('expense');self.assertEqual(r.status_code,200,r.text);a=r.json();self.check(a,'.15','.25');self.assertEqual(Decimal(a['predictions'][0]['naive_forecast']),Decimal('.20'));self.assertEqual(Decimal(a['predictions'][0]['absolute_error']),Decimal('.15'))
  short=self.request('expense','2026-03').json();self.assertEqual(short['predictions'][0],a['predictions'][0]);self.assertEqual(self.request('expense',start='2025-12').status_code,422);self.assertEqual(self.request('expense',end='2026-05').status_code,422)
  revenue=self.request('revenue');self.assertEqual(revenue.status_code,200);self.assertTrue(all(Decimal(x['actual'])==0 for x in revenue.json()['predictions']))
  self.f.login('admin-b');self.assertEqual(self.request('expense').status_code,422);self.f.login('reader-a');self.assertEqual(self.request('expense').status_code,403)
 def test_cashflow_approved_only_future_scope_duplicate(self):
  f=self.f;c=f.client;f.login('admin-a');ids=[]
  for month,amount in [('01','-10.01'),('02','20.01'),('03','30.01'),('04','999999.99')]:
   r=c.post('/api/v1/cfo/inputs',json=dict(period='2026-'+month,currency='CNY',source_reference='simulated:cash-'+month,version='v1',data_kind='simulated',values={'operating_cash_flow':amount}));self.assertEqual(r.status_code,201,r.text);ids.append(r.json()['id'])
  self.assertEqual(self.request('operating_cashflow').status_code,422)
  self.assertEqual(c.post('/api/v1/cfo/inputs/'+ids[0]+'/approve').status_code,403);f.login('reviewer-a')
  for jid in (ids[0],ids[2],ids[3]):self.assertEqual(c.post('/api/v1/cfo/inputs/'+jid+'/approve').status_code,200)
  self.assertEqual(self.request('operating_cashflow').status_code,422)
  self.assertEqual(c.post('/api/v1/cfo/inputs/'+ids[1]+'/approve').status_code,200)
  r=self.request('operating_cashflow');self.assertEqual(r.status_code,200,r.text);a=r.json();self.check(a,'5.00','25.01');self.assertEqual(Decimal(a['predictions'][0]['naive_forecast']),Decimal('20.01'));self.assertEqual(Decimal(a['predictions'][0]['absolute_error']),Decimal('25.01'));self.assertEqual(Decimal(a['predictions'][0]['naive_absolute_error']),Decimal('10.00'))
  self.assertEqual(self.request('operating_cashflow',end='2026-03').json()['predictions'][0],a['predictions'][0]);self.assertEqual({x['source_id'] for x in a['sources']},set(ids));self.assertTrue(all(x['data_kind']=='simulated' and len(x['source_hash'])==64 and x['version']=='v1' for x in a['sources']))
  self.assertEqual(self.request('operating_cashflow',start='2025-12').status_code,422);f.login('admin-b');self.assertEqual(self.request('operating_cashflow').status_code,422);self.assertEqual(c.get('/api/v1/cfo/inputs/'+ids[0]+'/ratios').status_code,404)
  f.login('admin-a');dup=c.post('/api/v1/cfo/inputs',json=dict(period='2026-01',currency='CNY',source_reference='simulated:duplicate',version='v2',data_kind='simulated',values={'operating_cash_flow':'2.00'})).json()['id'];f.login('reviewer-a');self.assertEqual(c.post('/api/v1/cfo/inputs/'+dup+'/approve').status_code,200);self.assertEqual(self.request('operating_cashflow').status_code,409)
  Path('work/redesign/r11-cashflow-result.json').write_text(json.dumps(a,indent=2),encoding='utf-8')
if __name__=='__main__':unittest.main(verbosity=2)
