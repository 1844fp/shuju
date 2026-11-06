"""Real enterprise account + ERP original/quarantine publication acceptance."""
import csv,io,json,os,time
from pathlib import Path

def exercise(root,secret):
 import psycopg
 from psycopg import sql
 from psycopg.conninfo import make_conninfo
 import app as core
 from fastapi.testclient import TestClient
 root=Path(root);base=root/'work/acceptance/enterprise';base.mkdir(parents=True,exist_ok=True)
 os.environ['FINAGENT_AUTH_MODE']='demo';os.environ['FINAGENT_ERP_APPROVAL_REQUIRED']='0'
 owner=make_conninfo(host='127.0.0.1',port=55439,dbname='postgres',user='owner',password=secret)
 with psycopg.connect(owner) as c:
  c.execute(sql.SQL('CREATE ROLE enterprise_reader LOGIN PASSWORD {} IN ROLE finagent_reader').format(sql.Literal(secret)))
  c.execute("INSERT INTO identity.login_organization VALUES('enterprise_reader','local-demo')")
 os.environ['FINAGENT_WAREHOUSE_URL']=owner
 os.environ['FINAGENT_WAREHOUSE_PRODUCTION']='1'
 os.environ['FINAGENT_WAREHOUSE_READERS_JSON']=json.dumps({'local-demo':make_conninfo(host='127.0.0.1',port=55439,dbname='postgres',user='enterprise_reader',password=secret)})
 core.app.state.db=core.engine('sqlite:///'+str(base/('source-'+str(time.time_ns())+'.sqlite')))
 with TestClient(core.app) as client:
  result=client.post('/api/v1/erp/accounts',json=dict(approved=True,accounts=[dict(code='REV.ENTERPRISE',name='企业测试收入',category='revenue')]))
  assert result.status_code==200,result.text
  columns=['posting_date','voucher_type','voucher_no','line_no','account_code','department_code','currency','debit','credit','__data_kind'];rows=[]
  for number,code,i,debit,credit in [('001','1002',1,'250.40','0'),('001','REV.ENTERPRISE',2,'0','250.40'),('002','UNKNOWN',1,'10','0'),('002','6001',2,'0','10')]:rows.append(dict(zip(columns,['2026-02-28','记',number,str(i),code,'D01','CNY',debit,credit,'simulated'])))
  buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=columns);writer.writeheader();writer.writerows(rows);original=buffer.getvalue().encode('utf-8-sig')
  value=client.post('/api/v1/erp/preview',files={'file':('enterprise-fixture.csv',original)},data=dict(ledger_id='ENTERPRISE',profile='generic')).json()
  response=client.post('/api/v1/erp/runs/'+value['id']+'/clean',json={'data_kind':'simulated'});assert response.status_code==200,response.text;value=response.json()
  assert value['quality']['valid_rows']==2 and value['quality']['quarantined_rows']==2
  response=client.post('/api/v1/erp/runs/'+value['id']+'/commit',json=dict(cleaning_token=value['cleaning_token'],acknowledge_quarantine=True));assert response.status_code==200,response.text;batch=response.json()['batch']['batch_id']
  response=client.post('/api/v1/warehouse/publish/'+batch);assert response.status_code==200,response.text
  assert client.post('/api/v1/warehouse/publish/'+batch).json()['status']=='already_published'
  data=client.get('/api/v1/warehouse/metrics').json();assert data[0]['revenue']=='250.40' and data[0]['data_kind']==['simulated']
 with psycopg.connect(owner) as c:
  assert c.execute("SELECT category FROM dim.account WHERE organization_id='local-demo' AND code='REV.ENTERPRISE'").fetchone()[0]=='revenue'
  stored=c.execute('SELECT original_content,source_sha256 FROM metadata.erp_snapshot WHERE batch_id=%s',(batch,)).fetchone();assert bytes(stored[0])==original
  assert c.execute('SELECT count(*) FROM ods.erp_source_row WHERE batch_id=%s',(batch,)).fetchone()[0]==4
  assert c.execute("SELECT count(*) FROM ods.erp_source_row WHERE batch_id=%s AND row_status='quarantined'",(batch,)).fetchone()[0]==2
  assert c.execute('SELECT count(*) FROM dwd.fact_journal_entry WHERE batch_id=%s',(batch,)).fetchone()[0]==2
 with psycopg.connect(host='127.0.0.1',port=55439,dbname='postgres',user='enterprise_reader',password=secret) as c:
  try:c.execute('SELECT original_content FROM metadata.erp_snapshot')
  except psycopg.errors.InsufficientPrivilege:pass
  else:raise AssertionError('reader can access original ERP content')
 core.app.state.db.dispose()
 result=dict(passed=True,checks=['custom_dimension','exact_metrics','byte_exact_original','all_four_original_rows','two_quarantined_rows','only_two_facts','idempotent_publication','production_reader_original_denied'],scope='isolated real PostgreSQL, simulated enterprise data')
 (base/'warehouse-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print('PASS: enterprise custom dimensions, complete original/quarantine provenance and protected read identity')
