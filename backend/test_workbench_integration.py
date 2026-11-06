import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import app as core
import identity, enterprise_controls as controls
class Integrated(unittest.TestCase):
 def test_real_routes(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   engines={o:core.engine('sqlite:///'+str(Path(d).resolve()/(o+'.db'))) for o in ('A','B')}
   def auth(r):return dict(id=r.headers.get('actor','maker'),username='test',role=r.headers.get('role','org_admin'),organization_id=r.headers.get('org','A'))
   with patch.dict(os.environ,{'FINAGENT_AUTH_MODE':'users','FINAGENT_HARNESS_PATH':str(Path(d)/'harness.sqlite')}),patch.object(identity,'authenticate',side_effect=auth),patch.object(identity,'tenant_engine',side_effect=lambda org:engines[org]):
    c=TestClient(core.app);base='/api/v1/finance-workbench/documents';p=dict(external_id='one',kind='expense',date='2026-11-06',amount='100.01',data_kind='simulated')
    r=c.post(base,json=p);self.assertEqual(r.status_code,201,r.text);jid=r.json()['id'];self.assertEqual(c.post(base,json=p).json()['id'],jid)
    self.assertEqual(c.post(base,json=dict(p,amount='100.02')).status_code,409)
    self.assertEqual(c.get(base,headers={'org':'B'}).json(),[])
    self.assertEqual(c.post(base,json=p,headers={'role':'viewer'}).status_code,403)
    self.assertEqual(c.post(base+'/'+jid+'/review',json=dict(decision='approved',reason='verified')).status_code,403)
    self.assertEqual(c.post(base+'/'+jid+'/review',json=dict(decision='approved',reason='verified'),headers={'actor':'reviewer'}).status_code,200)
    self.assertEqual(c.post(base+'/'+jid+'/voucher-draft').status_code,200)
    close=c.post('/api/v1/enterprise/periods/2026-11/close',json=dict(expected_version=0,reason='test lock'));self.assertEqual(close.status_code,200,close.text)
    self.assertEqual(c.post(base,json=dict(p,external_id='two')).status_code,409)
    self.assertEqual(c.post(base,json=p).json()['id'],jid)
    self.assertTrue(controls.verify(engines['A'])['valid'])
    r=c.post('/api/v1/agent-runs',json={});self.assertEqual(r.status_code,201,r.text);value=r.json();self.assertEqual(value['status'],'awaiting_approval',r.text);self.assertIn('batches',value['results']['data']);tid=value['task_id']
    self.assertEqual(c.post('/api/v1/agent-runs/'+tid+'/review',json=dict(decision='approved',reason='reviewed')).status_code,403)
    self.assertEqual(c.post('/api/v1/agent-runs/'+tid+'/review',json=dict(decision='approved',reason='reviewed'),headers={'actor':'reviewer'}).status_code,200)
    self.assertEqual(c.get('/api/v1/agent-runs/'+tid,headers={'org':'B'}).status_code,404)
    r=c.post('/api/v1/agent-runs/'+tid+'/resume');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'completed');self.assertIn('evidence',r.json()['results']['report']);self.assertTrue(all(x['status']=='reused' for x in r.json()['trace'][:4]),r.text)
   for e in engines.values():e.dispose()
if __name__=='__main__':unittest.main()
