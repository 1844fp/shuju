import unittest,tempfile,time,json,io,zipfile,threading,socket
from pathlib import Path
from decimal import Decimal
import app as core,report_exports
from agents.harness import Harness,ROLES
from openpyxl import load_workbook
import fitz
OUT=Path('work/redesign/r06-r12-r13');OUT.mkdir(parents=True,exist_ok=True)
class Acceptance(unittest.TestCase):
 def test_long_three_format_snapshot(self):
  rows=[]
  for i in range(60):
   amount=f'{100000+i}.01';rows.append(dict(period=f'{2021+i//12}-{i%12+1:02d}',currency='CNY',revenue=amount,cost='0.00',expense='0.00',gross_profit=amount,operating_profit=amount,gross_margin='1',metric_version='1.0',data_kind=['simulated'],batch_ids=[f'QA-source-{i:03d}']))
  pdf=report_exports.pdf_bytes(rows,'2021-01','2025-12','CNY');word=report_exports.docx_bytes(rows,'2021-01','2025-12','CNY');excel=report_exports.xlsx_bytes(rows,'2021-01','2025-12','CNY')
  for name,data in [('long.pdf',pdf),('long.docx',word),('long.xlsx',excel)]:(OUT/name).write_bytes(data)
  with fitz.open(stream=pdf,filetype='pdf') as d:
   self.assertGreater(len(d),5)
   for row in rows:
    containing=[page for page in d if row['batch_ids'][0] in page.get_text()]
    self.assertEqual(len(containing),1);self.assertIn(row['revenue'],containing[0].get_text())
   pdftext=''.join(p.get_text() for p in d);pages=len(d)
   for i in (0,len(d)-1):d[i].get_pixmap().save(str(OUT/f'pdf-{i+1}.png'))
  import xml.etree.ElementTree as ET
  with zipfile.ZipFile(io.BytesIO(word)) as z:wordtext=''.join(ET.fromstring(z.read('word/document.xml')).itertext())
  w=load_workbook(io.BytesIO(excel));exceltext=' '.join(str(c.value) for row in w.active for c in row);w.close()
  for row in rows:
   for text in (pdftext,wordtext,exceltext):self.assertIn(row['revenue'],text);self.assertIn(row['batch_ids'][0],text)
  (OUT/'report-result.json').write_text(json.dumps({'rows':60,'pdf_pages':pages,'all_60_amounts_and_sources_in_three_formats':True,'docx_visual':'pending Word render'}))
 def test_real_business_tool_latency_recovery(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   db=core.engine('sqlite:///'+str(Path(d).resolve()/'db'));import csv,io
   rows=list(csv.DictReader(io.StringIO((core.ROOT/'data_platform/sample_vouchers.csv').read_text(encoding='utf-8-sig'))));core.ingest(db,rows,'qa','qa',kind='simulated')
   token=core.request_database.set(db);calls=[]
   try:
    def tool(q,previous):time.sleep(.02);calls.append(1);return core.finance(**q)
    h=Harness(Path(d)/'h.sqlite');tools={r:tool for r in ROLES};start=time.monotonic();a=h.run('t','qa',{},tools);first=time.monotonic()-start;start=time.monotonic();b=h.run('t','qa',{},tools);recovery=time.monotonic()-start
    self.assertEqual(a['status'],'completed');self.assertEqual(b['status'],'completed');self.assertEqual(len(calls),5);self.assertTrue(all(t['status']=='reused' for t in b['trace']));self.assertEqual(b['results']['analysis'][0]['revenue'],'107500.00');self.assertGreaterEqual(first,.1)
    (OUT/'latency.json').write_text(json.dumps({'first_seconds':first,'recovery_seconds':recovery,'actual_metric_calls':len(calls),'injected_delay_per_call_seconds':.02,'all_reused':True}))
   finally:core.request_database.reset(token);db.dispose()
 def test_real_http_eight_rule_envelope(self):
  import test_identity as fixture,httpx,uvicorn
  f=fixture.IdentityTests();f.setUp();server=None;thread=None
  try:
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
   server=uvicorn.Server(uvicorn.Config(core.app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run);thread.start()
   for _ in range(100):
    if server.started:break
    time.sleep(.02)
   with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as c:
    self.assertEqual(c.post('/api/v1/auth/login',json={'username':'admin-a','password':'Test-password-123'}).status_code,200)
    for i in range(2):
     r=c.post('/api/v1/finance-workbench/documents',json=dict(external_id=f'qa-{i}',kind='expense',date='2026-11-07',currency='CNY',amount='6000.00',employee='E',invoice='I',data_kind='simulated'));self.assertEqual(r.status_code,201,r.text)
    # Agent audit adapter evaluates ledger/department sources as well.
    r=c.post('/api/v1/agent-runs',json={});self.assertEqual(r.status_code,201,r.text);rules=r.json()['results']['audit']['rules'];self.assertEqual(len(rules),8)
    for rule in ('duplicate_expense','split_expense','weekend'):self.assertTrue(next(x for x in rules if x['rule']==rule)['findings'])
    self.assertFalse(next(x for x in rules if x['rule']=='large_amount')['findings'])
    for rule in ('new_supplier','budget_exceeded','unbalanced_voucher','expense_growth'):self.assertEqual(next(x for x in rules if x['rule']==rule)['status'],'not_evaluated')
    (OUT/'http-risk.json').write_text(json.dumps({'transport':'real TCP HTTP','rules':rules,'scope':'missing fields explicitly not_evaluated; no fabricated hits'}))
  finally:
   if server:server.should_exit=True
   if thread:thread.join(10)
   f.tearDown()
if __name__=='__main__':unittest.main(verbosity=2)
