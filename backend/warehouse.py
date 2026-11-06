"""Controlled publication into the native PostgreSQL warehouse, with read-only metrics."""
import os,json
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
import app as core

def org():return core.request_organization.get()
def connection():
    import psycopg
    url=os.getenv('FINAGENT_WAREHOUSE_URL')
    if not url:raise HTTPException(503,'warehouse_not_configured')
    try:return psycopg.connect(url)
    except psycopg.Error:raise HTTPException(503,'warehouse_unavailable') from None

def read_connection():
    if os.getenv('FINAGENT_WAREHOUSE_PRODUCTION')!='1':return connection()
    import psycopg
    try:readers=json.loads(os.getenv('FINAGENT_WAREHOUSE_READERS_JSON') or '{}');url=readers.get(org())
    except (ValueError,AttributeError):raise HTTPException(503,'warehouse_reader_configuration_invalid') from None
    if not url:raise HTTPException(503,'warehouse_organization_reader_missing')
    try:return psycopg.connect(url)
    except psycopg.Error:raise HTTPException(503,'warehouse_reader_unavailable') from None

def publish(batch_id):
    batch=core.batch(batch_id)
    if batch['accepted_rows']==0:raise HTTPException(422,'批次没有通过校验的记录')
    with core.current_db().connect() as src:
        b=src.execute(select(core.batches).where(core.batches.c.id==batch_id)).mappings().one()
        originals=src.execute(select(core.raw).where(core.raw.c.batch_id==batch_id)).mappings().all()
        entries=src.execute(select(core.facts).where(core.facts.c.batch_id==batch_id)).mappings().all()
    from erp_imports import publication_source
    provenance=publication_source(batch_id)
    from erp_accounts import listing
    approved={x['code']:x for x in listing()}
    with connection() as c:
        existing=c.execute('SELECT id FROM metadata.data_batch WHERE organization_id=%s AND sha256=%s',(org(),b['sha256'])).fetchone()
        if existing:return {'status':'already_published','batch_id':str(existing[0]),'organization_id':org()}
        c.execute('INSERT INTO metadata.data_batch(id,organization_id,source_name,sha256,status,data_kind) VALUES(%s,%s,%s,%s,%s,%s)',(batch_id,org(),b['source'],b['sha256'],'completed',b['kind']))
        dimensions={}
        for entry in entries:
            code=json.loads(entry['payload'])['account_code'];category=entry['category']
            if code in dimensions and dimensions[code]!=category:raise HTTPException(409,'同一批次科目类别冲突')
            dimensions[code]=category
        for code,category in dimensions.items():
            old=c.execute('SELECT category FROM dim.account WHERE organization_id=%s AND code=%s',(org(),code)).fetchone()
            if old and old[0]!=category:raise HTTPException(409,'数仓科目类别与接入事实冲突，拒绝静默重分类')
            version=provenance[0]['account_catalog_sha256'] if provenance else 'builtin-1.0'
            c.execute('INSERT INTO dim.account VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(org(),code,approved.get(code,{}).get('name',code),category,version))
        for x in originals:c.execute('INSERT INTO ods.raw_vouchers VALUES(%s,%s,%s,%s::jsonb)',(org(),batch_id,x['row_number'],x['payload']))
        for x in entries:
            row=json.loads(x['payload']);key=json.loads(x['business_key'])
            c.execute('INSERT INTO dwd.fact_journal_entry(organization_id,batch_id,row_number,source_system,voucher_no,line_no,posting_date,account_code,department_code,currency,debit,credit) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(org(),batch_id,int(x['row_number']) if 'row_number' in x else next(r['row_number'] for r in originals if json.loads(r['payload'])==row),key[0],row['voucher_no'],int(row['line_no']),row['posting_date'],row['account_code'],row['department_code'],row['currency'],Decimal(x['debit_cents'])/100,Decimal(x['credit_cents'])/100))
        for e in batch['errors']:
            original=next(x['payload'] for x in originals if x['row_number']==e['row_number'])
            c.execute('INSERT INTO metadata.rejected_rows VALUES(%s,%s,%s,%s,%s,%s::jsonb)',(org(),batch_id,e['row_number'],'IMPORT_VALIDATION',e['message'],original))
        if provenance:
            value,original=provenance
            evidence={k:value.get(k) for k in ('id','ledger_id','profile','quality','cleaning_version','cleaning_token','account_catalog_sha256','cleaned_by','options','created_at','cleaned_at','committed_at')}
            c.execute('INSERT INTO metadata.erp_snapshot VALUES(%s,%s,%s,%s,%s,%s::jsonb)',(org(),batch_id,original['digest'],value['source_name'],original['content'],json.dumps(evidence,ensure_ascii=False)))
            for row in value['cleaned_rows']:
                c.execute('INSERT INTO ods.erp_source_row VALUES(%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb)',(org(),batch_id,row['row_number'],json.dumps(row['raw'],ensure_ascii=False),json.dumps(row['normalized'],ensure_ascii=False) if row['normalized'] is not None else None,row['status'],json.dumps(row['errors'],ensure_ascii=False),json.dumps(row['changes'],ensure_ascii=False)))
            for source,target in [('metadata.erp_snapshot','ods.erp_source_row'),('ods.erp_source_row','ods.raw_vouchers')]:c.execute('INSERT INTO metadata.data_lineage VALUES(%s,%s,%s,%s,%s)',(org(),source,target,batch_id,value['cleaning_version']))
        for a,z in [('ods.raw_vouchers','dwd.fact_journal_entry'),('dwd.fact_journal_entry','dws.monthly_finance'),('dws.monthly_finance','ads.finance_dashboard')]:c.execute('INSERT INTO metadata.data_lineage VALUES(%s,%s,%s,%s,%s)',(org(),a,z,batch_id,'1.0'))
    return {'status':'published','batch_id':batch_id,'organization_id':org(),'accepted_rows':len(entries)}

def metrics(start_period='2026-01',end_period='2026-12',currency='CNY'):
    # Shared validation does not query arbitrary user supplied SQL.
    from agents.runtime import Query
    Query(start_period=start_period,end_period=end_period,currency=currency)
    with read_connection() as c:
        c.execute('SET LOCAL ROLE finagent_reader');c.execute('SET LOCAL statement_timeout=5000');c.execute("SELECT set_config('app.organization_id',%s,true)",(org(),))
        rows=c.execute('SELECT period,currency,revenue,cost,expense,gross_profit,operating_profit,gross_margin,batch_ids,metric_version,data_kinds FROM ads.finance_dashboard WHERE organization_id=%s AND period BETWEEN %s AND %s AND currency=%s ORDER BY period LIMIT 1000',(org(),start_period,end_period,currency)).fetchall()
    keys=['period','currency','revenue','cost','expense','gross_profit','operating_profit','gross_margin','batch_ids','metric_version','data_kind']
    return [{k: str(v) if isinstance(v,Decimal) else [str(i) for i in v] if isinstance(v,list) else v for k,v in zip(keys,row)} for row in rows]

def install(app):
    @app.post('/api/v1/warehouse/publish/{batch_id}')
    def publish_batch(batch_id:str):return publish(batch_id)
    @app.get('/api/v1/warehouse/metrics')
    def query(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'):return metrics(start_period,end_period,currency)
