"""Deterministic, explicitly synthetic finance fixtures; never imports into a database."""
import argparse,csv,hashlib,json,random
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='finance-demo-1.0'
def money(cents):return format(Decimal(cents)/100,'.2f')
def generate(seed=20261106):
 rng=random.Random(seed);tables={k:[] for k in ('vouchers','invoices','expenses','bank','budgets','suppliers')}
 def row(identifier,day,**values):return dict(id=identifier,posting_date=day,period=day[:7],currency='CNY',data_kind='simulated',source='fictional-demo-company',batch_id='demo-'+str(seed),metric_version=VERSION,**values)
 for i in range(5000):
  day=(date(2026,1,1)+timedelta(days=i%365)).isoformat();amount=money(rng.randrange(10000,100000));dept='D%02d'%(i%10+1)
  for line,code,debit,credit in [(1,'1002',amount,'0.00'),(2,'6001','0.00',amount)]:
   tables['vouchers'].append(row('V%05d-%d'%(i,line),day,voucher_no='V%05d'%i,line_no=str(line),account_code=code,department_code=dept,debit=debit,credit=credit))
 for i in range(1000):
  day=(date(2026,1,1)+timedelta(days=i%365)).isoformat();amount=money(rng.randrange(10000,50000))
  tables['invoices'].append(row('I%04d'%i,day,invoice_no='INV%04d'%i,supplier_id='S%02d'%(i%50+1),amount=amount))
  tables['bank'].append(row('B%04d'%i,day,reference='I%04d'%i,supplier_id='S%02d'%(i%50+1),inflow='0.00',outflow=amount))
 for i in range(500):
  day=(date(2026,1,1)+timedelta(days=i%365)).isoformat()
  tables['expenses'].append(row('E%04d'%i,day,employee_id='EMP%03d'%(i%70),invoice_no='INV%04d'%i,department_code='D%02d'%(i%10+1),amount=money(rng.randrange(10000,50000))))
 for month in range(1,13):
  for dept in range(1,11):tables['budgets'].append(row('BU%02d-%02d'%(month,dept),'2026-%02d-01'%month,department_code='D%02d'%dept,amount='100000.00'))
 for i in range(50):tables['suppliers'].append(row('S%02d'%(i+1),'2026-01-01',name='模拟供应商%02d'%(i+1)))
 # Deliberate positive examples; truth is not an exhaustive set of all possible rule matches.
 tables['vouchers'][1]['credit']=money(int(Decimal(tables['vouchers'][0]['debit'])*100)-1)
 for key in ('posting_date','period','employee_id','invoice_no','amount'):tables['expenses'][1][key]=tables['expenses'][0][key]
 tables['invoices'][1]['invoice_no']=tables['invoices'][0]['invoice_no']
 tables['bank'][2]['outflow']='900000.00'
 tables['budgets'][0]['amount']='1.00'
 truth=[dict(rule='unbalanced_voucher',records=['V00000-1','V00000-2'],difference='0.01'),dict(rule='duplicate_expense',records=['E0000','E0001']),dict(rule='duplicate_invoice',records=['I0000','I0001']),dict(rule='large_payment',records=['B0002'],threshold='100000.00'),dict(rule='budget_exceeded',records=['BU01-01'],basis='January D01 expense register')]
 return tables,truth

def verify(tables):
 assert {k:len(v) for k,v in tables.items()}==dict(vouchers=10000,invoices=1000,expenses=500,bank=1000,budgets=120,suppliers=50)
 assert len({r['voucher_no'] for r in tables['vouchers']})==5000
 for rows in tables.values():
  assert len({r['id'] for r in rows})==len(rows)
  assert all(r['data_kind']=='simulated' for r in rows)
 for offset in range(0,10000,2):
  pair=tables['vouchers'][offset:offset+2];difference=sum(Decimal(r['debit'])-Decimal(r['credit']) for r in pair)
  assert difference==(Decimal('.01') if offset==0 else Decimal(0))
 return dict(passed=True,counts={k:len(v) for k,v in tables.items()},voucher_count=5000,unbalanced_vouchers=1)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'work/redesign/demo'));parser.add_argument('--seed',type=int,default=20261106);args=parser.parse_args()
 target=Path(args.output).resolve()
 if not target.is_relative_to((ROOT/'work').resolve()):raise ValueError('output must remain under project work/')
 if target.exists() and any(target.iterdir()):raise ValueError('output is nonempty; use a fresh directory')
 tables,truth=generate(args.seed);result=verify(tables);assert (tables,truth)==generate(args.seed)
 target.mkdir(parents=True,exist_ok=True);manifest={}
 for name,rows in tables.items():
  path=target/(name+'.csv')
  with path.open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
  manifest[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
 (target/'truth.json').write_text(json.dumps(dict(version=VERSION,seed=args.seed,scope='known positive examples, not exhaustive labels or fraud findings',cases=truth),ensure_ascii=False,indent=2),encoding='utf-8')
 (target/'manifest.json').write_text(json.dumps(dict(**result,seed=args.seed,version=VERSION,files=manifest),indent=2),encoding='utf-8')
 print(json.dumps(result))
if __name__=='__main__':main()
