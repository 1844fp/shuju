"""40 independent deterministic financial evaluations; synthetic isolated fixtures."""
import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for path in ('work/runtime','work/agent-runtime','work/export-runtime','backend','.') :sys.path.insert(0,str(ROOT/path))
from finance_risk_engine import evaluate,money
from agents.harness import Harness,ROLES

def row(**kw):return dict(id='a',currency='CNY',date='2026-11-06',**kw)
def finding(rule,rows):return next(r for r in evaluate(rows,'CNY')['rules'] if r['rule']==rule)
class BusinessEvaluation(unittest.TestCase):pass
CASES=[
('large_amount',[row(amount='10000.01')],True),('large_amount',[row(amount='10000.00')],False),('large_amount',[row(amount='-10000.01')],True),('large_amount',[row(amount='0.00')],False),
('weekend',[dict(row(),date='2026-11-07')],True),('weekend',[row()],False),('weekend',[dict(row(),date='2026-11-08')],True),('weekend',[dict(row(),date='2026-11-09')],False),
('duplicate_expense',[row(amount='1',employee='e',invoice='i'),dict(row(amount='1',employee='e',invoice='i'),id='b')],True),('duplicate_expense',[row(amount='1',employee='e',invoice='i')],False),('duplicate_expense',[row(amount='1',employee='e',invoice='i'),dict(row(amount='1',employee='x',invoice='i'),id='b')],False),('duplicate_expense',[row(amount='1',employee='e',invoice='i'),dict(row(amount='2',employee='e',invoice='i'),id='b')],False),
('split_expense',[row(amount='5000',employee='e'),dict(row(amount='5000',employee='e'),id='b')],True),('split_expense',[row(amount='4999.99',employee='e'),dict(row(amount='5000',employee='e'),id='b')],False),('split_expense',[row(amount='10000',employee='e')],False),('split_expense',[row(amount='-5000',employee='e'),dict(row(amount='5000',employee='e'),id='b')],False),
('new_supplier',[row(amount='10001',supplier='s',supplier_created='2026-10-07')],True),('new_supplier',[row(amount='10001',supplier='s',supplier_created='2026-10-06')],False),('new_supplier',[row(amount='10000',supplier='s',supplier_created='2026-11-06')],False),('new_supplier',[row(amount='10001',supplier='s',supplier_created='2026-11-07')],False),
('budget_exceeded',[row(amount='100.01',budget='100',department='d')],True),('budget_exceeded',[row(amount='100',budget='100',department='d')],False),('budget_exceeded',[row(amount='99.99',budget='100',department='d')],False),('budget_exceeded',[row(amount='0',budget='0',department='d')],False),
('unbalanced_voucher',[row(voucher_id='v',debit='0.01',credit='0')],True),('unbalanced_voucher',[row(voucher_id='v',debit='1',credit='1')],False),('unbalanced_voucher',[row(voucher_id='v',debit='1',credit='0'),dict(row(voucher_id='v',debit='0',credit='1'),id='b')],False),('unbalanced_voucher',[row(voucher_id='v',debit='0',credit='0')],False),
('expense_growth',[row(amount='150.01',previous_amount='100',department='d')],True),('expense_growth',[row(amount='150',previous_amount='100',department='d')],False),('expense_growth',[row(amount='149.99',previous_amount='100',department='d')],False),('expense_growth',[row(amount='100',previous_amount='0',department='d')],False)]
def make_case(rule,rows,hit):
 def test(self):
  result=finding(rule,rows);self.assertEqual(bool(result['findings']),hit)
  if hit:
   self.assertEqual(result['findings'][0]['evidence_ids'],sorted(r['id'] for r in rows));self.assertEqual(result['findings'][0]['classification'],'risk_lead')
 return test
for n,(rule,rows,hit) in enumerate(CASES,1):setattr(BusinessEvaluation,f'test_{n:02d}_{rule}',make_case(rule,rows,hit))
class HarnessEvaluation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work');self.h=Harness(Path(self.tmp.name)/'check.sqlite');self.calls=[]
  def tool(q,r):self.calls.append(1);return {'evidence_ids':['simulated-source']}
  self.tools={r:tool for r in ROLES}
 def tearDown(self):self.tmp.cleanup()
 def test_33_five_roles(self):self.assertEqual(set(self.h.run('t','a',{},self.tools)['results']),set(ROLES))
 def test_34_recovery_reuses(self):
  self.h.run('t','a',{},self.tools);self.h.run('t','a',{},self.tools);self.assertEqual(len(self.calls),5)
 def test_35_tenant_isolation(self):
  self.h.run('t','a',{},self.tools);self.h.run('t','b',{},self.tools);self.assertEqual(len(self.calls),10)
 def test_36_approval_gate(self):
  r=self.h.run('t','a',{},self.tools,approved=False);self.assertEqual(r['status'],'awaiting_approval');self.assertNotIn('report',r['results'])
 def test_37_approval_resume(self):
  self.h.run('t','a',{},self.tools,approved=False);self.assertEqual(self.h.run('t','a',{},self.tools)['status'],'completed');self.assertEqual(len(self.calls),5)
 def test_38_query_immutable(self):
  self.h.run('t','a',{},self.tools)
  with self.assertRaises(ValueError):self.h.run('t','a',{'currency':'USD'},self.tools)
 def test_39_call_budget(self):self.assertEqual(self.h.run('t','a',{},self.tools,max_calls=1)['status'],'budget_exhausted')
 def test_40_transient_retries(self):
  count=[]
  def fail(q,r):count.append(1);raise TimeoutError()
  self.tools['data']=fail;self.assertEqual(self.h.run('t','a',{},self.tools)['status'],'failed');self.assertEqual(len(count),2)
if __name__=='__main__':unittest.main(verbosity=2)
