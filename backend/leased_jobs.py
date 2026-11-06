"""Database compare-and-swap leases. At least once, never exactly once."""
import json, threading, time, uuid
from sqlalchemy import MetaData, Table, Column, String, Integer, Float, Text, select, or_, and_, update
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict
import app as core
meta=MetaData()
t=Table('metadata_leased_job',meta,Column('id',String,primary_key=True),Column('organization',String),Column('kind',String),Column('status',String),Column('attempts',Integer),Column('max_attempts',Integer),Column('owner',String),Column('expires',Float),Column('input',Text),Column('result',Text),Column('error',String))
def initialize(db):meta.create_all(db)
def submit(kind,body,max_attempts=3):
    if kind not in ('report','analysis') or not 1<=max_attempts<=5:raise HTTPException(422,'任务参数无效')
    allowed={'start_period','end_period','currency','question','mode'}
    if set(body)-allowed:raise HTTPException(422,'不支持的输入字段或组织覆盖')
    if kind=='analysis' and body.get('mode')!='demo':raise HTTPException(503,'model_not_configured')
    db=core.current_db();initialize(db);jid=str(uuid.uuid4())
    with db.begin() as c:c.execute(t.insert().values(id=jid,organization=core.request_organization.get(),kind=kind,status='queued',attempts=0,max_attempts=max_attempts,owner=None,expires=0,input=json.dumps(body)))
    return get(db,core.request_organization.get(),jid)
def get(db,org,jid):
    initialize(db)
    with db.connect() as c:r=c.execute(select(t).where(t.c.id==jid,t.c.organization==org)).mappings().first()
    if not r:raise HTTPException(404,'任务不存在')
    r=dict(r)
    for k in ('input','result'):r[k]=json.loads(r[k]) if r[k] else None
    return r
def claim(db,org,lease=30):
    if lease<=0:raise ValueError('lease must be positive')
    now=time.time();eligible=and_(t.c.organization==org,or_(t.c.status=='queued',and_(t.c.status=='running',t.c.expires<now)))
    with db.begin() as c:
        c.execute(update(t).where(eligible,t.c.attempts>=t.c.max_attempts).values(status='failed',error='attempt_limit',owner=None))
        ids=list(c.execute(select(t.c.id).where(eligible,t.c.attempts<t.c.max_attempts).limit(20)).scalars())
        for jid in ids:
            owner=str(uuid.uuid4())
            n=c.execute(update(t).where(t.c.id==jid,eligible,t.c.attempts<t.c.max_attempts).values(status='running',owner=owner,expires=now+lease,attempts=t.c.attempts+1)).rowcount
            if n:return jid,owner
    return None
def owned(org,jid,owner):return and_(t.c.id==jid,t.c.organization==org,t.c.owner==owner,t.c.status=='running',t.c.expires>time.time())
def heartbeat(db,org,jid,owner,lease=30):
    with db.begin() as c:return c.execute(update(t).where(owned(org,jid,owner)).values(expires=time.time()+lease)).rowcount==1
def finish(db,org,jid,owner,result=None,error=None):
    with db.begin() as c:
        return c.execute(update(t).where(owned(org,jid,owner)).values(status=('queued' if error else 'completed'),result=json.dumps(result) if result is not None else None,error='execution_failed' if error else None,owner=None,expires=0)).rowcount==1

def cancel(db,org,jid):
    initialize(db)
    with db.begin() as c:c.execute(update(t).where(t.c.id==jid,t.c.organization==org,t.c.status.in_(['queued','running'])).values(status='cancelled',owner=None,expires=0))
    return get(db,org,jid)
def run_once(db,org,lease=30):
    item=claim(db,org,lease)
    if not item:return False
    jid,owner=item;stop=threading.Event()
    def beat():
        while not stop.wait(lease/3):
            if not heartbeat(db,org,jid,owner,lease):return
    thread=threading.Thread(target=beat,daemon=True);thread.start()
    a=core.request_database.set(db);b=core.request_organization.set(org)
    try:
        p=get(db,org,jid)
        if p['kind']=='report':result={'report':core.report(**{k:v for k,v in p['input'].items() if k in ('start_period','end_period','currency')})}
        else:
            from integrations import execute_analysis
            result=execute_analysis(p['input'])
        finish(db,org,jid,owner,result)
    except Exception:finish(db,org,jid,owner,error=True)
    finally:stop.set();thread.join();core.request_organization.reset(b);core.request_database.reset(a)
    return True
class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:str
    input:dict=Field(default_factory=dict)
    max_attempts:int=Field(default=3,ge=1,le=5)
def install(app):
    @app.post('/api/v1/durable-jobs',status_code=202)
    def create(body:Input):return submit(body.kind,body.input,body.max_attempts)
    @app.get('/api/v1/durable-jobs/{jid}')
    def read(jid:str):return get(core.current_db(),core.request_organization.get(),jid)
    @app.post('/api/v1/durable-jobs/{jid}/cancel')
    def stop(jid:str):return cancel(core.current_db(),core.request_organization.get(),jid)
