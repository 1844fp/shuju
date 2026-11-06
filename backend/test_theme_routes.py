import tempfile,unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app as core,theme_routes as t,enterprise_controls as controls
class Tests(unittest.TestCase):
 def test_loop(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'db'));a=FastAPI();t.install(a)
   @a.middleware('http')
   async def scope(r,call):
    x=core.request_database.set(db);o=core.request_organization.set(r.headers.get('org','A'));actor=core.request_actor.set({'id':'test','role':r.headers.get('role','org_admin')})
    try:return await call(r)
    finally:core.request_database.reset(x);core.request_organization.reset(o);core.request_actor.reset(actor)
   c=TestClient(a);raw=(core.ROOT/'data_platform/theme_templates/budget.csv').read_bytes()
   def preview(raw):return c.post('/api/v1/theme-imports/budget/preview',files={'file':('budget.csv',raw)},data={'data_kind':'simulated'})
   r=preview(raw);self.assertEqual(r.status_code,201,r.text);jid=r.json()['preview_id'];base='/api/v1/theme-imports/'+jid
   self.assertEqual(preview(raw).json()['preview_id'],jid);self.assertEqual(c.get(base+'/source').content,raw);self.assertEqual(c.get(base,headers={'org':'B'}).status_code,404)
   self.assertEqual(c.post(base+'/confirm').status_code,200);self.assertEqual(c.post(base+'/confirm').status_code,200)
   self.assertEqual(c.post(base+'/revoke',json={'reason':'test revoke'},headers={'role':'viewer'}).status_code,403)
   self.assertEqual(c.post(base+'/revoke',json={'reason':'test revoke'},headers={'org':'B'}).status_code,404)
   self.assertEqual(c.post(base+'/revoke',json={'reason':'test revoke'}).status_code,200);self.assertEqual(c.post(base+'/revoke',json={'reason':'test revoke'}).status_code,200);self.assertEqual(c.get(base+'/source').content,raw);self.assertEqual(c.post(base+'/confirm').status_code,409)
   other=preview(raw.replace(b'12.30',b'13.30')).json()['preview_id'];self.assertEqual(c.post('/api/v1/theme-imports/'+other+'/confirm').status_code,409)
   bad=preview(raw.replace(b'12.30',b'not-money')).json();self.assertEqual(len(bad['snapshot']['quarantined']),1)
   x=core.request_database.set(db);o=core.request_organization.set('A')
   try:controls.change_period('2026-01','closed',controls.PeriodChange(expected_version=0,reason='test lock'))
   finally:core.request_database.reset(x);core.request_organization.reset(o)
   fresh=preview(raw.replace(b'SIM-external_id',b'SIM-new')).json()['preview_id'];self.assertEqual(c.post('/api/v1/theme-imports/'+fresh+'/confirm').status_code,409);db.dispose()
if __name__=='__main__':unittest.main()
