import unittest
from agents.runtime import *
class Checks(unittest.TestCase):
 def test_validation(self):
  for q in ({'currency':'CNY&x=1'},{'start_period':'2026-13'},{'start_period':'2027-01'}):
   with self.assertRaises(ValueError): Query(**q)
 def test_local(self):
  with self.assertRaises(ValueError): Tools('http://example.com')
 def test_no_fake_model(self):
  self.assertEqual(build_graph(Tools()).invoke({'mode':'model'})['status'],'model_not_configured')
 def test_retrieval(self):
  self.assertEqual(retrieve('unrelated'),[])
  self.assertTrue(retrieve('经营利润')[0]['locator'])
 def test_live(self):
  s=build_graph(Tools()).invoke({'mode':'demo','question':'利润','query':Query().model_dump()})
  self.assertEqual(s['status'],'completed'); self.assertTrue(s['sources']); self.assertIn('非 AI',s['answer'])
if __name__=='__main__': unittest.main()
