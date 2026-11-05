"""Single-process durable queue. Call recover(engine) for each organization at startup."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import Table, Column, String, Integer, Text, MetaData, select
from fastapi import HTTPException
from pydantic import BaseModel, Field
import app as core

metadata=MetaData()
jobs=Table('metadata_async_job',metadata,Column('id',String,primary_key=True),Column('status',String),Column('attempts',Integer),Column('payload',Text))
_lock=threading.RLock()
_pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='finance-job')

def read(db, job_id):
    jobs.create(db,checkfirst=True)
    with db.connect() as c: row=c.execute(select(jobs.c.payload).where(jobs.c.id==job_id)).scalar()
    if row is None: raise HTTPException(404,'任务不存在')
    return json.loads(row)

def write(db,p):
    p['updated_at']=core.now()
    with db.begin() as c:c.execute(jobs.update().where(jobs.c.id==p['task_id']).values(status=p['status'],attempts=p['attempts'],payload=json.dumps(p,ensure_ascii=False)))

def execute(p):
    if p['kind']=='analysis':
        from integrations import execute_analysis
        return execute_analysis(p['input'])
    return {'report':core.report(**{k:v for k,v in p['input'].items() if k in ('start_period','end_period','currency')}),'format':'markdown'}

def worker(db,job_id):
    token=core.request_database.set(db)
    try:
        while True:
            with _lock:
                p=read(db,job_id)
                if p['status']!='queued':return
                p['status']='running';p['attempts']+=1;write(db,p)
            try: result=execute(p); error=None
            except Exception as ex:
                result=None;error={'code':'dependency_unavailable' if isinstance(ex,HTTPException) and ex.status_code==503 else 'execution_failed','message':'任务执行失败，请检查依赖及输入'}
            with _lock:
                current=read(db,job_id)
                if current['status']=='cancelled':return
                p['result']=result;p['error']=error
                p['status']='completed' if error is None else ('queued' if p['attempts']<=p['max_retries'] else 'failed')
                write(db,p)
                if p['status']!='queued':return
    finally:core.request_database.reset(token)

def submit(kind,body,max_retries=0,dispatch=True):
    if kind not in ('analysis','report'):raise HTTPException(422,'无效任务类型')
    if not 0<=max_retries<=3:raise HTTPException(422,'重试次数须为0至3')
    if kind=='analysis' and body.get('mode')!='demo':raise HTTPException(503,'model_not_configured')
    if 'organization_id' in body:raise HTTPException(403,'禁止覆盖组织')
    db=core.current_db()
    p=dict(task_id=core.uid(),kind=kind,input=body,status='queued',attempts=0,max_retries=max_retries,result=None,error=None,created_at=core.now())
    with _lock:
        jobs.create(db,checkfirst=True)
        with db.begin() as c:c.execute(jobs.insert().values(id=p['task_id'],status='queued',attempts=0,payload=json.dumps(p)))
    if dispatch:_pool.submit(worker,db,p['task_id'])
    return p

def cancel(db,job_id):
    with _lock:
        p=read(db,job_id)
        if p['status'] in ('queued','running'):p['status']='cancelled';write(db,p)
        return p

def recover(db,dispatch=True):
    """Startup only, before accepting work; never run concurrently with live workers."""
    with _lock:
        jobs.create(db,checkfirst=True)
        with db.connect() as c: ids=list(c.execute(select(jobs.c.id).where(jobs.c.status.in_(['queued','running']))).scalars())
        pending=[]
        for jid in ids:
            p=read(db,jid)
            if p['status']=='running':
                p['status']='queued' if p['attempts']<=p['max_retries'] else 'failed'
                p['error']={'code':'worker_interrupted','message':'进程重启中断执行'};write(db,p)
            if p['status']=='queued':pending.append(jid)
    if dispatch:
        for jid in pending:_pool.submit(worker,db,jid)
    return pending

class JobInput(BaseModel):
    kind:str
    input:dict=Field(default_factory=dict)
    max_retries:int=Field(default=0,ge=0,le=3)

def install(app):
    @app.post('/api/v1/jobs',status_code=202)
    def create(body:JobInput):return submit(body.kind,body.input,body.max_retries)
    @app.get('/api/v1/jobs/{job_id}')
    def get(job_id:str):return read(core.current_db(),job_id)
    @app.post('/api/v1/jobs/{job_id}/cancel')
    def stop(job_id:str):return cancel(core.current_db(),job_id)

    @app.get('/api/v1/jobs')
    def listing():
        db=core.current_db();jobs.create(db,checkfirst=True)
        with db.connect() as c:
            records=c.execute(select(jobs.c.payload).limit(200)).scalars()
            return sorted([json.loads(x) for x in records],key=lambda p:p['created_at'],reverse=True)
