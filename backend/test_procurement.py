import tempfile,unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app as core,procurement as p,enterprise_controls as controls
class Tests(unittest.TestCase):
 def test_evidence(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'db'));a=FastAPI();p.install(a)
   @a.middleware('http')
   async def scope(r,call):
    x=core.request_database.set(db);y=core.request_organization.set(r.headers.get('org','A'));z=core.request_actor.set({'id':'maker','role':r.headers.get('role','org_admin')})
    try:return await call(r)
    finally:core.request_database.reset(x);core.request_organization.reset(y);core.request_actor.reset(z)
   c=TestClient(a);base='/api/v1/finance-workbench/procurement';payload=dict(case_id='one',external_id='SIM',version='v1',date='2026-11-07',currency='CNY',amount='999999999999.99',quantity='2',supplier='SIM-supplier',source_reference='SIM evidence',data_kind='simulated')
   for kind in p.KINDS:
    r=c.post(base+'/evidence',json=dict(payload,kind=kind));self.assertEqual(r.status_code,201,r.text)
   r=c.get(base+'/one/match').json();self.assertEqual(r['status'],'matched');self.assertEqual(len(r['evidence']),5)
   self.assertEqual(c.post(base+'/evidence',json=dict(payload,kind='invoice')).json()['status'],'already_registered')
   self.assertEqual(c.post(base+'/evidence',json=dict(payload,kind='invoice',amount='1.00')).status_code,409)
   self.assertEqual(c.post(base+'/evidence',json=dict(payload,kind='invoice'),headers={'role':'viewer'}).status_code,403)
   self.assertEqual(c.get(base+'/one/match',headers={'org':'B'}).status_code,404);self.assertEqual(c.get(base+'/one/match?currency=USD').status_code,404)
   for kind in p.KINDS:c.post(base+'/evidence',json=dict(payload,case_id='difference',kind=kind,amount='1.00' if kind=='payment' else '2.00'))
   self.assertEqual(c.get(base+'/difference/match').json()['status'],'quarantined')
   c.post(base+'/evidence',json=dict(payload,case_id='partial',kind='contract'));self.assertEqual(len(c.get(base+'/partial/match').json()['missing']),4)
   x=core.request_database.set(db)
   try:controls.change_period('2026-11','closed',controls.PeriodChange(expected_version=0,reason='test lock'));self.assertTrue(controls.verify(db)['valid'])
   finally:core.request_database.reset(x)
   self.assertEqual(c.post(base+'/evidence',json=dict(payload,case_id='closed',kind='contract')).status_code,409);db.dispose()
if __name__=='__main__':unittest.main()
