import unittest,tempfile
from pathlib import Path
from agents.task_memory import TaskMemory
from agents.harness import Harness,ROLES
class MemoryTests(unittest.TestCase):
 def test_recovery_routing_scope_stale(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   path=Path(d);calls=[];ref={'id':'public1','sha256':'a'*64};sources={('a','public1'):'a'*64}
   def tool(role):
    def call(q,p):calls.append(role);return {'source':'public1'}
    return call
   tools={r:tool(r) for r in ROLES};options=dict(intent='budget',data_kind='public_disclosure',references=[ref],resolve_source=lambda org,key:sources.get((org,key)))
   m=TaskMemory(path/'memory');h=Harness(path/'checkpoint')
   self.assertEqual(m.run(h,'t','a',{},tools,**options)['status'],'awaiting_approval')
   self.assertEqual(calls,['data','budget']);self.assertIsNone(m.load('b','t'))
   result=TaskMemory(path/'memory').run(Harness(path/'checkpoint'),'t','a',{},tools,approved=True,**options)
   self.assertEqual(result['status'],'completed');self.assertEqual(calls,['data','budget','report'])
   sources[('a','public1')]='b'*64
   self.assertEqual(m.run(h,'t','a',{},tools,approved=True,**options)['status'],'stale_source');self.assertEqual(len(calls),3)
   self.assertEqual(m.run(h,'t','b',{},tools,**options)['status'],'stale_source')
 def test_whitelist_and_budget(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   m=TaskMemory(Path(d)/'m');h=Harness(Path(d)/'h');tools={r:lambda q,p:'ok' for r in ROLES}
   opts=dict(intent='full',data_kind='simulated',references=[],resolve_source=lambda o,k:None,max_calls=1)
   self.assertEqual(m.run(h,'t','o',{},tools,**opts)['status'],'budget_exhausted')
   opts['intent']='payment'
   with self.assertRaises(ValueError):m.run(h,'x','o',{},tools,**opts)
   opts.update(intent='finance',data_kind='customer_private')
   with self.assertRaises(ValueError):m.run(h,'x','o',{},tools,**opts)
if __name__=='__main__':unittest.main()
