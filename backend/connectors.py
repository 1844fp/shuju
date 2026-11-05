"""Bounded, read-only SQLite journal connector inside the project import zone."""
import sqlite3,json,hashlib,re
from contextlib import closing
from pathlib import Path
from datetime import datetime,timezone
from fastapi import HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import MetaData,Table,Column,String,Text,select
import app as core
meta=MetaData();sources=Table('metadata_connector',meta,Column('id',String,primary_key=True),Column('payload',Text))
class Source(BaseModel):
 name:str=Field(min_length=1,max_length=100)
 kind:str='sqlite_journal'
 relative_path:str
 table_name:str

def zone():
 p=core.ROOT/'data_sources'/core.request_organization.get();p.mkdir(parents=True,exist_ok=True);return p.resolve()
def source_file(relative):
 if Path(relative).is_absolute():raise ValueError('仅接受当前组织data_sources目录内的相对路径')
 p=(zone()/relative).resolve()
 if not p.is_relative_to(zone()) or not p.is_file():raise ValueError('数据文件不存在或超出当前组织导入区')
 if p.stat().st_size>50_000_000:raise ValueError('SQLite源文件超过50MB')
 return p

def run_connector(sid):
 meta.create_all(core.current_db())
 with core.current_db().connect() as c:value=c.execute(select(sources.c.payload).where(sources.c.id==sid)).scalar()
 if not value:raise HTTPException(404,'连接器不存在')
 source=json.loads(value);p=source_file(source['relative_path']);table=source['table_name']
 try:
  with closing(sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=3)) as db:
   db.execute('PRAGMA query_only=ON');db.set_progress_handler(lambda:1 if (datetime.now(timezone.utc)-started).total_seconds()>5 else 0,1000)
   started=datetime.now(timezone.utc)
   exists=db.execute("SELECT type FROM sqlite_master WHERE name=?",(table,)).fetchone()
   if not exists or exists[0]!='table':raise ValueError('只允许读取命名的实体表')
   cols=[x[1] for x in db.execute('PRAGMA table_info("'+table+'")')]
   if any(k not in cols for k in core.FIELDS):raise ValueError('源表缺少凭证标准字段')
   data=db.execute('SELECT '+','.join('"'+k+'"' for k in core.FIELDS)+' FROM "'+table+'" LIMIT 10001').fetchall()
 except sqlite3.Error:raise ValueError('源数据库读取失败或超过查询时限') from None
 if not 1<=len(data)<=10000:raise ValueError('源表须包含1至10000行')
 rows=[{k:str(v) if v is not None else '' for k,v in zip(core.FIELDS,row)} for row in data]
 digest=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 return core.ingest(core.current_db(),rows,digest,source['name'],'connector-'+sid[:12],kind='uploaded')
def install(app):
 @app.post('/api/v1/connectors',status_code=201)
 def create(body:Source):
  if body.kind!='sqlite_journal' or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,62}',body.table_name):raise ValueError('仅支持SQLite标准凭证实体表及安全表名')
  source_file(body.relative_path);meta.create_all(core.current_db());value=body.model_dump();value.update(id=core.uid(),created_at=core.now())
  with core.current_db().begin() as c:c.execute(sources.insert().values(id=value['id'],payload=json.dumps(value,ensure_ascii=False)))
  return value
 @app.get('/api/v1/connectors')
 def listing():
  meta.create_all(core.current_db())
  with core.current_db().connect() as c:return [json.loads(x) for x in c.execute(select(sources.c.payload)).scalars()]
 @app.post('/api/v1/connectors/{sid}/run')
 def execute(sid:str):return run_connector(sid)
