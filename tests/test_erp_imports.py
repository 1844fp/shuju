import csv,io,json,os,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import app as core,erp_imports as etl,erp_database as sources
from fastapi.testclient import TestClient
from sqlalchemy import select

class ERPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');self.env=patch.dict(os.environ,{'FINAGENT_AUTH_MODE':'demo'});self.env.start()
  core.app.state.db=core.engine('sqlite:///'+str(Path(self.tmp.name)/'control.sqlite'));self.client=TestClient(core.app)
 def tearDown(self):self.client.close();core.app.state.db.dispose();self.env.stop();self.tmp.cleanup()
 def preview(self,content,name='data.csv',profile='generic',ledger='BOOK01',**extra):
  r=self.client.post('/api/v1/erp/preview',files={'file':(name,content)},data=dict(profile=profile,ledger_id=ledger,**extra));self.assertEqual(r.status_code,201,r.text);return r.json()
 def clean(self,v,**options):
  options.setdefault('data_kind','simulated')
  r=self.client.post('/api/v1/erp/runs/'+v['id']+'/clean',json=options);self.assertEqual(r.status_code,200,r.text);return r.json()
 def commit(self,v,ack=False):return self.client.post('/api/v1/erp/runs/'+v['id']+'/commit',json=dict(cleaning_token=v['cleaning_token'],acknowledge_quarantine=ack))
 def csv(self,rows,fields=None,encoding='utf-8-sig'):
  out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows);return out.getvalue().encode(encoding)
 def rows(self,number='001',when='2026-01-31',value='100.30'):
  return [dict(posting_date=when,voucher_no=number,line_no=str(i),account_code=account,department_code='D01',currency='CNY',debit=d,credit=c) for i,account,d,c in [(1,'1002',value,'0'),(2,'6001','0',value)]]
 def test_all_vendor_templates_roundtrip(self):
  for profile in etl.PROFILES:
   with self.subTest(profile=profile):
    data=self.client.get('/api/v1/erp/templates/'+profile).content;v=self.clean(self.preview(data,profile=profile));self.assertEqual(v['quality']['valid_rows'],2);self.assertEqual(v['quality']['data_kind'],'simulated')
    result=self.commit(v);self.assertEqual(result.status_code,200,result.text)
    # Different templates describe the same business voucher, so only the first can count.
  self.assertEqual(self.client.get('/api/v1/metrics/finance').json()[0]['revenue'],'100.00')
 def test_exact_cleaning_raw_retained_and_monthly_identity(self):
  rows=self.rows(value=' １,２３４.５０ ')+self.rows(when='2026-02-28',value='1234.50')
  rows[0]['currency']='人民币';rows[1]['currency']='人民币'
  content=self.csv(rows);v=self.clean(self.preview(content));self.assertEqual(v['quality']['valid_rows'],4)
  self.assertEqual(v['quality']['totals']['CNY']['debit'],'2469.00');r=self.commit(v);self.assertEqual(r.status_code,200,r.text)
  metrics=self.client.get('/api/v1/metrics/finance').json();self.assertEqual([r['revenue'] for r in metrics],['1234.50','1234.50'])
  with core.app.state.db.connect() as c:self.assertEqual(c.execute(select(etl.FILES.c.content)).scalar(),content)
  replay=self.commit(v);self.assertEqual(replay.json()['batch']['batch_id'],r.json()['batch']['batch_id'])
 def test_quarantine_atomic_and_explicit_acknowledgment(self):
  rows=self.rows()+self.rows('002');rows[2]['account_code']='9999'
  v=self.clean(self.preview(self.csv(rows)));self.assertEqual(v['quality']['valid_rows'],2);self.assertEqual(v['quality']['quarantined_rows'],2)
  self.assertEqual(self.commit(v).status_code,409);result=self.commit(v,True);self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['batch']['accepted_rows'],2)
  self.assertIn('9999',self.client.get('/api/v1/erp/runs/'+v['id']+'/errors.csv').text)
 def test_red_entries_and_direction_modes(self):
  v=self.clean(self.preview(self.csv(self.rows(value='(100.30)'))));self.assertEqual(self.commit(v).status_code,200)
  self.assertEqual(self.client.get('/api/v1/metrics/finance').json()[0]['revenue'],'-100.30')
  rows=[dict(posting_date='2026-02-28',voucher_no='002',line_no=str(i),account_code=account,currency='USD',amount=a,direction=direction) for i,account,a,direction in [(1,'1002','10.00','S'),(2,'6001','-10.00','H')]]
  v=self.clean(self.preview(self.csv(rows)),amount_mode='absolute_by_direction');self.assertEqual(v['quality']['valid_rows'],2)
 def test_mapping_currency_and_precision_fail_closed(self):
  rows=self.rows();rows[0]['account_code']='BANK';rows[1]['account_code']='SALES';rows[0]['currency']='';rows[1]['currency']=''
  v=self.clean(self.preview(self.csv(rows)),account_map={'BANK':'1002','SALES':'6001'},default_currency='CNY');self.assertEqual(v['quality']['valid_rows'],2)
  for invalid in ('1,23.00','0.001','NaN','1e2','$100.30'):
   rows=self.rows(value=invalid);v=self.clean(self.preview(self.csv(rows)));self.assertEqual(v['quality']['quarantined_rows'],2,invalid)
 def test_changed_configuration_and_ledger_refused(self):
  data=self.csv(self.rows());v=self.clean(self.preview(data));self.assertEqual(self.commit(v).status_code,200)
  changed=self.clean(self.preview(data),default_department='OTHER');self.assertEqual(self.commit(changed).status_code,409)
  other=self.clean(self.preview(self.csv(self.rows('002')),ledger='BOOK02'));self.assertEqual(self.commit(other).status_code,409)
 def test_missing_voucher_category_cannot_duplicate_known_category(self):
  data=self.rows();first=self.clean(self.preview(self.csv(data)));self.assertEqual(self.commit(first).status_code,200)
  for row in data:row['voucher_type']='记'
  second=self.clean(self.preview(self.csv(data)));self.assertEqual(self.commit(second).status_code,409)
  self.assertEqual(self.client.get('/api/v1/metrics/finance').json()[0]['revenue'],'100.30')
 def test_xlsx_header_numeric_and_formula(self):
  from openpyxl import Workbook
  workbook=Workbook();sheet=workbook.active;sheet.title='凭证';sheet.append(['模拟导出标题']);sheet.append(list(self.rows()[0]));
  for row in self.rows():sheet.append(list(row.values()))
  sheet['G3']=1234.56;sheet['H4']=1234.56
  out=io.BytesIO();workbook.save(out);v=self.clean(self.preview(out.getvalue(),'test.xlsx'));self.assertEqual(v['parser']['header_row'],2);self.assertEqual(v['quality']['totals']['CNY']['debit'],'1234.56')
  sheet['G3']='=1+2';out=io.BytesIO();workbook.save(out);v=self.clean(self.preview(out.getvalue(),'formula.xlsx'));self.assertEqual(v['quality']['quarantined_rows'],2)
  workbook.close()
 def test_gb18030_summary_and_duplicate_headers(self):
  rows=[dict(日期=r['posting_date'],凭证号=r['voucher_no'],行号=r['line_no'],科目代码=r['account_code'],币别='人民币',借方=r['debit'],贷方=r['credit']) for r in self.rows()]
  rows.append(dict.fromkeys(rows[0],''));rows[-1]['日期']='合计'
  v=self.clean(self.preview(self.csv(rows,encoding='gb18030')));self.assertEqual(v['quality']['valid_rows'],2);self.assertEqual(v['quality']['excluded_rows'],1)
  bad=self.client.post('/api/v1/erp/preview',files={'file':('bad.csv',b'date,date\na,b')},data={'ledger_id':'BOOK01','header_row':'1'});self.assertEqual(bad.status_code,422)
 def test_confirm_stale_token_missing_identity_and_unbalanced(self):
  rows=self.rows();rows[1]['credit']='90';v=self.clean(self.preview(self.csv(rows)));self.assertEqual(v['quality']['valid_rows'],0);self.assertEqual(self.commit(v).status_code,422)
  rows=self.rows();rows[0]['voucher_no']='';v=self.clean(self.preview(self.csv(rows)));self.assertTrue(v['quality']['commit_blocked'])
  v=self.clean(self.preview(self.csv(self.rows())));self.assertEqual(self.client.post('/api/v1/erp/runs/'+v['id']+'/commit',json={'cleaning_token':'old'}).status_code,409)
 def test_scope_and_source_ids_not_credentials(self):
  v=self.preview(self.csv(self.rows()));other=core.engine('sqlite:///'+str(Path(self.tmp.name)/'other.sqlite'));token=core.request_database.set(other)
  try:
   with self.assertRaises(Exception) as e:etl.get(v['id'])
   self.assertEqual(e.exception.status_code,404)
  finally:core.request_database.reset(token);other.dispose()
  self.assertEqual(self.client.post('/api/v1/erp/source-preview',json={'source_id':'x','ledger_id':'BOOK01','dsn':'secret'}).status_code,422)
  with patch.dict(os.environ,{'FINAGENT_ERP_SOURCES_JSON':json.dumps([dict(id='foreign',organization_id='other',ledger_id='BOOK01')])}):self.assertEqual(self.client.get('/api/v1/erp/sources').json(),[])
 def test_real_authentication_roles_and_tenant_isolation(self):
  import identity
  core.app.state.tenant_root=Path(self.tmp.name)/'tenants'
  a=identity.create_org('ERP-A');b=identity.create_org('ERP-B');password='ERP-fixture-only-123'
  identity.create_user('erp-admin-a',password,a['id'],'org_admin');identity.create_user('erp-reader-b',password,b['id'],'reader')
  try:
   with patch.dict(os.environ,{'FINAGENT_AUTH_MODE':'users'}):
    self.assertEqual(self.client.get('/api/v1/erp/runs').status_code,401)
    self.client.post('/api/v1/auth/login',json=dict(username='erp-admin-a',password=password));v=self.preview(self.csv(self.rows()));v=self.clean(v);self.assertEqual(self.commit(v).status_code,200)
    self.client.post('/api/v1/auth/logout');self.client.post('/api/v1/auth/login',json=dict(username='erp-reader-b',password=password))
    self.assertEqual(self.client.get('/api/v1/erp/runs/'+v['id']).status_code,404);self.assertEqual(self.client.get('/api/v1/erp/runs/'+v['id']+'/rows').status_code,404)
    self.assertEqual(self.client.get('/api/v1/erp/runs').json(),[])
    self.assertEqual(self.client.post('/api/v1/erp/source-preview',json=dict(source_id='x',profile='generic',ledger_id='BOOK01')).status_code,403)
  finally:
   for key,e in identity.engines.items():
    if str(self.tmp.name) in key:e.dispose()
 def test_explicit_mapping_clear_is_not_ignored(self):
  v=self.preview(self.csv(self.rows()));response=self.client.post('/api/v1/erp/runs/'+v['id']+'/clean',json={'mapping':{'debit':''}});self.assertEqual(response.status_code,422)
 def test_odata_iso_dates_and_non_summary_business_value(self):
  self.assertEqual(etl.day('/Date(0+0800)/'),'1970-01-01');self.assertEqual(etl.day('/Date(0-0800)/'),'1969-12-31');self.assertEqual(etl.day('2026-01-31T23:00:00+08:00'),'2026-01-31')
  rows=self.rows(number='Total');v=self.clean(self.preview(self.csv(rows)));self.assertEqual(v['quality']['valid_rows'],2)
 def test_approved_enterprise_account_codes_preserved(self):
  approved=self.client.post('/api/v1/erp/accounts',json=dict(approved=True,accounts=[dict(code='1405.01',name='库存商品',category='asset'),dict(code='2221.01',name='应交税费',category='liability')]))
  self.assertEqual(approved.status_code,200,approved.text)
  rows=self.rows();rows[0]['account_code']='1405.01';rows[1]['account_code']='2221.01'
  v=self.clean(self.preview(self.csv(rows)));self.assertEqual(v['quality']['valid_rows'],2);self.assertEqual(self.commit(v).status_code,200)
  with core.app.state.db.connect() as c:stored=[json.loads(x) for x in c.execute(select(core.facts.c.payload)).scalars()]
  self.assertEqual({r['account_code'] for r in stored},{'1405.01','2221.01'});self.assertEqual(self.client.get('/api/v1/metrics/finance').json()[0]['revenue'],'0.00')
 def test_chart_file_and_catalog_revision_guard(self):
  v=self.clean(self.preview(self.csv(self.rows())))
  chart='科目代码,科目名称,科目类别\n6601.001,销售费用明细,费用\n'
  result=self.client.post('/api/v1/erp/accounts/import',files={'file':('chart.csv',chart.encode('utf-8-sig'))},data={'approved':'true'})
  self.assertEqual(result.status_code,200,result.text);self.assertEqual(self.commit(v).status_code,409)
  conflict=self.client.post('/api/v1/erp/accounts',json=dict(approved=True,accounts=[dict(code='6601.001',name='重分类',category='revenue')]))
  self.assertEqual(conflict.status_code,409)
  invalid=self.client.post('/api/v1/erp/accounts/import',files={'file':('bad.csv','科目代码,科目名称,科目类别\n9999,未明确,损益\n'.encode())},data={'approved':'true'})
  self.assertEqual(invalid.status_code,422)
 def test_database_float_amount_is_quarantined(self):
  rows=self.rows();columns=list(rows[0]);records=[dict(row_number=i+1,values=row,cell_types={'debit':'database_float','credit':'database_float'}) for i,row in enumerate(rows)]
  value=etl.preview(b'float-db-test','fixture','generic','BOOK01',columns,records,{'kind':'database'})
  result=self.clean(value);self.assertEqual(result['quality']['quarantined_rows'],2)
 def test_erp_raw_and_receipts_survive_snapshot_restore(self):
  from infrastructure.recovery import snapshot,restore
  content=self.csv(self.rows());v=self.clean(self.preview(content));self.assertEqual(self.commit(v).status_code,200)
  root=Path(self.tmp.name);snapshot({'tenant':root/'control.sqlite'},root/'backup');restore(root/'backup',root/'restored')
  restored=core.engine('sqlite:///'+str(root/'restored/tenant.sqlite'))
  try:
   with restored.connect() as c:
    self.assertEqual(c.execute(select(etl.FILES.c.content)).scalar(),content);self.assertTrue(c.execute(select(etl.RECEIPTS.c.batch_id)).scalar())
    self.assertEqual(json.loads(c.execute(select(etl.RUNS.c.payload)).scalar())['status'],'committed')
   self.assertEqual(core.metrics(restored)[0]['revenue'],'100.30')
  finally:restored.dispose()

class ERPProtocolTests(unittest.TestCase):
 def setUp(self):
  self.requests=[];outer=self
  class Handler(BaseHTTPRequestHandler):
   def do_GET(self):
    outer.requests.append(('GET',self.path,self.headers.get('Authorization')))
    base='http://127.0.0.1:'+str(self.server.server_port)
    if self.path.startswith('/sap'):
     data={'d':{'results':[{'PostingDate':'2026-01-31','amount':10.30}]}}
     if 'page=2' not in self.path:data['d']['__next']=base+'/sap?page=2'
    elif self.path.startswith('/oracle'):data=dict(items=[{'line':2 if 'offset=1' in self.path else 1}],hasMore='offset=1' not in self.path)
    elif self.path.startswith('/escape'):data={'d':{'results':[{}],'__next':'https://invalid.example/steal'}}
    else:data=dict(items=[{}],hasMore=True)
    body=json.dumps(data).encode();self.send_response(200);self.end_headers();self.wfile.write(body)
   def do_POST(self):
    value=json.loads(self.rfile.read(int(self.headers['Content-Length'])));query=value['data'];query=json.loads(query) if isinstance(query,str) else query
    outer.requests.append(('POST',self.path,query['FormId']));self.send_response(200);self.end_headers();self.wfile.write(b'[["2026-01-31","001","1","1002","CNY","10.30","0.00"]]')
   def log_message(self,*args):pass
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start();self.base='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def test_sap_oracle_pagination_and_exact_numeric(self):
  cols,rows,info=sources.http_rows(dict(id='sap',kind='sap_odata',url=self.base+'/sap'));self.assertEqual(len(rows),2);self.assertEqual(rows[0]['values']['amount'],'10.3');self.assertEqual(len(info['_raw_pages_base64']),2)
  cols,rows,info=sources.http_rows(dict(id='oracle',kind='oracle_rest',url=self.base+'/oracle'));self.assertEqual([r['values']['line'] for r in rows],['1','2'])
 def test_kingdee_query_only(self):
  path='/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.ExecuteBillQuery.common.kdsvc';config=dict(id='kingdee',kind='kingdee_bill_query',url=self.base+path,columns=['FDate','FNumber','FEntryID','FAccountNumber','FCurrencyNumber','FDebit','FCredit'],query=dict(FormId='GL_VOUCHER',FieldKeys='FDate,FNumber',OrderString='FEntryID'))
  cols,rows,info=sources.http_rows(config);self.assertEqual(len(rows),1);self.assertEqual(self.requests[0][2],'GL_VOUCHER')
  with self.assertRaises(ValueError):sources.http_rows(config|{'url':self.base+'/Save'})
 def test_foreign_pagination_and_incomplete_generic_rejected(self):
  with self.assertRaises(ValueError):sources.http_rows(dict(id='escape',kind='sap_odata',url=self.base+'/escape'))
  self.assertEqual(len(self.requests),1)
  with self.assertRaises(ValueError):sources.http_rows(dict(id='generic',kind='rest_json',url=self.base+'/generic',rows_path='items'))

if __name__=='__main__':unittest.main()
