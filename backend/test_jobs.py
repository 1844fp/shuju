import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import app as core
import jobs
class Tests(unittest.TestCase):
 def test_queue(self):
  with tempfile.TemporaryDirectory() as d:
   a=core.engine('sqlite:///'+str(Path(d)/'a.db'));b=core.engine('sqlite:///'+str(Path(d)/'b.db'))
   token=core.request_database.set(a)
   try:
    p=jobs.submit('report',{},dispatch=False)
    with self.assertRaises(Exception):jobs.read(b,p['task_id'])
    with patch.object(jobs,'execute',side_effect=lambda p: {'bound':core.current_db() is a}):jobs.worker(a,p['task_id'])
    self.assertEqual(jobs.read(a,p['task_id'])['result'],{'bound':True})
    p=jobs.submit('report',{},max_retries=1,dispatch=False)
    with patch.object(jobs,'execute',side_effect=RuntimeError('secret')):jobs.worker(a,p['task_id'])
    r=jobs.read(a,p['task_id']);self.assertEqual(r['status'],'failed');self.assertEqual(r['attempts'],2);self.assertNotIn('secret',str(r))
    p=jobs.submit('report',{},dispatch=False);jobs.cancel(a,p['task_id']);jobs.worker(a,p['task_id']);self.assertEqual(jobs.read(a,p['task_id'])['status'],'cancelled')
    p=jobs.submit('report',{},max_retries=1,dispatch=False);p.update(status='running',attempts=1);jobs.write(a,p)
    self.assertIn(p['task_id'],jobs.recover(a,dispatch=False))
    jobs.worker(a,p['task_id']);self.assertEqual(jobs.read(a,p['task_id'])['status'],'completed')
    with self.assertRaises(Exception):jobs.submit('analysis',{},dispatch=False)
   finally:core.request_database.reset(token);a.dispose();b.dispose()
if __name__=='__main__':unittest.main()
