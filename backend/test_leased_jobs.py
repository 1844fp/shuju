import multiprocessing as mp, tempfile, time, unittest
from pathlib import Path
from sqlalchemy import create_engine
import app as core
import leased_jobs as q
def compete(url,out):
 db=create_engine(url);out.put(q.claim(db,'A',0.3));db.dispose()
class Tests(unittest.TestCase):
 def test_processes(self):
  root=Path('work/lease-tests');root.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=root) as d:
   url='sqlite:///'+str(Path(d).resolve()/'queue.db');db=core.engine(url)
   a=core.request_database.set(db);b=core.request_organization.set('A')
   try:
    p=q.submit('report',{},2);jid=p['id'];out=mp.Queue();ps=[mp.Process(target=compete,args=(url,out)) for _ in range(4)]
    for x in ps:x.start()
    for x in ps:x.join(20);self.assertEqual(x.exitcode,0)
    results=[out.get(timeout=2) for _ in ps];winners=[r for r in results if r];self.assertEqual(len(winners),1)
    old=winners[0][1];time.sleep(.4);new=q.claim(db,'A',2);self.assertIsNotNone(new);self.assertFalse(q.finish(db,'A',jid,old,{}));self.assertTrue(q.heartbeat(db,'A',jid,new[1],2))
    q.cancel(db,'A',jid);self.assertFalse(q.finish(db,'A',jid,new[1],{}));self.assertEqual(q.get(db,'A',jid)['status'],'cancelled')
    with self.assertRaises(Exception):q.get(db,'B',jid)
    p=q.submit('report',{},1);q.run_once(db,'A');self.assertEqual(q.get(db,'A',p['id'])['status'],'completed')
    p=q.submit('report',{},1);q.claim(db,'A',.01);time.sleep(.03);q.claim(db,'A');self.assertEqual(q.get(db,'A',p['id'])['status'],'failed')
   finally:core.request_database.reset(a);core.request_organization.reset(b);db.dispose()
if __name__=='__main__':unittest.main()
