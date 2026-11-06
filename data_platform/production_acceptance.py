"""Isolated production identity acceptance; all runtime files under work/."""
from pathlib import Path
import os,sys,subprocess,secrets,uuid,runpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/runtime'))
import psycopg
from psycopg import sql
alias=next(x+':' for x in 'ZYXWV' if not Path(x+':/').exists())
subprocess.run(['subst',alias,str(ROOT)],check=True)
base=ROOT/'work'/('production-db-'+uuid.uuid4().hex);base.mkdir()
secret=secrets.token_urlsafe(24);pw=base/'password.tmp';pw.write_text(secret)
def run(name,*args):
 def compat(x):return str(x).replace(str(ROOT),alias)
 subprocess.run([compat(ROOT/'work/postgres-runtime/pgsql/bin'/(name+'.exe')),*map(compat,args)],check=True,cwd=alias+'\\',env={**os.environ,'PGPASSWORD':secret})
started=False
try:
 run('initdb','-D',base/'data','-U','owner','--pwfile',pw,'-A','scram-sha-256','--encoding=UTF8','--locale=C');pw.unlink()
 run('pg_ctl','-D',base/'data','-l',base/'server.log','-o','-h 127.0.0.1 -p 55439','-w','start');started=True
 url='postgresql://owner:'+secret+'@127.0.0.1:55439/postgres'
 os.environ['DATABASE_URL']=url
 for command in ['migrate','load-demo']:
  sys.argv=['manage.py',command];runpy.run_path(str(ROOT/'data_platform/manage.py'),run_name='__main__')
 with psycopg.connect(url) as c:
  c.execute((ROOT/'data_platform/production_identity.sql').read_text(encoding='utf-8-sig'))
  for login,org in [('reader_a','demo'),('reader_b','other'),('reader_unknown',None)]:
   c.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} IN ROLE finagent_reader').format(sql.Identifier(login),sql.Literal(secret)))
   if org:c.execute('INSERT INTO identity.login_organization VALUES(%s,%s)',(login,org))
 for login,expected in [('reader_a',12),('reader_b',0),('reader_unknown',0)]:
  with psycopg.connect(host='127.0.0.1',port=55439,dbname='postgres',user=login,password=secret) as c:
   c.execute("select set_config('app.organization_id','demo',true)")
   assert c.execute('select count(*) from ads.finance_dashboard').fetchone()[0]==expected
   c.execute('SET ROLE finagent_reader')
   assert c.execute('select count(*) from ads.finance_dashboard').fetchone()[0]==expected
   for query in ['SELECT * FROM identity.login_organization','SELECT * FROM dwd.fact_journal_entry',"UPDATE identity.login_organization SET organization_id='demo'","SET ROLE owner"]:
    try:
     with c.transaction():c.execute(query)
    except psycopg.errors.InsufficientPrivilege:pass
    else:raise AssertionError(query)
 # Exercise the backend reader adapter with three distinct real login identities.
 import json
 for folder in ('backend','work/agent-runtime','work/export-runtime'):
  sys.path.insert(0,str(ROOT/folder))
 import app as core,warehouse
 os.environ['FINAGENT_WAREHOUSE_PRODUCTION']='1'
 os.environ['FINAGENT_WAREHOUSE_READERS_JSON']=json.dumps({'demo':'postgresql://reader_a:'+secret+'@127.0.0.1:55439/postgres','other':'postgresql://reader_b:'+secret+'@127.0.0.1:55439/postgres'})
 for org,expected in [('demo',12),('other',0)]:
  token=core.request_organization.set(org)
  try:assert len(warehouse.metrics())==expected
  finally:core.request_organization.reset(token)
 token=core.request_organization.set('unconfigured')
 try:
  try:warehouse.metrics()
  except Exception as e:assert getattr(e,'status_code',None)==503
  else:raise AssertionError('missing production reader did not fail closed')
 finally:core.request_organization.reset(token)
 print('PASS: backend production reader adapter respects login identity and missing mapping fails closed')
 if os.getenv('PRODUCTION_DBT')=='1':
  env={**os.environ,'PYTHONPATH':str(ROOT/'work/dbt-stable'),'DBT_USER':'owner','DBT_PASSWORD':secret,'DBT_PORT':'55439','DBT_DATABASE':'postgres','DBT_SEND_ANONYMOUS_USAGE_STATS':'false','DBT_LOG_PATH':str(ROOT/'work/dbt-stable-logs'),'DBT_TARGET_PATH':str(ROOT/'work/dbt-stable-target')}
  code="from dbt.cli.main import dbtRunner; import sys; r=dbtRunner().invoke(['build','--project-dir','dbt','--profiles-dir','dbt']); sys.exit(0 if r.success else 1)"
  subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,check=True)
 runpy.run_path(str(ROOT/'data_platform/verify_workbench.py'),run_name='__main__')
 sys.path.insert(0,str(ROOT/'data_platform'))
 runpy.run_path(str(ROOT/'data_platform/verify_workbench_publish.py'),run_name='__main__')
 print('PASS: real login binding, forged GUC rejection, SET ROLE identity retention, unmapped fail closed, mapping/base-table/escalation denial')
 if os.getenv('PRODUCTION_HTTP')=='1':
  runpy.run_path(str(ROOT/'data_platform/verify_workbench_http.py'),run_name='__main__')
 if os.getenv('PRODUCTION_RECOVERY')=='1':
  sys.path.insert(0,str(ROOT))
  from infrastructure.pg_recovery import exercise
  exercise(ROOT,base,secret,alias)
 if os.getenv('PRODUCTION_ERP')=='1':
  sys.path.insert(0,str(ROOT))
  from infrastructure.erp_postgres_acceptance import exercise as erp_exercise
  erp_exercise(ROOT,secret)
 if os.getenv('PRODUCTION_ENTERPRISE')=='1':
  sys.path.insert(0,str(ROOT))
  from infrastructure.enterprise_warehouse_acceptance import exercise as enterprise_exercise
  enterprise_exercise(ROOT,secret)
finally:
 if started:run('pg_ctl','-D',base/'data','-m','fast','-w','stop')
 pw.unlink(missing_ok=True)
 subprocess.run(['subst',alias,'/D'],check=True)



