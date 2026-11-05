import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import app as backend
from fastapi.testclient import TestClient
class BackendTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); backend.app.state.db=backend.engine('sqlite:///'+str(Path(self.tmp.name)/'test.db')); self.client=TestClient(backend.app)
 def tearDown(self):
  os.environ.pop('FINAGENT_API_TOKEN',None); os.environ.pop('FINAGENT_API_ROLE',None); backend.app.state.db.dispose(); self.tmp.cleanup()
 def test_tasks(self):
  r=self.client.post('/api/v1/reports',json={}); self.assertEqual(r.status_code,202)
  self.assertEqual(self.client.get('/api/v1/reports/'+r.json()['task_id']).json()['status'],'completed')
  self.assertEqual(self.client.post('/api/v1/analysis').status_code,503)
 def test_auth(self):
  os.environ['FINAGENT_API_TOKEN']='test-secret'; os.environ['FINAGENT_API_ROLE']='reader'
  self.assertEqual(self.client.get('/api/v1/metrics/finance').status_code,401)
  self.assertEqual(self.client.post('/api/v1/reports',json={},headers={'Authorization':'Bearer test-secret'}).status_code,403)
 def test_validation(self):
  self.assertEqual(self.client.get('/api/v1/ready').status_code,200)
  self.assertIn('error',self.client.post('/api/v1/imports',json={}).json())
  self.assertEqual(self.client.post('/api/v1/imports/preview',files={'file':('bad.xlsx',b'bad')}).status_code,422)
if __name__=='__main__': unittest.main()
