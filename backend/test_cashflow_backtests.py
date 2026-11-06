import tempfile,unittest,json
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app as core,cfo_models as m
class Tests(unittest.TestCase):
 def test_expense_cashflow(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'db'));a=FastAPI();m.install(a)
   @a.middleware('http')
   async def scope(r,call):
    x=core.request_database.set(db);y=core.request_organization.set(r.headers.get('org','A'));z=core.request_actor.set({'id':r.headers.get('actor','maker'),'role':'org_admin'})
    try:return await call(r)
    finally:core.request_database.reset(x);core.request_organization.reset(y);core.request_actor.reset(z)
   c=TestClient(a)
   with db.begin() as con:
    con.execute(core.batches.insert().values(id='sim',sha256='sim',kind='simulated'))
    for i in range(1,6):con.execute(core.facts.insert().values(id=str(i),business_key=str(i),batch_id='sim',period=f'2026-0{i}',currency='CNY',category='expense',debit_cents=i*1000,credit_cents=0,payload='{}'))
   query=dict(start_period='2026-01',end_period='2026-05',window=2,metric='expense');r=c.post('/api/v1/cfo/backtests',json=query);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['mae'],'15.00');self.assertEqual(r.json()['naive_mae'],'10.00')
   query['metric']='operating_cashflow';self.assertEqual(c.post('/api/v1/cfo/backtests',json=query).status_code,422)
   ids=[]
   for i in range(1,6):
    p=dict(period=f'2026-0{i}',currency='CNY',source_reference=f'SIM monthly cashflow {i}',version='1',data_kind='simulated',values={'operating_cash_flow':f'{i*10}.00'})
    r=c.post('/api/v1/cfo/inputs',json=p);self.assertEqual(r.status_code,201,r.text);jid=r.json()['id'];ids.append(jid);self.assertEqual(c.post('/api/v1/cfo/inputs/'+jid+'/approve',json={'reason':'verified monthly source'},headers={'actor':'reviewer'}).status_code,200)
   r=c.post('/api/v1/cfo/backtests',json=query);self.assertEqual(r.status_code,200,r.text);result=r.json();self.assertEqual(result['mae'],'15.00');self.assertEqual(result['naive_mae'],'10.00');self.assertEqual(result['forecast_next'],'45.00');self.assertEqual(result['sources'][0]['source_id'],ids[0])
   for p in result['predictions']:self.assertTrue(all(x<p['period'] for x in p['training_periods']))
   self.assertEqual(c.post('/api/v1/cfo/backtests',json=query,headers={'org':'B'}).status_code,422)
   self.assertEqual(c.post('/api/v1/cfo/backtests',json=dict(query,end_period='2026-06')).status_code,422)
   self.assertEqual(c.post('/api/v1/cfo/backtests',json=dict(query,metric='net_profit')).status_code,422)
   db.dispose()
if __name__=='__main__':unittest.main()

