import os,sys,tempfile,unittest,csv,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import app as core,warehouse
from fastapi.testclient import TestClient
@unittest.skipUnless(os.getenv('FINAGENT_WAREHOUSE_URL'),'requires isolated PostgreSQL acceptance runner')
class WarehouseTests(unittest.TestCase):
 def test_actual_publish_query_and_scope(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'work') as d:
   core.app.state.db=core.engine('sqlite:///'+str(Path(d)/'source.sqlite'));client=TestClient(core.app)
   data=(ROOT/'data_platform/sample_vouchers.csv').read_bytes();rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))));batch=core.ingest(core.current_db(),rows,'warehouse-http-test','sample.csv',kind='simulated')
   try:
    res=client.post('/api/v1/warehouse/publish/'+batch['batch_id']);self.assertEqual(res.status_code,200,res.text);self.assertEqual(res.json()['status'],'published')
    self.assertEqual(client.post('/api/v1/warehouse/publish/'+batch['batch_id']).json()['status'],'already_published')
    result=client.get('/api/v1/warehouse/metrics');self.assertEqual(result.status_code,200,result.text);self.assertEqual(len(result.json()),12);self.assertEqual(result.json()[0]['revenue'],'107500.00');self.assertEqual(result.json()[0]['operating_profit'],'29500.00')
    marker=core.request_organization.set('other-test-organization')
    try:self.assertEqual(warehouse.metrics(),[])
    finally:core.request_organization.reset(marker)
   finally:client.close();core.app.state.db.dispose()
if __name__=='__main__':unittest.main(verbosity=2)
