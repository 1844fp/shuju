import tempfile, unittest
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.testclient import TestClient
import app as core
import finance_workbench as w
class Tests(unittest.TestCase):
 def test_loop(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'test.db'));a=FastAPI();w.install(a)
   @a.middleware('http')
   async def identity(r,call):
    r.state.identity={'id':r.headers.get('actor','maker'),'role':'org_admin'};x=core.request_database.set(db);y=core.request_organization.set(r.headers.get('org','A'))
    try:return await call(r)
    finally:core.request_database.reset(x);core.request_organization.reset(y)
   c=TestClient(a);r=c.post('/api/v1/finance-workbench/documents',json=dict(external_id='expense-1',kind='expense',date='2026-11-06',amount='100.01',data_kind='simulated'));self.assertEqual(r.status_code,201);jid=r.json()['id'];base='/api/v1/finance-workbench/documents/'+jid
   self.assertEqual(c.get('/api/v1/finance-workbench/documents',headers={'org':'B'}).json(),[])
   self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'ok'}).status_code,403)
   self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'ok'},headers={'actor':'reviewer'}).status_code,200)
   self.assertEqual(c.post(base+'/voucher-draft').json()['lines'][0]['debit'],'100.01');db.dispose()
if __name__=='__main__':unittest.main()
