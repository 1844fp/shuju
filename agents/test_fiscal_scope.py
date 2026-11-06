import unittest
from agents.semantic import fiscal_years
from agents.hybrid import hybrid_search
class FiscalScopeTests(unittest.TestCase):
 def test_chinese_adjacent(self):
  self.assertEqual(fiscal_years('微软FY2025收入'),{'2025'})
  self.assertEqual(fiscal_years('微软2025年收入'),{'2025'})
 def test_compare(self):self.assertEqual(fiscal_years('比较2016与2025收入'),{'2016','2025'})
 def test_range(self):
  self.assertEqual(fiscal_years('2016-2025'),{str(y) for y in range(2016,2026)})
  self.assertEqual(fiscal_years('FY2016至FY2025收入'),{str(y) for y in range(2016,2026)})
 def test_no_year(self):self.assertEqual(fiscal_years('微软收入与净利润'),set())
 def test_policy_date(self):
  for q in ('2025年生效的报销制度','制度生效日期2025-01-01','effective 2025 policy'):
   self.assertEqual(fiscal_years(q),set())
 def test_no_filter_and_policy_retained(self):
  class Recorder:
   provenance={'revision':'scope-test-only'}
   def search(self,q,docs,*args):self.docs=docs;return []
  r=Recorder();docs=[dict(id=str(y),title=f'FY{y}收入',text='收入事实',effective_date='2020-01-01',version='1') for y in (2016,2020,2025)]
  hybrid_search('收入',docs,r);self.assertEqual(len(r.docs),3)
  hybrid_search('2016-2025收入',docs,r);self.assertEqual(len(r.docs),3)
  hybrid_search('2016与2025收入',docs,r);self.assertEqual({d['id'] for d in r.docs},{'2016','2025'})
  hybrid_search('制度2025年生效',docs,r);self.assertEqual(len(r.docs),3)
if __name__=='__main__':unittest.main()
