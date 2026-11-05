import sys,tempfile,unittest,sqlite3,csv,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import app as core,connectors,financial_statements
from fastapi.testclient import TestClient
class IntegrationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');core.app.state.db=core.engine('sqlite:///'+str(Path(self.tmp.name)/'main.db'));self.client=TestClient(core.app)
 def tearDown(self):self.client.close();core.app.state.db.dispose();self.tmp.cleanup()
 def test_connector_bounds_and_replay(self):
  path=connectors.zone()/('acceptance-'+core.uid()+'.sqlite')
  try:
   with sqlite3.connect(path) as c:
    c.execute('CREATE TABLE journal('+','.join(x+' TEXT' for x in core.FIELDS)+')');data=list(csv.DictReader(io.StringIO((ROOT/'data_platform/sample_vouchers.csv').read_text(encoding='utf-8-sig'))));c.executemany('INSERT INTO journal VALUES(?,?,?,?,?,?,?,?)',[[r[k] for k in core.FIELDS] for r in data])
   c.close()
   created=self.client.post('/api/v1/connectors',json={'name':'模拟凭证源','kind':'sqlite_journal','relative_path':path.name,'table_name':'journal'});self.assertEqual(created.status_code,201,created.text);sid=created.json()['id']
   a=self.client.post('/api/v1/connectors/'+sid+'/run');self.assertEqual(a.status_code,200,a.text);self.assertEqual(a.json()['accepted_rows'],72);self.assertEqual(self.client.post('/api/v1/connectors/'+sid+'/run').json()['batch_id'],a.json()['batch_id'])
   self.assertEqual(self.client.post('/api/v1/connectors',json={'name':'escape','relative_path':'../../.env','table_name':'journal'}).status_code,422)
   self.assertEqual(self.client.post('/api/v1/connectors',json={'name':'inject','relative_path':path.name,'table_name':'journal;DELETE'}).status_code,422)
  finally:path.unlink(missing_ok=True)
 def test_income_and_balance(self):
  data=list(csv.DictReader(io.StringIO((ROOT/'data_platform/sample_vouchers.csv').read_text(encoding='utf-8-sig'))));core.ingest(core.current_db(),data,'financial','sample',kind='simulated')
  self.assertEqual(self.client.get('/api/v1/finance/statements/balance?as_of=2026-01-31').status_code,422)
  for code,d,c in [('1002','10000','0'),('4001','0','10000')]:self.assertEqual(self.client.post('/api/v1/finance/opening-balances',json={'account_code':code,'as_of':'2026-01-01','debit':d,'credit':c,'source_reference':'模拟期初','data_kind':'simulated'}).status_code,201)
  result=self.client.get('/api/v1/finance/statements/balance?as_of=2026-01-31').json();self.assertTrue(result['balanced']);self.assertEqual(result['assets'],'39500.00');self.assertEqual(result['data_kind'],['simulated'])
  profit=self.client.get('/api/v1/finance/statements/income?start_date=2026-01-01&end_date=2026-01-31').json();self.assertEqual(profit['operating_profit'],'29500.00');self.assertEqual(profit['completeness'],'unverified')
 def test_bank_balance_worksheet(self):
  body={'external_id':'recon1','as_of':'2026-01-31','bank_closing':'1000','book_closing':'900','outstanding_payments':'100','source_reference':'模拟银行与账簿','data_kind':'simulated'}
  result=self.client.post('/api/v1/finance/bank-balance-reconciliation',json=body);self.assertEqual(result.status_code,200,result.text);self.assertTrue(result.json()['balanced']);self.assertEqual(result.json()['difference'],'0.00')
 def test_sales_refunds(self):
  sale={'external_id':'invoice1','posting_date':'2026-01-01','customer':'模拟客户','product':'模拟产品','amount':'100.00','data_kind':'simulated'}
  self.assertEqual(self.client.post('/api/v1/sales',json=sale).status_code,201)
  self.client.post('/api/v1/sales',json={**sale,'external_id':'refund1','direction':'refund','amount':'20'})
  self.assertEqual(self.client.get('/api/v1/sales/summary').json()['rows'][0]['net_sales'],'80.00')
  self.assertEqual(self.client.post('/api/v1/sales',json={**sale,'amount':'101'}).status_code,409)
if __name__=='__main__':unittest.main(verbosity=2)
