import unittest,io
from pathlib import Path
import test_identity as fixture
class DepartmentRevokeQA(unittest.TestCase):
 def setUp(self):self.f=fixture.IdentityTests();self.f.setUp();self.addCleanup(self.f.tearDown)
 def load(self,year,amount,currency='CNY'):
  import app,identity
  db=identity.tenant_engine(self.f.a['id']);key=f'{year}-{currency}'
  rows=[dict(posting_date=f'{year}-01-06',voucher_no=key,line_no=str(i),account_code=code,department_code='D01',currency=currency,debit=amount if i==1 else '0',credit=amount if i==2 else '0') for i,code in ((1,'6602'),(2,'1002'))]
  b=app.ingest(db,rows,key,key,kind='simulated');self.assertEqual(b['accepted_rows'],2);return b['batch_id']
 def test_department_exact_yoy_authorization(self):
  c=self.f.client;self.assertEqual(c.get('/api/v1/finance/departments').status_code,401)
  old=self.load(2025,'0.20');new=self.load(2026,'0.30');self.load(2026,'888','USD');self.f.login('reader-a')
  params=dict(start_period='2026-01',end_period='2026-01',currency='CNY',metric='expense');r=c.get('/api/v1/finance/departments',params=params);self.assertEqual(r.status_code,200,r.text);row=r.json()['rows'][0]
  self.assertEqual((row['amount'],row['prior_amount'],row['yoy']),('0.30','0.20','0.5'));self.assertEqual(row['batch_ids'],[new]);self.assertEqual(row['prior_batch_ids'],[old]);self.assertEqual(row['data_kind'],['simulated'])
  self.f.login('admin-b');self.assertEqual(c.get('/api/v1/finance/departments',params=params).json()['rows'],[])
 def test_theme_revoke_preserves_source_and_blocks_restore(self):
  f=self.f;c=f.client;raw=(fixture.r/'data_platform/theme_templates/budget.csv').read_bytes();path='/api/v1/theme-imports/budget/preview'
  f.login('reader-a');self.assertEqual(c.post(path,files={'file':('qa.csv',raw)}).status_code,403)
  f.login('admin-a');r=c.post(path,files={'file':('qa.csv',raw)},data={'data_kind':'simulated'});self.assertEqual(r.status_code,201,r.text);base='/api/v1/theme-imports/'+r.json()['preview_id'];self.assertEqual(c.post(base+'/confirm').status_code,200)
  f.login('admin-b');self.assertEqual(c.post(base+'/revoke',json={'reason':'qa review'}).status_code,404)
  f.login('admin-a');self.assertEqual(c.post(base+'/revoke',json={'reason':'qa review'}).json()['status'],'revoked');self.assertEqual(c.post(base+'/revoke',json={'reason':'qa review'}).json()['status'],'revoked');self.assertEqual(c.get(base+'/source').content,raw);self.assertEqual(c.post(base+'/confirm').status_code,409);self.assertEqual(c.get(base).json()['status'],'revoked')
if __name__=='__main__':unittest.main(verbosity=2)

