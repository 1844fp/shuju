import json,os,unittest
from pathlib import Path
from unittest.mock import patch
import test_erp_imports as fixtures
import app as core
import enterprise_controls as controls
from sqlalchemy import select

class EnterpriseTests(unittest.TestCase):
 def setUp(self):
  fixtures.ERPTests.setUp(self);core.app.state.tenant_root=Path(self.tmp.name)/'tenants'
 def tearDown(self):
  import identity
  for path,e in identity.engines.items():
   if self.tmp.name in path:e.dispose()
  fixtures.ERPTests.tearDown(self)
 preview=fixtures.ERPTests.preview
 clean=fixtures.ERPTests.clean
 commit=fixtures.ERPTests.commit
 csv=fixtures.ERPTests.csv
 rows=fixtures.ERPTests.rows
 def test_custom_account_statement_requires_explicit_mapping(self):
  self.client.post('/api/v1/erp/accounts',json=dict(approved=True,accounts=[dict(code='REV.CUSTOM',name='企业收入',category='revenue')]))
  rows=self.rows();rows[1]['account_code']='REV.CUSTOM';value=self.clean(self.preview(self.csv(rows)));self.assertEqual(self.commit(value).status_code,200)
  # An unmapped statement line must be a controlled rejection, never a KeyError/500.
  response=self.client.get('/api/v1/finance/statements/income?start_date=2026-01-01&end_date=2026-12-31')
  self.assertEqual(response.status_code,422,response.text)
  mapped=self.client.post('/api/v1/finance/statements/mappings',json=dict(reason='财务核准收入报表项目',mappings=[dict(code='REV.CUSTOM',line='revenue')]))
  self.assertEqual(mapped.status_code,200,mapped.text)
  result=self.client.get('/api/v1/finance/statements/income?start_date=2026-01-01&end_date=2026-12-31').json()
  self.assertEqual(result['lines']['revenue'],'100.30');self.assertEqual(len(result['mapping_version']),64)
  self.assertEqual(self.client.post('/api/v1/finance/statements/mappings',json=dict(reason='禁止类别不相容',mappings=[dict(code='REV.CUSTOM',line='income_tax')])).status_code,422)
 def test_period_close_blocks_all_financial_data_inputs(self):
  first=self.clean(self.preview(self.csv(self.rows('001'))));self.assertEqual(self.commit(first).status_code,200)
  close=self.client.post('/api/v1/enterprise/periods/2026-01/close',json=dict(expected_version=0,reason='月度数据复核锁定'))
  self.assertEqual(close.status_code,200,close.text)
  # Replays are read-only and remain valid; new or modified data cannot enter the closed period.
  self.assertEqual(self.commit(first).status_code,200)
  second=self.clean(self.preview(self.csv(self.rows('002'))));self.assertEqual(self.commit(second).status_code,409)
  self.assertEqual(self.client.post('/api/v1/finance/registers',json=dict(external_id='closed',kind='budget',period='2026-01',department='D01',amount='1')).status_code,409)
  self.assertEqual(self.client.post('/api/v1/bank/transactions',json=dict(external_id='closed',posting_date='2026-01-31',reference='closed',inflow='1')).status_code,409)
  self.assertEqual(self.client.post('/api/v1/sales',json=dict(external_id='closed',posting_date='2026-01-31',customer='C',product='P',amount='1')).status_code,409)
  self.assertEqual(self.client.post('/api/v1/finance/opening-balances',json=dict(account_code='1002',as_of='2026-01-01',debit='1',source_reference='fixture')).status_code,409)
  self.assertEqual(self.client.post('/api/v1/enterprise/periods/2026-01/reopen',json=dict(expected_version=0,reason='旧版本不能覆盖')).status_code,409)
  reopened=self.client.post('/api/v1/enterprise/periods/2026-01/reopen',json=dict(expected_version=1,reason='财务复核后重新开放'))
  self.assertEqual(reopened.status_code,200,reopened.text);self.assertEqual(self.commit(second).status_code,200)
  self.assertEqual(self.client.get('/api/v1/metrics/finance').json()[0]['revenue'],'200.60')
  self.assertTrue(self.client.get('/api/v1/enterprise/audit/verify').json()['valid'])
 def users(self):
  import identity
  org=identity.create_org('Enterprise A');other=identity.create_org('Enterprise B');password='Controls-test-only-123'
  for name,target,role in [('maker',org,'org_admin'),('reviewer',org,'org_admin'),('foreign',other,'org_admin'),('reader',org,'reader')]:identity.create_user(name,password,target['id'],role)
  return password
 def login(self,name,password):
  self.client.cookies.clear();result=self.client.post('/api/v1/auth/login',json=dict(username=name,password=password));self.assertEqual(result.status_code,200,result.text)
 def test_maker_checker_and_legacy_bypass_denied(self):
  password=self.users()
  with patch.dict(os.environ,{'FINAGENT_AUTH_MODE':'users','FINAGENT_ERP_APPROVAL_REQUIRED':'1'}):
   self.login('maker',password);value=self.clean(self.preview(self.csv(self.rows())))
   self.assertEqual(self.commit(value).status_code,409)
   approval=self.client.post('/api/v1/erp/runs/'+value['id']+'/request-approval');self.assertEqual(approval.status_code,201,approval.text);aid=approval.json()['id']
   self.assertEqual(self.client.post('/api/v1/enterprise/approvals/'+aid+'/review',json=dict(decision='approved',reason='不能自行批准')).status_code,403)
   original=self.client.post('/api/v1/imports/preview',files={'file':('direct.csv',self.csv(self.rows('BYPASS')))}).json()
   self.assertEqual(self.client.post('/api/v1/imports',json=dict(preview_id=original['preview_id'])).status_code,409)
   self.login('foreign',password);self.assertEqual(self.client.post('/api/v1/enterprise/approvals/'+aid+'/review',json=dict(decision='approved',reason='其他组织不可访问')).status_code,404)
   self.login('reader',password);self.assertEqual(self.client.post('/api/v1/enterprise/periods/2026-01/close',json=dict(expected_version=0,reason='只读不可关期')).status_code,403)
   self.login('reviewer',password);response=self.client.post('/api/v1/enterprise/approvals/'+aid+'/review',json=dict(decision='approved',reason='独立复核凭证与来源'))
   self.assertEqual(response.status_code,200,response.text);self.assertEqual(self.commit(value).status_code,200)
   self.assertTrue(self.client.get('/api/v1/enterprise/audit/verify').json()['valid'])
 def test_review_binds_the_actual_cleaned_snapshot(self):
  import erp_imports
  password=self.users()
  with patch.dict(os.environ,{'FINAGENT_AUTH_MODE':'users','FINAGENT_ERP_APPROVAL_REQUIRED':'1'}):
   self.login('maker',password);value=self.clean(self.preview(self.csv(self.rows())))
   approval=self.client.post('/api/v1/erp/runs/'+value['id']+'/request-approval').json()
   self.login('reviewer',password);self.assertEqual(self.client.post('/api/v1/enterprise/approvals/'+approval['id']+'/review',json=dict(decision='approved',reason='首次复核通过')).status_code,200)
   # Simulate privileged storage tampering to test snapshot binding, not a public edit API.
   organization=core.request_organization.set(response_org(self.client));import identity
   database=identity.tenant_engine(response_org(self.client));token=core.request_database.set(database)
   try:
    changed=erp_imports.get(value['id']);changed['cleaned_rows'][0]['normalized']['debit']='999.00';erp_imports.save(changed)
   finally:core.request_database.reset(token);core.request_organization.reset(organization)
   self.assertEqual(self.commit(value).status_code,409)
 def test_local_audit_chain_detects_modified_event(self):
  self.client.post('/api/v1/enterprise/periods/2026-02/close',json=dict(expected_version=0,reason='审计验证样本'))
  self.assertTrue(controls.verify(core.current_db())['valid'])
  with core.current_db().begin() as c:c.execute(controls.EVENTS.update().values(payload='modified'))
  self.assertFalse(controls.verify(core.current_db())['valid'])

def response_org(client):return client.get('/api/v1/auth/me').json()['organization_id']

if __name__=='__main__':unittest.main()
