import os,sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT))
import app as core
from fastapi.testclient import TestClient
class AnalysisKnowledgeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');core.app.state.db=core.engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'));self.client=TestClient(core.app)
 def tearDown(self):
  self.client.close();core.app.state.db.dispose();self.tmp.cleanup()
  if hasattr(core.app.state,'model_test_transport'):del core.app.state.model_test_transport
 def test_model_confirmation(self):
  self.assertEqual(self.client.post('/api/v1/analysis/plan',json={'question':'收入'}).status_code,422)
  core.app.state.model_test_transport=lambda _: {'choices':[{'message':{'content':json.dumps({'intent':'finance_metrics','query':{'start_period':'2026-01','end_period':'2026-12','currency':'CNY'}})}}]}
  with patch.dict(os.environ,{'FINAGENT_MODEL_API_KEY':'offline-test','FINAGENT_MODEL':'offline-test','FINAGENT_MODEL_BASE_URL':'https://invalid.test/v1'}):
   planned=self.client.post('/api/v1/analysis/plan',json={'question':'收入','allow_question_transmission':True});self.assertEqual(planned.status_code,201,planned.text);value=planned.json()
   self.assertEqual(self.client.post('/api/v1/analysis/confirm',json={'plan_id':value['task_id'],'confirmed_query':{'currency':'USD'}}).status_code,409)
   confirmed=self.client.post('/api/v1/analysis/confirm',json={'plan_id':value['task_id'],'confirmed_query':value['intent']['query']});self.assertEqual(confirmed.status_code,200,confirmed.text);self.assertEqual(confirmed.json()['mode'],'model_assisted_confirmed')
 def test_vector_versions_and_isolation(self):
  doc={'title':'费用制度','version':'1','effective_date':'2026-01-01','locator':'第1段','text':'差旅费用报销审批制度'}
  saved=self.client.post('/api/v1/knowledge/documents',json=doc);self.assertEqual(saved.status_code,201,saved.text)
  found=self.client.get('/api/v1/knowledge/vector-search',params={'q':'差旅费用报销审批制度'}).json();self.assertAlmostEqual(found['matches'][0]['score'],1);self.assertFalse(found['semantic_embeddings'])
  self.assertEqual(self.client.get('/api/v1/knowledge/vector-search',params={'q':'差旅','as_of':'2025-01-01'}).json()['matches'],[])
  analysis=self.client.post('/api/v1/analysis',json={'mode':'demo','question':doc['text']}).json();self.assertIn(saved.json()['content_sha256'],analysis['answer'])
  self.assertEqual(self.client.post('/api/v1/knowledge/documents',json={**doc,'text':'不同内容'}).status_code,409)
  alternate=core.engine('sqlite:///'+str(Path(self.tmp.name)/'other.db'));marker=core.request_database.set(alternate)
  try:
   from knowledge_vectors import docs
   docs.create(alternate,checkfirst=True)
   from sqlalchemy import select
   with alternate.connect() as c:self.assertEqual(c.execute(select(docs.c.id)).all(),[])
  finally:core.request_database.reset(marker);alternate.dispose()
if __name__=='__main__':unittest.main(verbosity=2)
