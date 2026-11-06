import csv, io, json, hashlib, os, uuid, re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from collections import defaultdict
from fastapi import FastAPI, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Text, select
from pydantic import BaseModel

ROOT=Path(__file__).resolve().parents[1]
from contextvars import ContextVar
request_database=ContextVar('request_database',default=None)
request_organization=ContextVar('request_organization',default='local-demo')
request_actor=ContextVar('request_actor',default=None)
def current_db(): return request_database.get() if request_database.get() is not None else app.state.db
ACCOUNTS={'1002':'asset','6001':'revenue','6401':'cost','6602':'expense'}
FIELDS=['posting_date','voucher_no','line_no','account_code','department_code','currency','debit','credit']
meta=MetaData()
batches=Table('metadata_data_batch',meta,Column('id',String,primary_key=True),Column('sha256',String,unique=True),Column('source',String),Column('kind',String),Column('status',String),Column('details',Text))
raw=Table('ods_raw_vouchers',meta,Column('id',String,primary_key=True),Column('batch_id',String),Column('row_number',Integer),Column('payload',Text))
facts=Table('dwd_fact_journal_entry',meta,Column('id',String,primary_key=True),Column('business_key',String,unique=True),Column('batch_id',String),Column('period',String),Column('currency',String),Column('category',String),Column('debit_cents',Integer),Column('credit_cents',Integer),Column('payload',Text))
previews=Table('metadata_preview',meta,Column('id',String,primary_key=True),Column('digest',String),Column('source',String),Column('payload',Text),Column('created',String))
audit=Table('metadata_audit',meta,Column('id',String,primary_key=True),Column('action',String),Column('resource',String),Column('created',String))
def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
def money(x): return format(Decimal(x)/100,'.2f')
def cents(x):
    d=Decimal(str(x or '0'))
    if not d.is_finite() or d<0 or d!=d.quantize(Decimal('.01')) or d>Decimal('999999999999.99'): raise ValueError('金额须为非负、最多两位小数且不超过999999999999.99')
    return int(d*100)
def engine(url=None):
    e=create_engine(url or os.getenv('DATABASE_URL',f'sqlite:///{ROOT / "local.db"}'))
    meta.create_all(e)
    from sqlalchemy import text
    with e.begin() as c:
        c.execute(text("CREATE VIEW IF NOT EXISTS dws_monthly_finance AS SELECT period, currency, SUM(CASE WHEN category='revenue' THEN credit_cents-debit_cents ELSE 0 END) AS revenue_cents, SUM(CASE WHEN category='cost' THEN debit_cents-credit_cents ELSE 0 END) AS cost_cents, SUM(CASE WHEN category='expense' THEN debit_cents-credit_cents ELSE 0 END) AS expense_cents FROM dwd_fact_journal_entry GROUP BY period,currency"))
        c.execute(text("CREATE VIEW IF NOT EXISTS ads_finance_dashboard AS SELECT *, revenue_cents-cost_cents-expense_cents AS operating_profit_cents FROM dws_monthly_finance"))
    return e

def ingest(e, rows, digest, source, source_system='local', kind='uploaded', account_catalog=None, approval_reference=None, trusted_bootstrap=False):
    import enterprise_controls as controls
    controls.initialize(e)
    catalog=ACCOUNTS if account_catalog is None else account_catalog
    if not isinstance(catalog,dict) or any(x not in {'asset','liability','equity','revenue','cost','expense','other'} for x in catalog.values()):raise ValueError('服务端科目分类无效')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,50}',source_system): raise ValueError('来源系统只能使用字母、数字、下划线和连字符')
    with e.begin() as c:
        old=c.execute(select(batches).where(batches.c.sha256==digest)).mappings().first()
        if old: return json.loads(old['details'])
        controls.assert_approval(c,approval_reference,digest,bootstrap=trusted_bootstrap,kind=kind)
        controls.assert_open(c,{str(row.get('posting_date',''))[:7] for row in rows})
        bid=uid(); groups=defaultdict(list); errors=[]; accepted=[]
        for n,row in enumerate(rows,2):
            key=(str(row.get('posting_date','')),str(row.get('voucher_no','')),str(row.get('currency','')))
            groups[key].append((n,row))
            c.execute(raw.insert().values(id=uid(),batch_id=bid,row_number=n,payload=json.dumps(row,ensure_ascii=False)))
        seen=set()
        for key,items in groups.items():
            staged=[]; failure=None
            try:
                date.fromisoformat(key[0])
                if not key[1] or len(key[1])>100: raise ValueError('凭证号缺失或过长')
                if not re.fullmatch('[A-Z]{3}',key[2]): raise ValueError('币种须为三位大写代码')
                for n,row in items:
                    if any(f not in row for f in FIELDS): raise ValueError('缺少必需字段')
                    if row['account_code'] not in catalog: raise ValueError('未知科目：'+str(row['account_code']))
                    line=int(row['line_no'])
                    if line<1: raise ValueError('行号必须为正整数')
                    d,cr=cents(row['debit']),cents(row['credit'])
                    if (d>0)==(cr>0): raise ValueError('每行须且仅须一方有金额')
                    bk=json.dumps([source_system,key[0][:4],key[1],line],ensure_ascii=False)
                    if bk in seen or any(s['business_key']==bk for s in staged) or c.execute(select(facts.c.id).where(facts.c.business_key==bk)).first(): raise ValueError('重复业务键')
                    staged.append(dict(id=uid(),business_key=bk,batch_id=bid,period=key[0][:7],currency=key[2],category=catalog[row['account_code']],debit_cents=d,credit_cents=cr,payload=json.dumps(row,ensure_ascii=False)))
                if sum(x['debit_cents']-x['credit_cents'] for x in staged)!=0: raise ValueError('凭证借贷不平衡')
            except (ValueError,TypeError,InvalidOperation) as ex: failure=str(ex)
            if failure:
                errors.extend({'row_number':n,'voucher_no':key[1],'message':failure} for n,_ in items)
            else:
                for x in staged: c.execute(facts.insert().values(**x)); seen.add(x['business_key'])
                accepted.extend(staged)
        result=dict(batch_id=bid,status='committed' if accepted else 'failed',total_rows=len(rows),accepted_rows=len(accepted),rejected_rows=len(errors),errors=errors,source=source,data_kind=kind)
        c.execute(batches.insert().values(id=bid,sha256=digest,source=source,kind=kind,status=result['status'],details=json.dumps(result,ensure_ascii=False)))
        c.execute(audit.insert().values(id=uid(),action='import',resource=bid,created=now()))
        controls.append(c,'data_import',bid,dict(file_digest=digest,source_system=source_system,accepted_rows=len(accepted),rejected_rows=len(errors),approval_reference=approval_reference))
        return result

def metrics(e,start='2026-01',end='2026-12',currency='CNY'):
    for p in (start,end):
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',p): raise ValueError('期间格式须为YYYY-MM')
    if start>end: raise ValueError('起始期间不得晚于结束期间')
    if not re.fullmatch('[A-Z]{3}',currency): raise ValueError('币种无效')
    out={}
    with e.connect() as c:
        records=c.execute(select(facts).where(facts.c.period>=start,facts.c.period<=end,facts.c.currency==currency)).mappings().all()
        kinds={x['id']:x['kind'] for x in c.execute(select(batches)).mappings()}
    for x in records:
        v=out.setdefault(x['period'],{'revenue':0,'cost':0,'expense':0,'batch_ids':set()})
        cat=x['category']
        if cat in ('revenue','cost','expense'): v[cat]+= (x['credit_cents']-x['debit_cents']) if cat=='revenue' else (x['debit_cents']-x['credit_cents'])
        v['batch_ids'].add(x['batch_id'])
    result=[]
    for p,v in sorted(out.items()):
        rev,cost,expense=(v[k] for k in ['revenue','cost','expense'])
        result.append(dict(period=p,currency=currency,revenue=money(rev),cost=money(cost),expense=money(expense),gross_profit=money(rev-cost),operating_profit=money(rev-cost-expense),gross_margin=str(Decimal(rev-cost)/Decimal(rev)) if rev else None,batch_ids=sorted(v['batch_ids']),metric_version='1.0',data_kind=sorted({kinds[b] for b in v['batch_ids']})))
    return result

class Confirm(BaseModel):
    preview_id:str
    mapping:dict[str,str]={}
    source_system:str='local'

app=FastAPI(title='FinAgent DataHub',version='0.1.0')
@app.exception_handler(ValueError)
async def invalid(request,ex): return JSONResponse(status_code=422,content={'error':{'code':'validation_error','message':str(ex),'trace_id':uid()}})
@app.exception_handler(HTTPException)
async def http_error(request,ex): return JSONResponse(status_code=ex.status_code,content={'error':{'code':str(ex.status_code),'message':str(ex.detail),'trace_id':uid()}})
@app.middleware('http')
async def local_only(request:Request,call_next):
    if request.headers.get('origin') and request.headers['origin'] not in {str(request.base_url).rstrip('/'), *os.getenv('FINAGENT_ALLOWED_ORIGINS','http://127.0.0.1:3000,http://localhost:3000').split(',')}:
        return JSONResponse(status_code=403,content={'error':{'code':'origin_denied','message':'仅接受同源请求','trace_id':uid()}})
    if request.headers.get('host','').split(':')[0] not in os.getenv('FINAGENT_ALLOWED_HOSTS','127.0.0.1,localhost,testserver').split(','):
        return JSONResponse(status_code=403,content={'error':{'code':'host_denied','message':'仅供本机使用','trace_id':uid()}})
    return await call_next(request)
@app.get('/api/v1/health')
def health(): return {'status':'ok','mode':'users-organizations' if os.getenv('FINAGENT_AUTH_MODE')=='users' else 'single-organization-local','llm':'disabled'}
@app.get('/api/v1/ready')
def ready():
    with current_db().connect() as c: c.execute(select(batches.c.id).limit(1))
    return {'status':'ready','storage':current_db().dialect.name,'schema_version':'1'}
@app.post('/api/v1/imports/preview')
async def preview(file:UploadFile):
    data=await file.read(10485761)
    if len(data)>10485760: raise HTTPException(413,'文件超过10MB')
    name=file.filename or ''
    if name.lower().endswith('.csv'):
        try: rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        except UnicodeError: raise ValueError('CSV须使用UTF-8编码')
    elif name.lower().endswith('.xlsx'):
        from openpyxl import load_workbook
        import zipfile
        if not zipfile.is_zipfile(io.BytesIO(data)): raise ValueError('无效XLSX文件')
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist())>50_000_000: raise ValueError('解压后文件过大')
        try:
            w=load_workbook(io.BytesIO(data),read_only=True,data_only=True)
            it=iter(w.active.values); headers=[str(x) for x in next(it)]; rows=[]
            for values in it:
                rows.append({k:str(v) if v is not None else '' for k,v in zip(headers,values)})
                if len(rows)>10000: raise ValueError('最多10000行')
            w.close()
        except ValueError: raise
        except Exception: raise ValueError('无法读取XLSX，请使用标准模板')
    else: raise ValueError('仅支持CSV/XLSX')
    if not rows or len(rows)>10000: raise ValueError('文件须包含1至10000行')
    pid=uid()
    with current_db().begin() as c: c.execute(previews.insert().values(id=pid,digest=hashlib.sha256(data).hexdigest(),source=Path(name).name,payload=json.dumps(rows,ensure_ascii=False),created=now()))
    return dict(preview_id=pid,columns=list(rows[0]),sample_rows=rows[:5],suggested_mapping={k:k for k in FIELDS if k in rows[0]},required_fields=FIELDS,expires_in_seconds=3600)
@app.post('/api/v1/imports',status_code=202)
def commit(body:Confirm):
    with current_db().connect() as c: p=c.execute(select(previews).where(previews.c.id==body.preview_id)).mappings().first()
    if not p: raise HTTPException(404,'预览不存在')
    if (datetime.now(timezone.utc)-datetime.fromisoformat(p['created'])).total_seconds()>3600: raise ValueError('预览已过期，请重新上传')
    rows=json.loads(p['payload']); mapping=body.mapping or {k:k for k in FIELDS}
    if set(mapping)!=set(FIELDS) or any(v not in rows[0] for v in mapping.values()): raise ValueError('请完成全部字段映射')
    mapped=[{k:row.get(v,'') for k,v in mapping.items()} for row in rows]
    return ingest(current_db(),mapped,p['digest'],p['source'],body.source_system)
@app.get('/api/v1/imports')
def batch_list():
    with current_db().connect() as c: return [json.loads(x) for x in c.execute(select(batches.c.details)).scalars()]
@app.get('/api/v1/imports/{bid}')
def batch(bid:str):
    with current_db().connect() as c: x=c.execute(select(batches.c.details).where(batches.c.id==bid)).scalar()
    if not x: raise HTTPException(404,'批次不存在')
    return json.loads(x)
@app.get('/api/v1/metrics/finance')
def finance(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'): return metrics(current_db(),start_period,end_period,currency)
@app.post('/api/v1/analysis')
def analysis(body: dict | None = None):
    if not body or body.get('mode') != 'demo': raise HTTPException(503,'model_not_configured：请显式指定mode=demo使用规则分析')
    from integrations import execute_analysis
    return execute_analysis(body)
@app.get('/api/v1/reports',response_class=PlainTextResponse)
def report(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'):
    data=metrics(current_db(),start_period,end_period,currency)
    lines=['# 财务经营报告',f'期间：{start_period} 至 {end_period}；币种：{currency}；指标版本：1.0','本报告由确定性规则生成，不是AI推断。未包含税费及其他损益，经营利润不等于净利润。']
    for x in data: lines.append(f"\n## {x['period']}\n收入 {x['revenue']}；成本 {x['cost']}；费用 {x['expense']}；经营利润 {x['operating_profit']}\n来源批次：{', '.join(x['batch_ids'])}；数据类型：{', '.join(x['data_kind'])}")
    return '\n'.join(lines)
@app.get('/api/v1/template')
def template(): return FileResponse(ROOT/'data_platform'/'sample_vouchers.csv',filename='sample_vouchers.csv')
@app.get('/')
def index(): return FileResponse(ROOT/'frontend'/'index.html')
@app.get('/static/{filename}')
def static_asset(filename:str):
    if filename not in ('style.css','app.js','operations.js'): raise HTTPException(404,'资源不存在')
    return FileResponse(ROOT/'frontend'/filename)


# Local MVP security boundary: one configured organization only; never claim tenant isolation.
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import secrets

@app.exception_handler(RequestValidationError)
async def request_invalid(request, ex):
    return JSONResponse(status_code=422, content={'error': {'code':'validation_error','message':'请求参数校验失败','trace_id':uid()}})

@app.exception_handler(SQLAlchemyError)
async def storage_error(request, ex):
    return JSONResponse(status_code=503, content={'error': {'code':'storage_unavailable','message':'存储暂不可用','trace_id':uid()}})

@app.middleware('http')
async def authentication(request, call_next):
    path=request.url.path
    token=os.getenv('FINAGENT_API_TOKEN','')
    if path.startswith('/api/v1/') and not path.startswith('/api/v1/auth/') and path not in ('/api/v1/health','/api/v1/ready'):
        if token and os.getenv('FINAGENT_AUTH_MODE','demo')!='users':
            supplied=request.headers.get('authorization','')
            if not secrets.compare_digest(supplied, 'Bearer '+token):
                return JSONResponse(status_code=401,content={'error':{'code':'unauthorized','message':'需要有效Bearer凭据','trace_id':uid()}})
            if request.method not in ('GET','HEAD','OPTIONS') and os.getenv('FINAGENT_API_ROLE','admin') != 'admin':
                return JSONResponse(status_code=403,content={'error':{'code':'forbidden','message':'当前角色只允许读取','trace_id':uid()}})
        if 'organization_id' in request.query_params or request.headers.get('x-organization-id'):
            return JSONResponse(status_code=403,content={'error':{'code':'organization_override_denied','message':'本地单组织模式不接受客户端组织覆盖','trace_id':uid()}})
    return await call_next(request)

class ReportRequest(BaseModel):
    start_period: str='2026-01'
    end_period: str='2026-12'
    currency: str='CNY'

# Deterministic reports complete synchronously; task records persist in the database.
tasks=Table('metadata_backend_task',meta,Column('id',String,primary_key=True),Column('payload',Text))

def save_task(payload):
    tasks.create(current_db(),checkfirst=True)
    with current_db().begin() as c:
        c.execute(tasks.insert().values(id=payload['task_id'],payload=json.dumps(payload,ensure_ascii=False)))
    return payload

@app.post('/api/v1/reports',status_code=202)
def create_report(body:ReportRequest):
    content=report(body.start_period,body.end_period,body.currency)
    payload=save_task(dict(task_id=uid(),status='completed',report=content,format='markdown',metric_version='1.0',created_at=now()))
    return {'task_id':payload['task_id'],'status':payload['status']}

def get_task(task_id:str):
    tasks.create(current_db(),checkfirst=True)
    with current_db().connect() as c:
        value=c.execute(select(tasks.c.payload).where(tasks.c.id==task_id)).scalar()
    if not value: raise HTTPException(404,'任务不存在')
    return json.loads(value)

@app.get('/api/v1/analysis/{task_id}')
def analysis_task(task_id:str):
    value=get_task(task_id)
    if value.get('type') != 'analysis': raise HTTPException(404,'分析任务不存在')
    return value

from integrations import install
install(app)

from identity import install_identity
install_identity(app)

@app.get('/api/v1/reports/{task_id}')
def report_task(task_id:str):
    value=get_task(task_id)
    if value.get('type','report')!='report':raise HTTPException(404,'报告任务不存在')
    return value

import jobs
jobs.install(app)

import warehouse
warehouse.install(app)

import model_routes,knowledge_vectors
model_routes.install(app)
knowledge_vectors.install(app)

import treasury
treasury.install(app)

import report_exports
report_exports.install(app)

import connectors,financial_statements
connectors.install(app)
financial_statements.install(app)

financial_statements.install_bank_worksheet(app)

import leased_jobs
leased_jobs.install(app)

import semantic_routes
semantic_routes.install(app)

import erp_imports
erp_imports.install(app)

import erp_database
erp_database.install(app)

import erp_accounts
erp_accounts.install(app)

import enterprise_controls
enterprise_controls.install(app)

import finance_workbench, agent_runs
finance_workbench.install(app)
agent_runs.install(app)

import cfo_briefings
cfo_briefings.install(app)

import cfo_models
cfo_models.install(app)

import finance_query
finance_query.install(app)

import theme_routes
theme_routes.install(app)

import knowledge_uploads
knowledge_uploads.install(app)

import public_company
public_company.install(app)

import department_metrics
department_metrics.install(app)

import procurement
procurement.install(app)

import supplier_registry
supplier_registry.install(app)
