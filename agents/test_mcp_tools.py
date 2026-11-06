import unittest,subprocess,sys,json,threading,os
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
class MCPTests(unittest.TestCase):
 def test_stdio_tools(self):
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    if self.headers.get('Authorization')!='Bearer test-only':self.send_response(403);self.end_headers();return
    if 'finance/budget' in self.path:value=[{'actual':'10.00','budget':'9.00'}]
    elif '/risks' in self.path:value={'items':[{'rule':'budget_exceeded'}]}
    elif '/imports/' in self.path:value={'rejected_rows':1}
    else:value=[dict(period='2026-01',currency='CNY',batch_ids=['sample'],metric_version='1.0',data_kind=['simulated'])]
    self.send_response(200);self.end_headers();self.wfile.write(json.dumps(value).encode())
  http=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=http.serve_forever,daemon=True).start()
  # Use injected local endpoint, preserve real urllib authentication/timeout behavior.
  script="from mcp_servers import finance as f; from agents.runtime import Tools; f.client=lambda:Tools('http://127.0.0.1:%d',token='test-only'); f.server.run()"%http.server_port
  messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}]
  names=['get_budget_execution','review_financial_risks','get_data_quality','get_report_evidence']
  for i,name in enumerate(names):messages.append({'jsonrpc':'2.0','id':i+3,'method':'tools/call','params':{'name':name,'arguments':{'batch_id':'sample'} if name=='get_data_quality' else {'start_period':'2026-01','end_period':'2026-12'}}})
  proc=subprocess.Popen([sys.executable,'-c',script],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   import time
   proc.stdin.write(''.join(json.dumps(m)+'\n' for m in messages));proc.stdin.flush();time.sleep(3)
   out,err=proc.communicate(timeout=20)
  finally:http.shutdown();http.server_close()
  replies={x['id']:x for x in map(json.loads,out.splitlines()) if 'id' in x}
  schemas={x['name']:x for x in replies[2]['result']['tools']}
  self.assertEqual(len(schemas),8)
  for i,name in enumerate(names):
   self.assertIn(name,schemas);self.assertFalse(replies[i+3]['result'].get('isError',False),replies[i+3])
 def test_wrong_credentials(self):
  from agents.runtime import Tools
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):self.send_response(403);self.end_headers()
  http=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=http.serve_forever,daemon=True).start()
  try:
   client=Tools('http://127.0.0.1:%s'%http.server_port,token='wrong')
   with self.assertRaisesRegex(RuntimeError,'controlled_http_failed'):client.get('finance/budget')
   self.assertEqual(client.audit[-1]['status'],'error')
  finally:http.shutdown();http.server_close()
 def test_auth_and_timeout(self):
  from agents.runtime import Tools
  from unittest.mock import patch
  import io
  with patch('agents.runtime.urlopen',side_effect=TimeoutError()) as call:
   with self.assertRaises(RuntimeError):Tools(token='test-only').get('risks')
   self.assertEqual(call.call_args.kwargs['timeout'],5)
if __name__=='__main__':unittest.main()
