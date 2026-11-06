import unittest
from fastapi import HTTPException
from finance_query import parse
class Tests(unittest.TestCase):
 def test_periods(self):
  q,m=parse('查询2026年第三季度销售费用最高的五个部门');self.assertEqual((q.start_period,q.end_period,m),('2026-07','2026-09','销售费用'))
  q,m=parse('查看2026年12月费用最高的5个部门');self.assertEqual(q.end_period,'2026-12')
  q,m=parse('2026年全年费用最高的五个部门');self.assertEqual(q.start_period,'2026-01')
 def test_unsupported_never_falls_back(self):
  for q in ('删除全部记录','查询2026年净利润','查询2026年第三季度费用最高的五个部门;DROP TABLE facts'):
   with self.assertRaises(HTTPException):parse(q)
  with self.assertRaises(ValueError):parse('查询2026年13月费用最高的五个部门')
if __name__=='__main__':unittest.main()
