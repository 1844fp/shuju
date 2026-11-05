"""Standalone PostgreSQL migration/demo loader. Requires psycopg[binary]."""
import argparse, csv, hashlib, json, os, uuid
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
ROOT = Path(__file__).resolve().parent

def validate(rows):
    groups = defaultdict(list)
    for n, row in enumerate(rows, 2):
        groups[(row['voucher_no'], row['posting_date'], row['currency'])].append((n,row))
    for entries in groups.values():
        error = None
        total = Decimal(0)
        for _, r in entries:
            try:
                d,c = Decimal(r['debit']),Decimal(r['credit'])
                if not d.is_finite() or not c.is_finite() or min(d,c)<0 or (d and c) or d != d.quantize(Decimal('.01')) or c != c.quantize(Decimal('.01')):
                    raise ValueError()
                total += d-c
                if r['account_code'] not in ('1002','6001','6401','6602'): error='UNKNOWN_ACCOUNT'
            except Exception: error='INVALID_AMOUNT'
        if total and not error: error='UNBALANCED'
        yield entries,error

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['migrate','load-demo','check'])
    p.add_argument('--organization',default='demo')
    args=p.parse_args()
    rows=list(csv.DictReader((ROOT/'sample_vouchers.csv').open(encoding='utf-8-sig')))
    if args.command=='check':
        assert all(error is None for _,error in validate(rows))
        assert len(rows)==72
        print('PASS: 72 demo rows; Decimal precision and voucher balance');return
    import psycopg
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        if args.command=='migrate':
            
            for migration in sorted((ROOT/'migrations').glob('*.sql')):
                conn.execute(migration.read_text(encoding='utf-8-sig'))
            return
        org=args.organization
        digest=hashlib.sha256((ROOT/'sample_vouchers.csv').read_bytes()).hexdigest()
        batch=uuid.uuid4()
        result=conn.execute("INSERT INTO metadata.data_batch VALUES (%s,%s,'demo',%s,'loading','simulated',now()) ON CONFLICT(organization_id,sha256) DO NOTHING RETURNING id",(batch,org,digest)).fetchone()
        if not result:
            print('Already loaded; unchanged');return
        for code,name,category in [('1002','Bank','asset'),('6001','Revenue','revenue'),('6401','Cost','cost'),('6602','Expense','expense')]:
            conn.execute('INSERT INTO dim.account VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(org,code,name,category,'demo-v1'))
        for n,r in enumerate(rows,2):
            conn.execute('INSERT INTO ods.raw_vouchers VALUES(%s,%s,%s,%s::jsonb)',(org,batch,n,json.dumps(r)))
        for entries,error in validate(rows):
            for _,r in entries:
                exists=conn.execute("SELECT 1 FROM dwd.fact_journal_entry WHERE organization_id=%s AND source_system='demo' AND voucher_no=%s AND line_no=%s AND extract(year FROM posting_date)=extract(year FROM %s::date)",(org,r['voucher_no'],r['line_no'],r['posting_date'])).fetchone()
                if exists: error='DUPLICATE_BUSINESS_KEY'
            for n,r in entries:
                if error:
                    conn.execute('INSERT INTO metadata.rejected_rows VALUES(%s,%s,%s,%s,%s,%s::jsonb)',(org,batch,n,error,'Entire voucher isolated',json.dumps(r)))
                else:
                    conn.execute("INSERT INTO dwd.fact_journal_entry(organization_id,batch_id,row_number,source_system,voucher_no,line_no,posting_date,account_code,department_code,currency,debit,credit) VALUES(%s,%s,%s,'demo',%s,%s,%s,%s,%s,%s,%s,%s)",(org,batch,n,r['voucher_no'],r['line_no'],r['posting_date'],r['account_code'],r['department_code'],r['currency'],Decimal(r['debit']),Decimal(r['credit'])))
        for source,target in [('ods.raw_vouchers','dwd.fact_journal_entry'),('dwd.fact_journal_entry','dws.monthly_finance'),('dws.monthly_finance','ads.finance_dashboard')]:
            conn.execute('INSERT INTO metadata.data_lineage VALUES(%s,%s,%s,%s,%s)',(org,source,target,batch,'finance-v1'))
        conn.execute("UPDATE metadata.data_batch SET status='completed' WHERE id=%s",(batch,))
        print('Loaded simulated batch',batch)
if __name__=='__main__': main()


