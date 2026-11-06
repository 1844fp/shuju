import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app as core,cfo_models as m
class Tests(unittest.TestCase):
 def test_numbers(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'db'));a=FastAPI();m.install(a)
   @a.middleware('http')
   async def scope(r,call):
    x=core.request_database.set(db);y=core.request_organization.set(r.headers.get('org','A'));z=core.request_actor.set({'id':r.headers.get('actor','maker'),'role':'org_admin'})
    try:return await call(r)
    finally:core.request_database.reset(x);core.request_organization.reset(y);core.request_actor.reset(z)
   c=TestClient(a);values=dict(revenue='100.00',cost='40.00',expense='20.00',net_profit='10.00',equity_open='40.00',equity_close='60.00',current_assets='80.00',current_liabilities='40.00',inventory_close='20.00',inventory_open='20.00',liabilities='40.00',assets='100.00',receivables_open='10.00',receivables_close='10.00',credit_sales='100.00',operating_cash_flow='30.00',capex='5.00')
   r=c.post('/api/v1/cfo/inputs',json=dict(period='2026-01',source_reference='test report',version='1',values=values));self.assertEqual(r.status_code,201,r.text);jid=r.json()['id'];base='/api/v1/cfo/inputs/'+jid
   self.assertEqual(c.get(base+'/ratios').status_code,409);self.assertEqual(c.post(base+'/approve').status_code,403);self.assertEqual(c.post(base+'/approve',headers={'actor':'other'}).status_code,200)
   r=c.get(base+'/ratios').json()['ratios'];self.assertEqual({k:r[k]['value'] for k in r},{'net_margin':'0.1','roe':'0.2','current_ratio':'2','quick_ratio':'1.5','debt_ratio':'0.4','receivable_turnover':'10','inventory_turnover':'2','free_cash_flow':'25.00'})
   self.assertEqual(c.get(base+'/ratios',headers={'org':'B'}).status_code,404);self.assertEqual(c.post(base+'/scenario',json={'revenue_change':'-0.10'}).json()['operating_profit'],'30.00')
   history=[{'period':f'2026-0{i}','revenue':str(i*10),'batch_ids':['test'],'metric_version':'1'} for i in range(1,6)]
   with patch.object(core,'finance',return_value=history):
    r=c.post('/api/v1/cfo/backtests',json=dict(start_period='2026-01',end_period='2026-05',window=2));self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['mae'],'15');self.assertEqual(r.json()['forecast_next'],'45')
   self.assertIsNone(m.ratios({'values':{}})['roe']['value']);db.dispose()
if __name__=='__main__':unittest.main()
