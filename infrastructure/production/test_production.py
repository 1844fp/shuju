import unittest,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import monitor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
class Tests(unittest.TestCase):
 def test_probe_up_and_down(self):
  class H(BaseHTTPRequestHandler):
   def do_GET(self):self.send_response(200);self.end_headers()
   def log_message(self,*args):pass
  s=ThreadingHTTPServer(('127.0.0.1',0),H);t=threading.Thread(target=s.serve_forever);t.start()
  url='http://127.0.0.1:'+str(s.server_port)
  try:self.assertIn('finagent_up 1',monitor.probe(url))
  finally:s.shutdown();s.server_close();t.join()
  self.assertIn('finagent_up 0',monitor.probe(url))
if __name__=='__main__':unittest.main(verbosity=2)
