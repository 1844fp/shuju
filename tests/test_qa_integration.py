import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from test_finance import FinanceTests
import app

class QAIntegration(FinanceTests):
 def test_decimal_boundary(self):
  self.assertEqual(app.cents('999999999999.99'),99999999999999)
  self.assertEqual(app.cents('0.10')+app.cents('0.20'),30)
  for value in ['-1','Infinity','0.001','1000000000000.00']:
   with self.assertRaises(ValueError): app.cents(value)
 def test_input_limits(self):
  for name,data,status in [('empty.csv',b'',422),('bad.csv',b'\xff',422),('huge.csv',b'x'*10485761,413)]:
   self.assertEqual(self.client.post('/api/v1/imports/preview',files={'file':(name,data)}).status_code,status)
 def test_host_and_origin_permissions(self):
  self.assertEqual(self.client.get('/api/v1/imports',headers={'host':'evil.example'}).status_code,403)
  self.assertEqual(self.client.get('/api/v1/imports',headers={'origin':'https://evil.example'}).status_code,403)
 def test_missing_resource_and_readiness(self):
  self.assertEqual(self.client.get('/api/v1/ready').status_code,200)
  self.assertEqual(self.client.get('/api/v1/imports/missing').status_code,404)
 def test_corrupt_excel(self):
  response=self.client.post('/api/v1/imports/preview',files={'file':('bad.xlsx',b'not-a-zip')})
  self.assertEqual(response.status_code,422)

if __name__=='__main__': unittest.main(verbosity=2)
