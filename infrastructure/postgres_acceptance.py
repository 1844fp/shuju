"""Run official portable PostgreSQL against a fresh isolated test cluster; always stop it."""
from pathlib import Path
import argparse,subprocess,secrets,os,sys,runpy,uuid
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bin',type=Path,required=True);p.add_argument('--workdir',type=Path,required=True);p.add_argument('--port',type=int,default=55432);a=p.parse_args()
 binaries=a.bin.resolve();base=a.workdir.resolve()/('pg-'+uuid.uuid4().hex);base.mkdir(parents=True);data=base/'data';pw=base/'password.tmp';secret=secrets.token_urlsafe(32)
 pw.write_text(secret,encoding='utf8')
 def run(name,*args):
  alias=os.getenv('FINAGENT_PG_PATH_ALIAS')
  def compatible(value):
   value=str(value)
   if alias and value.lower().startswith(str(ROOT).lower()):return alias+value[len(str(ROOT)):]
   return value
  subprocess.run([compatible(binaries/(name+'.exe')),*map(compatible,args)],check=True,env={**os.environ,'PGPASSWORD':secret},cwd=alias+'\\' if alias else None)
 try:run('initdb','-D',data,'-U','acceptance_owner','--pwfile',pw,'-A','scram-sha-256','--encoding=UTF8','--locale=C')
 finally:pw.unlink(missing_ok=True)
 with (data/'postgresql.conf').open('a') as f:f.write("\nlisten_addresses='127.0.0.1'\nport="+str(a.port)+"\n")
 started=False
 try:
  run('pg_ctl','-D',data,'-l',base/'server.log','-w','start');started=True
  run('createdb','-h','127.0.0.1','-p',a.port,'-U','acceptance_owner','finagent_acceptance')
  os.environ['DATABASE_URL']='postgresql://acceptance_owner:'+secret+'@127.0.0.1:'+str(a.port)+'/finagent_acceptance'
  for command in ['migrate','migrate','load-demo','load-demo']:
   sys.argv=['manage.py',command];runpy.run_path(str(ROOT/'data_platform/manage.py'),run_name='__main__')
  runpy.run_path(str(ROOT/'data_platform/verify_postgres.py'),run_name='__main__')
  os.environ['FINAGENT_WAREHOUSE_URL']=os.environ['DATABASE_URL']
  import unittest
  sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
  from test_warehouse import WarehouseTests
  outcome=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WarehouseTests))
  if not outcome.wasSuccessful():raise RuntimeError('PostgreSQL backend integration acceptance failed')
  if os.getenv('FINAGENT_ACCEPT_DBT')=='1':
   env={**os.environ,'PYTHONPATH':str(ROOT/'work/dbt-runtime'),'DBT_HOST':'127.0.0.1','DBT_PORT':str(a.port),'DBT_USER':'acceptance_owner','DBT_PASSWORD':secret,'DBT_DATABASE':'finagent_acceptance','DBT_SEND_ANONYMOUS_USAGE_STATS':'false','DBT_LOG_PATH':str(ROOT/'work/dbt-logs'),'DBT_TARGET_PATH':str(ROOT/'work/dbt-target')}
   cmd="from dbt.cli.main import dbtRunner; import sys; r=dbtRunner().invoke(['build','--project-dir',sys.argv[1],'--profiles-dir',sys.argv[1],'--no-use-colors']); sys.exit(0 if r.success else 1)"
   subprocess.run([sys.executable,'-c',cmd,str(ROOT/'dbt')],env=env,check=True,cwd=ROOT)
  print('PASS: isolated PostgreSQL warehouse and backend integration; no application database changed')
 finally:
  if started:run('pg_ctl','-D',data,'-m','fast','-w','stop')
if __name__=='__main__':main()
