"""Real PostgreSQL SELECT-only ERP source through the HTTP ETL pipeline."""
import json,os,time
from pathlib import Path

def exercise(root,secret):
 import psycopg
 import app as core
 from fastapi.testclient import TestClient
 from sqlalchemy.engine import URL
 root=Path(root);base=root/'work/acceptance/erp';base.mkdir(parents=True,exist_ok=True)
 with psycopg.connect(host='127.0.0.1',port=55439,user='owner',password=secret,dbname='postgres') as c:
  c.execute('CREATE TABLE public.erp_fixture(dbill_date date, csign text, ino_id text, inid integer, ccode text, cdept_id text, cexch_name text, md numeric(20,2), mc numeric(20,2))')
  c.execute("INSERT INTO public.erp_fixture VALUES ('2026-01-31','记','001',1,'1002','D01','CNY',100.23,0),('2026-01-31','记','001',2,'6001','D01','CNY',0,100.23)")
  c.execute(psycopg.sql.SQL('CREATE ROLE erp_reader LOGIN PASSWORD {}').format(psycopg.sql.Literal(secret)))
  c.execute('GRANT USAGE ON SCHEMA public TO erp_reader');c.execute('GRANT SELECT ON public.erp_fixture TO erp_reader')
 dsn=URL.create('postgresql+psycopg',username='erp_reader',password=secret,host='127.0.0.1',port=55439,database='postgres').render_as_string(hide_password=False)
 os.environ['FINAGENT_ERP_DSN_ACCEPTANCE']=dsn
 os.environ['FINAGENT_ERP_SOURCES_JSON']=json.dumps([dict(id='pg-u8',name='isolated-U8-field-fixture',organization_id='local-demo',ledger_id='TESTBOOK',kind='database',dsn_env='FINAGENT_ERP_DSN_ACCEPTANCE',read_only_verified=True,schema='public',table='erp_fixture',columns=['dbill_date','csign','ino_id','inid','ccode','cdept_id','cexch_name','md','mc'],order_by=['dbill_date','ino_id','inid'])])
 os.environ['FINAGENT_AUTH_MODE']='demo'
 core.app.state.db=core.engine('sqlite:///'+str(base/('erp-'+str(time.time_ns())+'.sqlite')))
 checks=[]
 with TestClient(core.app) as client:
  response=client.post('/api/v1/erp/source-preview',json=dict(source_id='pg-u8',ledger_id='TESTBOOK',profile='yonyou_u8'))
  if response.status_code!=201:raise AssertionError('registered PostgreSQL preview failed: '+response.text)
  v=response.json();checks.append('registered_read_only_preview')
  response=client.post('/api/v1/erp/runs/'+v['id']+'/clean',json={});assert response.status_code==200,response.text;v=response.json()
  assert v['quality']['valid_rows']==2 and v['quality']['totals']['CNY']['debit']=='100.23';checks.append('decimal_cleaning_exact')
  response=client.post('/api/v1/erp/runs/'+v['id']+'/commit',json={'cleaning_token':v['cleaning_token']});assert response.status_code==200,response.text;batch=response.json()['batch']['batch_id'];checks.append('explicit_commit')
  assert client.get('/api/v1/metrics/finance').json()[0]['revenue']=='100.23';checks.append('metrics_match')
  replay=client.post('/api/v1/erp/source-preview',json=dict(source_id='pg-u8',ledger_id='TESTBOOK',profile='yonyou_u8')).json()
  replay=client.post('/api/v1/erp/runs/'+replay['id']+'/clean',json={}).json()
  result=client.post('/api/v1/erp/runs/'+replay['id']+'/commit',json={'cleaning_token':replay['cleaning_token']});assert result.json()['batch']['batch_id']==batch;checks.append('database_snapshot_idempotent')
 with psycopg.connect(host='127.0.0.1',port=55439,user='erp_reader',password=secret,dbname='postgres') as c:
  try:c.execute("DELETE FROM public.erp_fixture")
  except psycopg.errors.InsufficientPrivilege:checks.append('source_reader_cannot_delete')
  else:raise AssertionError('reader unexpectedly has write privilege')
 core.app.state.db.dispose()
 result=dict(passed=True,checks=checks,scope='real PostgreSQL with synthetic U8-shaped rows; not an actual customer U8 instance')
 (base/'postgres-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print('PASS: real read-only PostgreSQL ERP source, exact cleaning, commit, metrics, replay and denied DELETE')
 return result
