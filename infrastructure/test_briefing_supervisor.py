"""Isolated real process supervision; all artifacts under project work/."""
import json,os,sys,time,tempfile,unittest,subprocess,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for n in ('runtime','agent-runtime','export-runtime'):sys.path.insert(0,str(ROOT/'work'/n))
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'infrastructure'))
import briefing_supervisor as sup
import app as core
import cfo_briefings as b
class SupervisorTests(unittest.TestCase):
 def wait(self,fn,timeout=20):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   value=fn()
   if value:return value
   time.sleep(.1)
  self.fail('condition timed out')
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work',prefix='brief-supervisor-');self.base=Path(self.tmp.name);self.state=self.base/'state';db=self.base/'simulation.sqlite';self.db=core.engine('sqlite:///'+str(db));b.meta.create_all(self.db)
  with self.db.begin() as c:c.execute(b.schedules.insert().values(id='TEST-ORG|daily',organization='TEST-ORG',payload=json.dumps(dict(id='daily',currency='CNY',hour=0))))
  self.cfg=self.base/'config.json';self.cfg.write_text(json.dumps(dict(database=str(db.relative_to(ROOT)),organization='TEST-ORG',state_dir=str(self.state.relative_to(ROOT)),interval_seconds=1,heartbeat_seconds=.1,backoff_seconds=.2,max_backoff_seconds=1,stop_timeout_seconds=5)),encoding='utf-8');self.arg=str(self.cfg.relative_to(ROOT));self.env=os.environ.copy();self.env['TEMP']=self.env['TMP']=str(ROOT/'work');self.env['PYTHONPATH']=os.pathsep.join(str(ROOT/'work'/n) for n in ('runtime','agent-runtime','export-runtime'))
 def cli(self,action,check=True):
  result=subprocess.run([sys.executable,str(ROOT/'infrastructure/briefing_supervisor.py'),action,'--config',self.arg],cwd=ROOT,env=self.env,capture_output=True,text=True,timeout=25,check=False)
  if check and result.returncode:
   self.fail(result.stderr+'\n'+((self.state/'supervisor.log').read_text(errors='replace') if (self.state/'supervisor.log').exists() else ''))
  return result
 def info(self):return sup.read(self.state/'state.json')
 def count(self):
  with self.db.connect() as c:return len(list(c.execute(b.briefs.select())))
 def tearDown(self):
  r=self.info()
  if sup.owned(r.get('supervisor',{})):
   try:self.cli('stop')
   except Exception:sup.terminate(r['supervisor'],5)
  r=self.info()
  if sup.owned(r.get('child',{})):sup.terminate(r['child'],5)
  self.db.dispose();self.tmp.cleanup()
 def test_restart_daily_idempotence_and_graceful_stop(self):
  self.cli('start');self.wait(lambda:self.count()==1);initial=self.info();old=initial['child'];self.assertTrue(sup.owned(old));sup.terminate(old,5)
  recovered=self.wait(lambda:self.info().get('child',{}).get('pid') not in (None,old['pid']) and self.info().get('restarts',0)>=1)
  self.wait(lambda:sup.read(self.state/'child-heartbeat.json').get('phase')=='waiting');time.sleep(1.2);self.assertEqual(self.count(),1)
  status=json.loads(self.cli('status').stdout);self.assertTrue(status['supervisor_running']);self.assertTrue(status['worker_running']);self.assertGreater(status['heartbeat'],initial['heartbeat'])
  duplicate=self.cli('start',False);self.assertNotEqual(duplicate.returncode,0)
  self.cli('stop');end=self.info();self.assertEqual(end['status'],'stopped');self.assertFalse(end['forced']);self.assertFalse(sup.owned(end['child']));self.assertEqual(self.count(),1)
  events=[json.loads(x)['event'] for x in (self.state/'events.jsonl').read_text().splitlines()];self.assertIn('worker_exited',events)
 def test_parent_crash_recovery(self):
  self.cli('start');self.wait(lambda:self.count()==1);r=self.info();sup.terminate(r['supervisor'],5);self.wait(lambda:not sup.owned(r['child']))
  self.cli('start');self.wait(lambda:sup.read(self.state/'child-heartbeat.json').get('token')==self.info().get('token') and sup.read(self.state/'child-heartbeat.json').get('phase')=='waiting');self.assertEqual(self.count(),1);self.cli('stop')
 def test_failure_backoff_is_bounded(self):
  c=json.loads(self.cfg.read_text());c['interval_seconds']=10;self.cfg.write_text(json.dumps(c),encoding='utf-8')
  with self.db.begin() as conn:conn.execute(b.schedules.update().values(payload=json.dumps(dict(id='daily',currency='CNY',hour='invalid'))))
  self.cli('start')
  def delays():
   p=self.state/'events.jsonl'
   return [json.loads(x)['backoff_seconds'] for x in p.read_text().splitlines() if json.loads(x)['event']=='worker_exited'] if p.exists() else []
  self.wait(lambda:len(delays())>=4,timeout=25);self.assertEqual(delays()[:4],[.2,.4,.8,1]);self.assertEqual(self.count(),0);self.cli('stop')
 def test_config_and_identity_fail_closed(self):
  c=sup.config(self.arg);self.assertEqual(c['organization'],'TEST-ORG')
  self.cli('start');self.wait(lambda:self.info().get('child'));r=self.info();forged={**r['supervisor'],'created':r['supervisor']['created']+10};self.assertIsNone(sup.owned(forged));self.assertIsNone(sup.owned({**r['supervisor'],'command':['not-the-worker']}));self.cli('stop')
  original=json.loads(self.cfg.read_text())
  for update in ({'database':'../outside.sqlite'},{'organization':''},{'state_dir':'backend'},{'database':str(self.base/'simulation.sqlite')},{'interval_seconds':True},{'arbitrary_command':'whoami'}):
   self.cfg.write_text(json.dumps({**original,**update}),encoding='utf-8')
   with self.assertRaises(ValueError):sup.config(self.arg)
  self.cfg.write_text(json.dumps(original),encoding='utf-8')
if __name__=='__main__':unittest.main()
