import unittest,tempfile,time,threading,contextvars,sys
from pathlib import Path
from unittest.mock import patch
from agents.harness import Harness,ROLES
class DeadlineTests(unittest.TestCase):
 def test_late_and_approval(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   h=Harness(Path(d)/'s'); tenant=contextvars.ContextVar('testtenant');tenant.set('a')
   def slow(q,p):time.sleep(.15);return 'late'
   tools={r:lambda q,p:tenant.get() for r in ROLES};tools['data']=slow
   self.assertEqual(h.run('t','a',{},tools,max_attempts=1,tool_timeout=.02)['status'],'failed')
   tools['data']=lambda q,p:'new'
   result=h.run('t','a',{},tools,max_attempts=2,tool_timeout=.02,approved=False)
   self.assertEqual(result['status'],'awaiting_approval');time.sleep(.2)
   final=h.run('t','a',{},tools,max_attempts=2,approved=True)
   self.assertEqual(final['results']['data'],'new');self.assertEqual(final['results']['analysis'],'a');self.assertEqual(final['status'],'completed')
 def test_real_five_adapters(self):
  sys.path.insert(0,str(Path('backend').resolve()))
  import app as core
  import agent_runs
  from sqlalchemy import create_engine
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=create_engine('sqlite:///'+str(Path(d)/'test.sqlite'));core.meta.create_all(db)
   old=getattr(core.app.state,'db',None);core.app.state.db=db
   scope=core.request_organization.set('integration')
   class LocalHarness(Harness):
    def __init__(self,path):super().__init__(Path(d)/'checkpoints.sqlite')
   try:
    agent_runs.meta.create_all(db)
    with db.begin() as c:
     c.execute(agent_runs.runs.insert().values(id='t',organization='integration',query='{}'))
     c.execute(agent_runs.approvals.insert().values(id='t',organization='integration',maker='maker',reviewer='reviewer',decision='approved'))
    with patch('agents.harness.Harness',LocalHarness):
     result=agent_runs.execute('t',{})
     self.assertEqual(result['status'],'completed');self.assertEqual(set(result['results']),set(ROLES))
   finally:core.request_organization.reset(scope);core.app.state.db=old;db.dispose()
if __name__=='__main__':unittest.main()
