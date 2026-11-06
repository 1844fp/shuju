"""Accepted balanced journal facts, exact sums, scopes and missing mappings."""
import unittest,tempfile
from pathlib import Path
import app as core,finance_query
from fastapi import FastAPI
from fastapi.testclient import TestClient
class AmountQueryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='work');self.dbs={k:core.engine('sqlite:///'+str(Path(self.tmp.name).resolve()/(k+'.sqlite'))) for k in ('A','B')}
  a=FastAPI();finance_query.install(a)
  @a.middleware('http')
  async def scope(r,call):
   token=core.request_database.set(self.dbs[r.headers.get('org','A')])
   try:return await call(r)
   finally:core.request_database.reset(token)
  self.c=TestClient(a)
 def tearDown(self):
  self.c.close()
  for db in self.dbs.values():db.dispose()
  self.tmp.cleanup()
 def load(self,org,month,department,amount,currency='CNY',code='6601',reverse=False):
  key=f'{org}-{month}-{department}-{currency}-{code}-{amount}-{reverse}'
  rows=[]
  for n,account in enumerate((code,'1002'),1):
   debit=(n==1)!=reverse
   rows.append(dict(posting_date='2026-'+month+'-06',voucher_no=key,line_no=str(n),account_code=account,department_code=department,currency=currency,debit=amount if debit else '0',credit='0' if debit else amount))
  result=core.ingest(self.dbs[org],rows,key,key,kind='simulated',account_catalog={code:'expense','1002':'asset'})
  self.assertEqual(result['accepted_rows'],2);return result['batch_id']
 def query(self,text='查询2026年第三季度费用最高的五个部门',**kw):return self.c.get('/api/v1/finance-query',params={'q':text,**kw})
 def test_exact_quarter_department_currency_and_org(self):
  bids=[self.load('A','07','D1','0.10'),self.load('A','08','D1','0.20'),self.load('A','09','D1','0.01',reverse=True)]
  self.load('A','09','D2','0.29');self.load('A','06','D1','999');self.load('A','07','D1','888','USD');self.load('B','07','D1','777')
  response=self.query();self.assertEqual(response.status_code,200,response.text);rows=response.json()['rows']
  self.assertEqual([(r['department'],r['amount']) for r in rows],[('D1','0.29'),('D2','0.29')]);self.assertEqual(rows[0]['batch_ids'],sorted(bids));self.assertEqual(rows[0]['data_kind'],['simulated'])
  self.assertEqual(self.query(currency='USD').json()['rows'][0]['amount'],'888.00')
  self.assertEqual(self.c.get('/api/v1/finance-query',params={'q':'查询2026年第三季度费用最高的五个部门'},headers={'org':'B'}).json()['rows'][0]['amount'],'777.00')
  self.assertEqual(self.query('查询2026年8月费用最高的五个部门').json()['rows'][0]['amount'],'0.20')
 def test_selling_mapping_missing_refuses(self):
  self.load('A','07','D1','100',code='CUSTOM_EXPENSE')
  r=self.query('查询2026年第三季度销售费用最高的五个部门');self.assertEqual(r.status_code,422,r.text);self.assertIn('CUSTOM_EXPENSE',r.text)
 def test_selling_explicit_mapping_excludes_management(self):
  self.load('A','07','D1','10.01');self.load('A','08','D1','900',code='6602')
  r=self.query('查询2026年第三季度销售费用最高的五个部门');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['rows'][0]['amount'],'10.01');self.assertEqual(r.json()['rows'][0]['account_codes'],['6601'])
if __name__=='__main__':unittest.main(verbosity=2)
