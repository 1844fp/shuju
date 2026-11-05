import unittest,json,sys
from pathlib import Path
from unittest.mock import patch
from agents.semantic import Semantic
class SemanticTests(unittest.TestCase):
 def test_missing(self):
  s=Semantic()
  with patch('agents.semantic.CACHE',Path('work/nonexistent-semantic-test')):self.assertIn(s.initialize()['status'],('model_missing','dependency_missing'))
 def test_real_chinese(self):
  s=Semantic();self.assertEqual(s.initialize()['status'],'ready')
  items=[{'id':'a','text':'客户未按时偿还货款，企业需要加强应收账款催收。','effective_date':'2020-01-01','version':'1'},{'id':'b','text':'员工食堂今天供应面条和米饭。','effective_date':'2020-01-01','version':'1'}]
  self.assertEqual(s.search('买家拖欠付款怎么办',items)[0]['id'],'a')
  self.assertEqual(s.search('买家拖欠付款怎么办',items,as_of='2019-01-01'),[])
 def test_tenant_routes(self):
  sys.path.insert(0,str(Path('backend').resolve()))
  import semantic_routes as routes
  from fastapi import FastAPI
  from fastapi.testclient import TestClient
  from sqlalchemy import create_engine
  dbs=[create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=__import__('sqlalchemy').pool.StaticPool) for _ in range(2)]
  for index,db in enumerate(dbs):
   routes.meta.create_all(db)
   with db.begin() as c:c.execute(routes.docs.insert().values(id=str(index),payload=json.dumps({'id':str(index),'text':'隔离测试','effective_date':'2020-01-01','version':'1'})))
  class Fake:
   status='ready'
   def info(self):return {'status':'ready'}
   def search(self,q,items,*args):return items
  app=FastAPI();routes.install(app)
  with patch.object(routes,'engine',Fake()):
   for index,db in enumerate(dbs):
    with patch.object(routes.core,'current_db',return_value=db):self.assertEqual(TestClient(app).get('/api/v1/knowledge/semantic-search?q=test').json()['matches'][0]['id'],str(index))
if __name__=='__main__':unittest.main()
