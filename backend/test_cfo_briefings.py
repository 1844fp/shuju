import tempfile,unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app as core,cfo_briefings as b
class Tests(unittest.TestCase):
 def test_snapshot_and_ticks(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'db.sqlite'));a=FastAPI();b.install(a)
   @a.middleware('http')
   async def scope(r,call):
    x=core.request_database.set(db);y=core.request_organization.set(r.headers.get('org','A'))
    try:return await call(r)
    finally:core.request_database.reset(x);core.request_organization.reset(y)
   c=TestClient(a);v=c.get('/api/v1/cfo/overview').json();self.assertIsNone(v['changes']['yoy']['revenue']['value']);self.assertIn('roe',v['unavailable'])
   self.assertEqual(c.post('/api/v1/briefing-schedules',json={'id':'daily'}).status_code,201)
   first=c.post('/api/v1/briefing-schedules/daily/tick',json={'date':'2026-11-06'});self.assertEqual(first.status_code,200,first.text);self.assertEqual(first.json(),c.post('/api/v1/briefing-schedules/daily/tick',json={'date':'2026-11-06'}).json())
   self.assertEqual(c.get('/api/v1/briefing-schedules',headers={'org':'B'}).json(),[]);self.assertEqual(c.post('/api/v1/briefing-schedules/daily/tick',json={'date':'2026-11-06'},headers={'org':'B'}).status_code,404);db.dispose()
if __name__=='__main__':unittest.main()
