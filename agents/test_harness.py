import unittest,tempfile,sqlite3
from contextlib import closing
from pathlib import Path
from agents.harness import Harness,ROLES
class HarnessTests(unittest.TestCase):
 def test_recovery_scope_transaction(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   path=Path(d)/'state.sqlite'; h=Harness(path);calls=[]
   def tool(q,r):
    with closing(sqlite3.connect(path,timeout=.1)) as db:db.execute('BEGIN IMMEDIATE');db.rollback()
    calls.append(1);return {'ok':True}
   tools={r:tool for r in ROLES}
   self.assertEqual(h.run('t','a',{},tools)['status'],'completed')
   self.assertEqual(h.run('t','a',{},tools)['status'],'completed');self.assertEqual(len(calls),5)
   self.assertEqual(h.run('t','b',{},tools)['status'],'completed');self.assertEqual(len(calls),10)
 def test_retry_budget(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   h=Harness(Path(d)/'s');calls=[]
   def fail(q,r):calls.append(1);raise TimeoutError()
   tools={r:fail for r in ROLES}
   self.assertEqual(h.run('t','o',{},tools)['status'],'failed')
   self.assertEqual(h.run('t','o',{},tools)['status'],'budget_exhausted');self.assertEqual(len(calls),2)
if __name__=='__main__':unittest.main()

