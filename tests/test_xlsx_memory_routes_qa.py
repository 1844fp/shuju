import unittest,io,csv,tempfile,os
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook
import test_identity as fixture
import identity
class RouteQA(unittest.TestCase):
 def setUp(self):
  self.f=fixture.IdentityTests();self.f.setUp();self.addCleanup(self.f.tearDown);self.tmp=tempfile.TemporaryDirectory(dir='work');self.addCleanup(self.tmp.cleanup)
  self.env=patch.dict(os.environ,{'FINAGENT_HARNESS_PATH':str(Path(self.tmp.name)/'h.sqlite')});self.env.start();self.addCleanup(self.env.stop)
 def test_xlsx_amount_source_scope_revoke(self):
  c=self.f.client;raw=(fixture.r/'data_platform/theme_templates/budget.csv').read_text(encoding='utf-8-sig');w=Workbook();s=w.active
  for row in csv.reader(io.StringIO(raw)):s.append(row)
  b=io.BytesIO();w.save(b);w.close();data=b.getvalue();path='/api/v1/theme-imports/budget/preview'
  self.f.login('reader-a');self.assertEqual(c.post(path,files={'file':('q.xlsx',data)}).status_code,403)
  self.f.login('admin-a');r=c.post(path,files={'file':('q.xlsx',data)},data={'data_kind':'simulated'});self.assertEqual(r.status_code,201,r.text);p=r.json();self.assertIn('12.30',str(p['snapshot']['accepted']));base='/api/v1/theme-imports/'+p['preview_id'];self.assertEqual(c.get(base+'/source').content,data);self.assertEqual(c.post(base+'/confirm').status_code,200)
  self.f.login('admin-b');self.assertEqual(c.get(base).status_code,404)
  self.f.login('admin-a');self.assertEqual(c.post(base+'/revoke',json={'reason':'qa review'}).status_code,200);self.assertEqual(c.post(base+'/confirm').status_code,409);self.assertEqual(c.get(base+'/source').content,data)
 def test_memory_plan_auth_resume_scope(self):
  f=self.f;c=f.client;identity.create_user('reviewer-a','Test-password-123',f.a['id'],'org_admin');f.login('admin-a')
  r=c.post('/api/v1/agent-runs',json={'intent':'budget'});self.assertEqual(r.status_code,201,r.text);jid=r.json()['task_id'];self.assertEqual(r.json()['status'],'awaiting_approval');self.assertEqual(set(r.json()['results']),{'data','budget'});base='/api/v1/agent-runs/'+jid
  self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'qa review'}).status_code,403)
  f.login('admin-b');self.assertEqual(c.post(base+'/resume').status_code,404)
  f.login('reviewer-a');self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'qa review'}).status_code,200);r=c.post(base+'/resume');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'completed');self.assertEqual(set(r.json()['results']),{'data','budget','report'});self.assertTrue(all(x['status']=='reused' for x in r.json()['trace'] if x['node']!='report'))
  self.assertEqual(c.post('/api/v1/agent-runs',json={'intent':'payment'}).status_code,422)
  f.login('reader-a');self.assertEqual(c.post('/api/v1/agent-runs',json={'intent':'budget'}).status_code,403)
if __name__=='__main__':unittest.main(verbosity=2)

