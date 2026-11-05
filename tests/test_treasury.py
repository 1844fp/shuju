import sys,tempfile,unittest,csv,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import app as core,treasury
from fastapi.testclient import TestClient
class TreasuryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');core.app.state.db=core.engine('sqlite:///'+str(Path(self.tmp.name)/'bank.db'));self.client=TestClient(core.app)
 def tearDown(self):self.client.close();core.app.state.db.dispose();self.tmp.cleanup()
 def transaction(self,**kw):
  return self.client.post('/api/v1/bank/transactions',json={'external_id':'b1','posting_date':'2026-01-01','reference':'DEMO-01-R','inflow':'107500','data_kind':'simulated',**kw})
 def load(self,source='local'):
  data=(ROOT/'data_platform/sample_vouchers.csv').read_text(encoding='utf-8-sig');return core.ingest(core.current_db(),list(csv.DictReader(io.StringIO(data))),'sample-'+source,'sample.csv',source_system=source,kind='simulated')
 def test_exact_match_and_ambiguous(self):
  self.load();first=self.transaction();self.assertEqual(first.status_code,201,first.text)
  exact=self.client.get('/api/v1/bank/reconcile').json();self.assertEqual(len(exact['matches']),1);self.assertTrue(exact['matches'][0]['ledger']['batch_ids'])
  self.transaction(external_id='b2');result=self.client.get('/api/v1/bank/reconcile').json();self.assertEqual(len(result['matches']),0);self.assertEqual(len(result['ambiguous']),1)
 def test_multiple_source_ledger_ambiguous(self):
  self.load('a');self.load('b');self.transaction();result=self.client.get('/api/v1/bank/reconcile').json();self.assertEqual(len(result['ambiguous']),1)
 def test_cashflow_and_forecast(self):
  for n in (1,2,3):self.transaction(external_id='m'+str(n),posting_date=f'2026-{n:02}-01',inflow=str(n*100),category='operating')
  result=self.client.get('/api/v1/finance/cashflow').json();self.assertEqual(result['rows'][0]['net'],'100.00')
  prediction=self.client.get('/api/v1/finance/cashflow/forecast?history_end=2026-03&months=2').json();self.assertEqual(prediction['rows'][0],{'period':'2026-04','forecast_net':'200.00'});self.assertTrue(prediction['scenario_only']);self.assertEqual(len(prediction['sources']),3)
  self.assertEqual(self.client.get('/api/v1/finance/cashflow/forecast?history_end=2026-04').json()['rows'],[])
 def test_idempotency_validation_scope(self):
  a=self.transaction();self.assertEqual(self.transaction(inflow='107500.00').json()['id'],a.json()['id']);self.assertEqual(self.transaction(inflow='1').status_code,409)
  self.assertEqual(self.transaction(external_id='bad',outflow='1').status_code,422);self.assertEqual(self.transaction(external_id='bad',inflow='0.001').status_code,422)
  self.assertEqual(self.transaction(external_id='bad',account='another-account').status_code,422)
  other=core.engine('sqlite:///'+str(Path(self.tmp.name)/'other.db'));marker=core.request_database.set(other)
  try:self.assertEqual(treasury.rows(),[])
  finally:core.request_database.reset(marker);other.dispose()
if __name__=='__main__':unittest.main(verbosity=2)
