import os,sys,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import app as core,leased_jobs
class WorkerProcessTests(unittest.TestCase):
 def test_operator_worker_executes_committed_job(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'work') as d:
   url='sqlite:///'+str(Path(d)/'worker.db');db=core.engine(url);token=core.request_database.set(db);org=core.request_organization.set('local-demo')
   try:
    job=leased_jobs.submit('report',{})
    env={**os.environ,'DATABASE_URL':url,'FINAGENT_AUTH_MODE':'demo','TEMP':str(ROOT/'work'),'TMP':str(ROOT/'work')}
    result=subprocess.run([sys.executable,str(ROOT/'backend/worker.py'),'--once'],env=env,cwd=ROOT,capture_output=True,text=True,timeout=30)
    self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(leased_jobs.get(db,'local-demo',job['id'])['status'],'completed')
   finally:core.request_database.reset(token);core.request_organization.reset(org);db.dispose()
if __name__=='__main__':unittest.main(verbosity=2)
