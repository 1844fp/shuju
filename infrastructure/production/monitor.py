"""Independent localhost Prometheus probe. No credentials or financial payloads exported."""
import time,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

def probe(url):
 start=time.monotonic()
 try:
  with urllib.request.urlopen(url,timeout=3) as r:up=int(r.status==200)
 except Exception:up=0
 return f'finagent_up {up}\nfinagent_probe_duration_seconds {time.monotonic()-start:.6f}\n'

def serve(target,port):
 class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
   if self.path!='/metrics':self.send_error(404);return
   body=probe(target).encode();self.send_response(200);self.send_header('Content-Type','text/plain; version=0.0.4');self.end_headers();self.wfile.write(body)
  def log_message(self,*args):pass
 ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--target',default='http://127.0.0.1:8000/api/v1/ready');p.add_argument('--port',type=int,default=9118);a=p.parse_args();serve(a.target,a.port)
