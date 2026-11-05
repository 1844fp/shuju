import sys,unittest,hashlib,csv,io
from pathlib import Path
r=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(r.parents[1]/'work/runtime'));sys.path.insert(0,str(r/'backend'))
import app
from fastapi.testclient import TestClient
class FinanceTests(unittest.TestCase):
 def setUp(self):
  from sqlalchemy.pool import StaticPool
  from sqlalchemy import create_engine
  self.e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);app.meta.create_all(self.e);app.app.state.db=self.e;self.client=TestClient(app.app)
  self.data=(r/'data_platform/sample_vouchers.csv').read_bytes();self.rows=list(csv.DictReader(io.StringIO(self.data.decode('utf-8-sig'))))
 def tearDown(self):
  self.client.close();self.e.dispose()
 def load(self,rows=None,digest='test'):return app.ingest(self.e,rows or self.rows,digest,'sample.csv',kind='simulated')
 def test_financial_totals(self):
  b=self.load();self.assertEqual(b['accepted_rows'],72);d=app.metrics(self.e);self.assertEqual(len(d),12);self.assertEqual(d[0]['revenue'],'107500.00');self.assertEqual(d[0]['operating_profit'],'29500.00')
 def test_idempotency_and_business_duplicates(self):
  a=self.load();self.assertEqual(self.load()['batch_id'],a['batch_id']);b=self.load(digest='other');self.assertEqual(b['accepted_rows'],0);self.assertEqual(len(app.metrics(self.e)),12)
 def test_voucher_atomicity(self):
  rows=self.rows[:2];rows[0]['credit']='1';b=self.load(rows);self.assertEqual(b['accepted_rows'],0);self.assertEqual(b['rejected_rows'],2)
 def test_unknown_and_precision(self):
  for field,value in [('account_code','bad'),('credit','NaN'),('credit','0.001')]:
   rows=[dict(x) for x in self.rows[:2]];rows[0][field]=value;b=self.load(rows,digest=field+value);self.assertEqual(b['accepted_rows'],0)
 def test_zero_and_currency(self):
  self.load(self.rows[2:4]);self.assertIsNone(app.metrics(self.e)[0]['gross_margin']);self.assertEqual(app.metrics(self.e,currency='USD'),[])
 def test_api_flow(self):
  p=self.client.post('/api/v1/imports/preview',files={'file':('demo.csv',self.data,'text/csv')});self.assertEqual(p.status_code,200)
  b=self.client.post('/api/v1/imports',json={'preview_id':p.json()['preview_id']});self.assertEqual(b.status_code,202);self.assertEqual(b.json()['accepted_rows'],72)
  self.assertEqual(self.client.get('/api/v1/metrics/finance').json()[0]['revenue'],'107500.00')
  self.assertIn(b.json()['batch_id'],self.client.get('/api/v1/reports').text)
  self.assertEqual(self.client.post('/api/v1/analysis').status_code,503)
 def test_input_and_origin(self):
  self.assertEqual(self.client.post('/api/v1/imports/preview',files={'file':('bad.xlsm',b'bad')}).status_code,422)
  self.assertEqual(self.client.get('/api/v1/metrics/finance?start_period=bad').status_code,422)
  self.assertEqual(self.client.post('/api/v1/imports',json={'preview_id':'x'},headers={'origin':'https://example.com'}).status_code,403)
 def test_excel(self):
  import openpyxl
  w=openpyxl.Workbook();s=w.active;s.append(app.FIELDS)
  for row in self.rows[:2]:s.append([row[k] for k in app.FIELDS])
  buf=io.BytesIO();w.save(buf)
  p=self.client.post('/api/v1/imports/preview',files={'file':('sample.xlsx',buf.getvalue())});self.assertEqual(p.status_code,200)
if __name__=='__main__':unittest.main(verbosity=2)
