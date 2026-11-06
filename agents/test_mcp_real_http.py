import unittest,sys,tempfile,threading,socket,time,csv,io,os
from pathlib import Path
from unittest.mock import patch
class RealHTTP(unittest.TestCase):
 def test_nonempty(self):
  sys.path.insert(0,str(Path('backend').resolve()))
  import app as core,uvicorn
  from sqlalchemy import create_engine
  from mcp_servers import finance
  from agents.runtime import Tools
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=create_engine('sqlite:///'+str(Path(d)/'db.sqlite'));core.meta.create_all(db)
   old=getattr(core.app.state,'db',None);core.app.state.db=db
   data=list(csv.DictReader(io.StringIO(Path('data_platform/sample_vouchers.csv').read_text(encoding='utf-8-sig'))))
   core.ingest(db,data,'mcp-real-http','sample.csv',kind='simulated')
   sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   server=uvicorn.Server(uvicorn.Config(core.app,log_level='error',lifespan='off'));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
   with patch.dict(os.environ,{'FINAGENT_API_TOKEN':'test-mcp-only','FINAGENT_API_ROLE':'reader'}):
    thread.start()
    try:
     for _ in range(100):
      if server.started:break
      time.sleep(.02)
     with patch.object(finance,'client',lambda:Tools('http://127.0.0.1:%d'%port,token='test-mcp-only')):
      result=finance.get_report_evidence('2026-01','2026-12')
      self.assertTrue(result['metrics']);self.assertTrue(result['sources'][0]['batch_ids'])
      batches=core.batch_list();self.assertTrue(finance.get_data_quality(batches[0]['batch_id']))
      self.assertIsInstance(finance.review_financial_risks('2026-01','2026-12'),dict)
      self.assertIsInstance(finance.get_budget_execution('2026-01','2026-12'),list)
     with self.assertRaises(RuntimeError):Tools('http://127.0.0.1:%d'%port,token='wrong').query_finance_metrics(__import__('agents.runtime',fromlist=['Query']).Query())
    finally:server.should_exit=True;thread.join(5);sock.close();core.app.state.db=old;db.dispose()
if __name__=='__main__':unittest.main()

