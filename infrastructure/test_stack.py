import unittest,sys,socket,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import start_stack as stack
class StackTests(unittest.TestCase):
 def test_wrong_creation_identity(self):
  import psutil
  p=psutil.Process()
  self.assertIsNone(stack.owned(dict(pid=p.pid,created=p.create_time()+1,command=p.cmdline())))
 def test_wrong_command(self):
  import psutil
  p=psutil.Process()
  self.assertIsNone(stack.owned(dict(pid=p.pid,created=p.create_time(),command=['unrelated'])))
 def test_ports_closed_after_integration(self):
  for port in (8123,3123):
   with socket.socket() as s:self.assertNotEqual(s.connect_ex(('127.0.0.1',port)),0)
if __name__=='__main__':unittest.main(verbosity=2)
