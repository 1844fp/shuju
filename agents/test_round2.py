import os,json,unittest,subprocess,sys
from unittest.mock import patch
from agents.provider import Provider,Intent
from agents.runtime import retrieve
class Round2(unittest.TestCase):
 def test_missing(self):
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaisesRegex(RuntimeError,'model_not_configured'): Provider().plan('利润')
 def test_mock(self):
  with patch.dict(os.environ,{'FINAGENT_MODEL_API_KEY':'mock','FINAGENT_MODEL':'mock','FINAGENT_MODEL_BASE_URL':'https://mock.invalid/v1'}):
   p=Provider(transport=lambda payload:{'choices':[{'message':{'content':json.dumps({'intent':'finance_metrics','query':{'currency':'CNY'}})}}]})
   self.assertEqual(p.plan('利润').query.currency,'CNY')
   with self.assertRaisesRegex(RuntimeError,'model_network_disabled'): Provider().plan('利润')
 def test_reject_sql(self):
  with self.assertRaises(ValueError): Intent.model_validate({'intent':'sql','query':{},'sql':'DELETE FROM x'})
 def test_versions(self):
  self.assertEqual(retrieve('利润',version='99'),[])
  self.assertEqual(retrieve('利润',as_of='2020-01-01'),[])
  self.assertEqual(len(retrieve('利润')[0]['content_sha256']),64)
 def test_stdio(self):
  proc=subprocess.Popen([sys.executable,'-m','mcp_servers.finance'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
  messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}]
  try: out,err=proc.communicate(''.join(json.dumps(m)+'\n' for m in messages),timeout=15)
  except subprocess.TimeoutExpired:
   proc.kill(); proc.communicate(); raise
  responses=[json.loads(line) for line in out.splitlines() if line.startswith('{')]
  self.assertTrue(any(r.get('id')==1 and 'result' in r for r in responses),err)
  tools=next(r['result']['tools'] for r in responses if r.get('id')==2)
  self.assertEqual(len(tools),4)
if __name__=='__main__': unittest.main()
