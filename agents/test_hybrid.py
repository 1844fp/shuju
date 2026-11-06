import unittest,os,json
from unittest.mock import patch
from agents.hybrid import hybrid_search,verify_citations
from agents.semantic import Semantic
from agents.provider import Provider
class Tests(unittest.TestCase):
 def test_real(self):
  s=Semantic();self.assertEqual(s.initialize()['status'],'ready')
  docs=[dict(id='a',title='应收账款',text='客户未按时偿还货款，应加强应收账款催收。',version='1',effective_date='2020-01-01',locator='段1'),dict(id='b',title='食堂',text='今天食堂供应面条和米饭。',version='1',effective_date='2020-01-01',locator='段2')]
  hits=hybrid_search('买家拖欠付款怎么办',docs,s);self.assertEqual(hits[0]['id'],'a');self.assertTrue(verify_citations(hits,docs)['valid'])
  hits[0]['matched_text']='伪造';self.assertFalse(verify_citations(hits,docs)['valid'])
  self.assertEqual(hybrid_search('货款',docs,s,as_of='2019-01-01'),[])
 def test_budget(self):
  def mock(p):
   self.assertEqual(p['max_completion_tokens'],512)
   return {'choices':[{'message':{'content':json.dumps({'intent':'finance_metrics','query':{}})}}]}
  with patch.dict(os.environ,{'FINAGENT_MODEL_API_KEY':'mock','FINAGENT_MODEL':'mock','FINAGENT_MODEL_BASE_URL':'https://mock.invalid'}):
   p=Provider(transport=mock)
   for _ in range(4):p.plan('查询')
   with self.assertRaisesRegex(RuntimeError,'budget'):p.plan('查询')
