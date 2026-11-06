import unittest,tempfile,threading,time
from pathlib import Path
from agents.harness import Harness,ROLES
class ParallelTests(unittest.TestCase):
 def test_parallel_barrier(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   h=Harness(Path(d)/'s');barrier=threading.Barrier(3)
   def branch(q,p):
    assert 'data' in p
    barrier.wait(timeout=2);return 'ok'
   def report(q,p):
    assert all(x in p for x in ROLES[:-1]);return 'done'
   tools={'data':lambda q,p:'ready','analysis':branch,'budget':branch,'audit':branch,'report':report}
   self.assertEqual(h.run('t','o',{},tools)['status'],'completed')
 def test_concurrent_claim(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   h=Harness(Path(d)/'s');entered=threading.Event();release=threading.Event();calls=[]
   def data(q,p):calls.append(1);entered.set();release.wait(2);return 'ok'
   tools={r:lambda q,p:'ok' for r in ROLES};tools['data']=data
   t=threading.Thread(target=lambda:h.run('t','o',{},tools));t.start();entered.wait(2)
   self.assertEqual(h.run('t','o',{},tools)['status'],'busy');release.set();t.join();self.assertEqual(len(calls),1)
 def test_global_budget(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   h=Harness(Path(d)/'s');tools={r:lambda q,p:'ok' for r in ROLES}
   self.assertEqual(h.run('t','o',{},tools,max_calls=2)['status'],'budget_exhausted')
   with h.connect() as db:self.assertEqual(db.execute('SELECT SUM(attempts) FROM harness_nodes').fetchone()[0],2)
if __name__=='__main__':unittest.main()
