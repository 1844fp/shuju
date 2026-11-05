import sys,unittest,csv,io,os
from pathlib import Path
r=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(r));sys.path.insert(0,str(r/'backend'))
from test_finance import FinanceTests
class IntegratedTests(FinanceTests):
 def test_analysis_task_and_sources(self):
  self.load();x=self.client.post('/api/v1/analysis',json={'mode':'demo','question':'毛利率与经营利润'});self.assertEqual(x.status_code,200,x.text);result=x.json();self.assertEqual(result['status'],'completed');self.assertEqual(len(result['rows']),12);self.assertTrue(result['sources']);self.assertTrue(result['tool_calls']);self.assertEqual(self.client.get('/api/v1/analysis/'+result['task_id']).json()['answer'],result['answer']);self.assertTrue(self.client.get('/api/v1/audit').json())
 def test_budget_and_risk(self):
  self.load();payload=dict(external_id='budget1',kind='budget',period='2026-01',department='D01',amount='10000')
  a=self.client.post('/api/v1/finance/registers',json=payload);self.assertEqual(a.status_code,201,a.text)
  self.assertEqual(self.client.post('/api/v1/finance/registers',json=payload).json()['id'],a.json()['id'])
  self.assertEqual(self.client.post('/api/v1/finance/registers',json=dict(payload,amount='20000')).status_code,409)
  rows=self.client.get('/api/v1/finance/budget?start_period=2026-01&end_period=2026-01').json();self.assertEqual(rows[0]['actual'],'18500.00');self.assertEqual(rows[0]['variance'],'8500.00');self.assertTrue(rows[0]['over_budget'])
  self.assertIn('budget_exceeded',[x['rule'] for x in self.client.get('/api/v1/risks').json()['items']])
 def test_aging_and_period(self):
  payload=dict(external_id='ar1',kind='receivable',period='2026-01',department='D01',amount='1000',settled='200',due_date='2026-02-01',counterparty='模拟客户')
  self.assertEqual(self.client.post('/api/v1/finance/registers',json=payload).status_code,201)
  data=self.client.get('/api/v1/finance/aging?as_of=2026-03-15').json();self.assertEqual(data['outstanding'],'800.00');self.assertEqual(data['rows'][0]['days_overdue'],42)
  self.assertEqual(self.client.get('/api/v1/finance/aging?as_of=bad').status_code,422)
  self.assertEqual(self.client.post('/api/v1/finance/registers',json=dict(payload,external_id='ar2',settled='2000')).status_code,422)
 def test_lineage_dictionary_knowledge(self):
  b=self.load();self.assertEqual(len(self.client.get('/api/v1/governance/lineage/'+b['batch_id']).json()['edges']),4)
  self.assertIn('gross_margin',self.client.get('/api/v1/governance/dictionary').json()['metrics']);self.assertTrue(self.client.get('/api/v1/knowledge/search?q=毛利率').json()['matches'])
 def test_proxy_and_static_boundary(self):
  self.assertEqual(self.client.get('/static/operations.js').status_code,200)
  self.assertEqual(self.client.get('/static/package.json').status_code,404)
  self.assertNotEqual(self.client.post('/api/v1/analysis',json={'mode':'demo'},headers={'origin':'http://127.0.0.1:3000'}).status_code,403)
 def test_analysis_permission(self):
  os.environ['FINAGENT_API_TOKEN']='secret';os.environ['FINAGENT_API_ROLE']='reader'
  try:
   self.assertEqual(self.client.post('/api/v1/analysis',json={'mode':'demo'},headers={'Authorization':'Bearer secret'}).status_code,403)
   self.assertEqual(self.client.get('/api/v1/audit').status_code,401)
  finally:os.environ.pop('FINAGENT_API_TOKEN');os.environ.pop('FINAGENT_API_ROLE')
if __name__=='__main__':unittest.main(verbosity=2)
