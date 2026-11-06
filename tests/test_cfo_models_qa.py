import unittest,tempfile,json
from pathlib import Path
from decimal import Decimal
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app as core,cfo_models as model
from sqlalchemy import select,func
VALUES=dict(revenue='200',net_profit='20',equity_open='80',equity_close='120',current_assets='150',current_liabilities='50',inventory_close='30',liabilities='40',assets='200',credit_sales='120',receivables_open='20',receivables_close='40',cost='60',inventory_open='10',operating_cash_flow='50',capex='12')
class CFOModelsQA(unittest.TestCase):
 def test_eight_formulas(self):
  r=model.ratios({'values':VALUES});expected=dict(net_margin='.1',roe='.2',current_ratio='3',quick_ratio='2.4',debt_ratio='.2',receivable_turnover='4',inventory_turnover='3',free_cash_flow='38')
  self.assertEqual(set(r),set(expected))
  for k,v in expected.items():self.assertEqual(Decimal(r[k]['value']),Decimal(v));self.assertIsNone(r[k]['reason'])
 def test_missing_and_zero(self):
  r=model.ratios({'values':{}})
  self.assertTrue(all(x['value'] is None and x['reason'].startswith('missing:') for x in r.values()))
  r=model.ratios({'values':{k:'0' for k in VALUES}})
  for k,x in r.items():
   if k=='free_cash_flow':self.assertEqual(x['value'],'0')
   else:self.assertIsNone(x['value']);self.assertEqual(x['reason'],'zero_denominator')
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='work');self.db=core.engine('sqlite:///'+str(Path(self.tmp.name).resolve()/'db.sqlite'));self.app=FastAPI();model.install(self.app)
  @self.app.middleware('http')
  async def scope(r,call):
   a=core.request_database.set(self.db);b=core.request_organization.set(r.headers.get('org','A'));c=core.request_actor.set({'id':r.headers.get('actor','maker'),'role':'org_admin'})
   try:return await call(r)
   finally:core.request_database.reset(a);core.request_organization.reset(b);core.request_actor.reset(c)
  self.c=TestClient(self.app)
 def tearDown(self):self.c.close();self.db.dispose();self.tmp.cleanup()
 def test_approved_source_scope_and_get_readonly(self):
  p=dict(period='2026-01',currency='CNY',source_reference='simulated:source<&>',version='qa-1',data_kind='simulated',values=VALUES)
  r=self.c.post('/api/v1/cfo/inputs',json=p);self.assertEqual(r.status_code,201,r.text);jid=r.json()['id'];base='/api/v1/cfo/inputs/'+jid
  self.assertEqual(self.c.get(base+'/ratios').status_code,409);self.assertEqual(self.c.post(base+'/approve').status_code,403)
  self.assertEqual(self.c.post(base+'/approve',headers={'actor':'reviewer'}).status_code,200)
  for _ in range(2):
   r=self.c.get(base+'/ratios');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['source'],p)
  with self.db.connect() as c:self.assertEqual(c.execute(select(func.count()).select_from(model.calculations)).scalar(),0)
  self.assertEqual(self.c.get(base+'/ratios',headers={'org':'B'}).status_code,404)
 def load(self,month,amount):
  rows=[dict(posting_date='2026-'+month+'-01',voucher_no=month,line_no=str(i),account_code=code,department_code='D',currency='CNY',debit=amount if i==1 else '0',credit=amount if i==2 else '0') for i,code in ((1,'1002'),(2,'6001'))]
  self.assertEqual(core.ingest(self.db,rows,month,month,kind='simulated')['accepted_rows'],2)
 def test_backtest_future_leakage_and_naive(self):
  for m,v in [('01','10'),('02','20'),('03','30'),('04','1000')]:self.load(m,v)
  base=dict(start_period='2026-01',end_period='2026-03',window=2,currency='CNY');a=self.c.post('/api/v1/cfo/backtests',json=base);self.assertEqual(a.status_code,200,a.text);a=a.json()
  b=self.c.post('/api/v1/cfo/backtests',json={**base,'end_period':'2026-04'}).json()
  self.assertEqual(a['predictions'][0],b['predictions'][0]);self.assertEqual(Decimal(a['predictions'][0]['forecast']),15);self.assertEqual(Decimal(a['mae']),15);self.assertEqual(Decimal(a['naive_mae']),10)
  self.assertEqual(Decimal(b['predictions'][1]['forecast']),25);self.assertEqual(Decimal(b['predictions'][1]['naive_forecast']),30)
  self.assertTrue(all(x['data_kind']==['simulated'] for x in a['sources']));self.assertTrue(all(x['period']<='2026-03' for x in a['sources']))
if __name__=='__main__':unittest.main(verbosity=2)
