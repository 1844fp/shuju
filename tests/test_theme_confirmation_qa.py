import unittest,tempfile,json
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app as core,theme_routes as t
class ThemeConfirmationQA(unittest.TestCase):
 def test_quarantine_ack_empty_and_snapshot(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'db'));a=FastAPI();t.install(a)
   @a.middleware('http')
   async def scope(r,call):
    x=core.request_database.set(db);o=core.request_organization.set('A')
    try:return await call(r)
    finally:core.request_database.reset(x);core.request_organization.reset(o)
   try:
    with TestClient(a) as c:
     raw=(core.ROOT/'data_platform/theme_templates/budget.csv').read_bytes()
     def preview(data):
      r=c.post('/api/v1/theme-imports/budget/preview',files={'file':('a.csv',data)},data={'data_kind':'simulated'});self.assertEqual(r.status_code,201,r.text);return r.json()
     bad=preview(raw.replace(b'12.30',b'not-money'));self.assertEqual(c.post('/api/v1/theme-imports/'+bad['preview_id']+'/confirm',json={'acknowledge_quarantine':True}).status_code,422)
     # Mix one valid and one invalid independent source row.
     lines=raw.decode('utf-8-sig').splitlines();mixed=('\n'.join(lines+[lines[1].replace('12.30','not-money').replace('SIM-external_id','SIM-invalid')])+'\n').encode()
     p=preview(mixed);self.assertTrue(p['snapshot']['accepted']);self.assertTrue(p['snapshot']['quarantined']);base='/api/v1/theme-imports/'+p['preview_id']+'/confirm'
     self.assertEqual(c.post(base).status_code,409)
     self.assertEqual(c.post(base,json={'acknowledge_quarantine':True,'expected_snapshot_hash':'stale'}).status_code,409)
     self.assertEqual(c.post(base,json={'acknowledge_quarantine':True,'expected_snapshot_hash':p['snapshot']['snapshot_hash']}).status_code,200)
     clean=preview(raw);jid=clean['preview_id']
     with db.begin() as conn:
      payload=clean['snapshot'];payload['data_kind']='uploaded';conn.execute(t.imports.update().where(t.imports.c.id==jid).values(payload=json.dumps(payload)))
     self.assertEqual(c.post('/api/v1/theme-imports/'+jid+'/confirm').status_code,409)
   finally:db.dispose()
if __name__=='__main__':unittest.main(verbosity=2)
