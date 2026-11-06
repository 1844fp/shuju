import json,hashlib
from datetime import date
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import MetaData,Table,Column,String,Text,select
import app as core
import enterprise_controls as controls
meta=MetaData();suppliers=Table('metadata_supplier_registration',meta,Column('id',String,primary_key=True),Column('organization',String),Column('payload',Text))
class Supplier(BaseModel):
 model_config=ConfigDict(extra='forbid')
 supplier:str=Field(min_length=1,max_length=100)
 registered_date:date
 source_reference:str=Field(min_length=1,max_length=300)
 data_kind:str

def registrations():
 meta.create_all(core.current_db())
 with core.current_db().connect() as c:return {json.loads(r['payload'])['supplier']:json.loads(r['payload']) for r in c.execute(select(suppliers).where(suppliers.c.organization==core.request_organization.get())).mappings()}
def install(app):
 @app.post('/api/v1/finance-workbench/suppliers',status_code=201)
 def register(body:Supplier):
  who=core.request_actor.get()
  if not who or who['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要管理员')
  if body.data_kind not in ('simulated','uploaded'):raise HTTPException(422,'来源类型无效')
  meta.create_all(core.current_db());controls.initialize(core.current_db());p=body.model_dump(mode='json');raw=controls.canonical(p);org=core.request_organization.get();key=hashlib.sha256((org+'|'+body.supplier).encode()).hexdigest()
  with controls.LOCK,core.current_db().begin() as c:
   old=c.execute(select(suppliers.c.payload).where(suppliers.c.id==key)).scalar()
   if old:
    if old!=raw:raise HTTPException(409,'供应商注册证据不可覆盖')
    return p
   c.execute(suppliers.insert().values(id=key,organization=org,payload=raw));controls.append(c,'supplier_registered',body.supplier,{'source_reference':body.source_reference})
  return p
 @app.get('/api/v1/finance-workbench/suppliers')
 def listing():return list(registrations().values())
