"""New routes exercised with real identity middleware and isolated organization stores."""
import unittest,os
import test_identity as fixture
class RedesignHTTP(unittest.TestCase):
 def setUp(self):
  self.f=fixture.IdentityTests();self.f.setUp();self.addCleanup(self.f.tearDown)
 def test_document_scope_approval_evidence(self):
  f=self.f;f.login('admin-a');c=f.client
  p=dict(external_id='qa-expense',kind='expense',date='2026-11-06',currency='CNY',amount='100.01',data_kind='simulated')
  r=c.post('/api/v1/finance-workbench/documents',json=p);self.assertEqual(r.status_code,201,r.text);jid=r.json()['id'];base='/api/v1/finance-workbench/documents/'+jid
  self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'qa'}).status_code,403)
  f.login('admin-b');self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'qa'}).status_code,404)
  self.assertEqual(c.get('/api/v1/finance-workbench/documents').json(),[])
  f.login('reader-a');self.assertEqual(c.post('/api/v1/finance-workbench/documents',json=p).status_code,403)
 def test_agent_scope_and_resume(self):
  f=self.f;f.login('admin-a');c=f.client
  r=c.post('/api/v1/agent-runs',json={});self.assertEqual(r.status_code,201,r.text);jid=r.json()['task_id']
  self.assertIn(r.json()['status'],('completed','awaiting_approval'))
  f.login('admin-b');self.assertEqual(c.get('/api/v1/agent-runs/'+jid).status_code,404);self.assertEqual(c.post('/api/v1/agent-runs/'+jid+'/resume').status_code,404)
 def test_nonempty_agent_approval_and_three_exports(self):
  import identity,io,zipfile,xml.etree.ElementTree as ET
  from openpyxl import load_workbook
  import fitz
  f=self.f;identity.create_user('reviewer-a','Test-password-123',f.a['id'],'org_admin');f.login('admin-a');c=f.client
  data=(fixture.r/'data_platform/sample_vouchers.csv').read_bytes()
  preview=c.post('/api/v1/imports/preview',files={'file':('simulated.csv',data)});self.assertEqual(preview.status_code,200,preview.text)
  batch=c.post('/api/v1/imports',json={'preview_id':preview.json()['preview_id']});self.assertEqual(batch.status_code,202,batch.text);bid=batch.json()['batch_id']
  self.assertEqual(batch.json()['accepted_rows'],72)
  b=c.post('/api/v1/finance/registers',json=dict(external_id='qa-budget',kind='budget',period='2026-01',department='D01',amount='10000'));self.assertEqual(b.status_code,201,b.text)
  run=c.post('/api/v1/agent-runs',json={});self.assertEqual(run.status_code,201,run.text);r=run.json();jid=r['task_id'];self.assertEqual(r['status'],'awaiting_approval')
  self.assertEqual(r['results']['analysis'][0]['revenue'],'107500.00');self.assertEqual(r['results']['budget'][0]['actual'],'18500.00')
  rules=r['results']['audit']['rules'];self.assertEqual(len(rules),8);self.assertTrue(next(x for x in rules if x['rule']=='budget_exceeded')['findings']);self.assertFalse(next(x for x in rules if x['rule']=='unbalanced_voucher')['findings'])
  base='/api/v1/agent-runs/'+jid;self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'qa'}).status_code,403)
  f.login('reviewer-a');self.assertEqual(c.post(base+'/review',json={'decision':'approved','reason':'qa'}).status_code,200)
  result=c.post(base+'/resume').json();self.assertEqual(result['status'],'completed');self.assertIn(bid,result['results']['report']['sources']['batch_ids']);self.assertEqual(sum(x['status']=='reused' for x in result['trace']),4)
  for ext in ('docx','xlsx','pdf'):
   response=c.get('/api/v1/exports/finance.'+ext);self.assertEqual(response.status_code,200,response.text[:200] if response.status_code!=200 else '')
   if ext=='docx':
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:text=''.join(ET.fromstring(z.read('word/document.xml')).itertext())
   elif ext=='xlsx':
    w=load_workbook(io.BytesIO(response.content));text=' '.join(str(x.value) for row in w.active for x in row);w.close()
   else:
    with fitz.open(stream=response.content,filetype='pdf') as d:text=''.join(p.get_text() for p in d)
   self.assertIn('107500.00',text);self.assertIn(bid,text)
if __name__=='__main__':unittest.main(verbosity=2)
