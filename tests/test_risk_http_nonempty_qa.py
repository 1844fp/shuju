import unittest,threading,socket,time,csv,io,json,os,tempfile
from pathlib import Path
from unittest.mock import patch
import test_identity as fixture
import app as core
import httpx,uvicorn
class RiskHTTPNonempty(unittest.TestCase):
 def test_real_tcp_committed_budget_growth_and_quarantine(self):
  f=fixture.IdentityTests();f.setUp();self.addCleanup(f.tearDown);server=None;thread=None
  with tempfile.TemporaryDirectory(dir='work') as tmp,patch.dict(os.environ,{'FINAGENT_HARNESS_PATH':str(Path(tmp)/'h.sqlite')}):
   try:
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(core.app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run);thread.start()
    for _ in range(100):
     if server.started:break
     time.sleep(.02)
    with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as c:
     self.assertEqual(c.post('/api/v1/auth/login',json={'username':'admin-a','password':'Test-password-123'}).status_code,200)
     def ingest(year,amount,bad=False):
      rows=[dict(posting_date=f'{year}-11-06',voucher_no=f'QA-{year}-{bad}',line_no=str(i),account_code=code,department_code='D01',currency='CNY',debit=amount if i==1 else '0',credit=('0.01' if bad else amount) if i==2 else '0') for i,code in ((1,'6602'),(2,'1002'))]
      out=io.StringIO();w=csv.DictWriter(out,fieldnames=core.FIELDS);w.writeheader();w.writerows(rows)
      p=c.post('/api/v1/imports/preview',files={'file':('qa.csv',out.getvalue().encode())});self.assertEqual(p.status_code,200,p.text)
      b=c.post('/api/v1/imports',json={'preview_id':p.json()['preview_id']});self.assertEqual(b.status_code,202,b.text);return b.json()
     prior=ingest(2025,'100.00');current=ingest(2026,'200.01');bad=ingest(2026,'9.99',True);self.assertEqual(bad['accepted_rows'],0);self.assertEqual(bad['rejected_rows'],2);self.assertTrue(all('平衡' in x['message'] for x in bad['errors']))
     budget=c.post('/api/v1/finance/registers',json=dict(external_id='qa-budget',kind='budget',period='2026-11',department='D01',amount='150.00'));self.assertEqual(budget.status_code,201,budget.text)
     supplier=c.post('/api/v1/finance-workbench/suppliers',json=dict(supplier='S',registered_date='2026-11-01',source_reference='simulated:registration',data_kind='simulated'));self.assertEqual(supplier.status_code,201,supplier.text)
     for i,amount in enumerate(('6000.00','6000.00','10000.01')):
      r=c.post('/api/v1/finance-workbench/documents',json=dict(external_id=f'qa-{i}',kind='expense',date='2026-11-07',currency='CNY',amount=amount,employee='E',invoice='I',supplier='S',data_kind='simulated'));self.assertEqual(r.status_code,201,r.text)
     r=c.post('/api/v1/agent-runs',json={'start_period':'2026-11','end_period':'2026-11'});self.assertEqual(r.status_code,201,r.text);result=r.json();rules={x['rule']:x for x in result['results']['audit']['rules']}
     for name in ('duplicate_expense','large_amount','split_expense','weekend','budget_exceeded','expense_growth','new_supplier'):
      self.assertEqual(rules[name]['status'],'evaluated');self.assertTrue(rules[name]['findings'],name);self.assertTrue(all(x['evidence_ids'] for x in rules[name]['findings']))
     self.assertEqual(rules['unbalanced_voucher']['status'],'evaluated');self.assertFalse(rules['unbalanced_voucher']['findings'])
     self.assertEqual(result['results']['budget'][0]['actual'],'200.01');self.assertIn(bad['batch_id'],result['results']['data']['batch_ids'])
     report={'transport':'real TCP HTTP','rules':list(rules.values()),'quarantined_batch':bad,'prior_batch_id':prior['batch_id'],'current_batch_id':current['batch_id'],'coverage':'seven rules positive including registered supplier; balanced committed voucher explicit negative; rejected unbalanced batch quality retained'}
     path=Path('work/redesign/risk-http-nonempty.json');path.write_text(json.dumps(report,indent=2),encoding='utf-8')
   finally:
    if server:server.should_exit=True
    if thread:thread.join(10)

if __name__=='__main__':unittest.main(verbosity=2)
