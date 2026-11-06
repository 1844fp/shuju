import json,base64,hashlib
from pathlib import Path
from pydantic import BaseModel,ConfigDict
class Confirmation(BaseModel):
 model_config=ConfigDict(extra="forbid")
 acknowledge_quarantine:bool=False
 expected_snapshot_hash:str|None=None
def fingerprint(p):
 return hashlib.sha256(json.dumps({k:v for k,v in p.items() if k!="snapshot_hash"},sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
from fastapi import HTTPException,UploadFile,Form
from fastapi.responses import Response,FileResponse
from sqlalchemy import MetaData,Table,Column,String,Text,select
from sqlalchemy.exc import IntegrityError
import app as core
import enterprise_controls as controls
from data_platform.theme_imports import parse_csv,SCHEMAS
meta=MetaData();imports=Table('metadata_theme_import',meta,Column('id',String,primary_key=True),Column('organization',String),Column('file_key',String,unique=True),Column('status',String),Column('payload',Text));records=Table('metadata_theme_record',meta,Column('business_key',String,primary_key=True),Column('organization',String),Column('row_hash',String),Column('payload',Text))
manifests=Table('metadata_theme_source_manifest',meta,Column('id',String,primary_key=True),Column('organization',String),Column('payload',Text),Column('sha256',String))
def scope():
 db=core.current_db();meta.create_all(db);controls.initialize(db);return db,core.request_organization.get()
def get(jid):
 db,org=scope()
 with db.connect() as c:r=c.execute(select(imports).where(imports.c.id==jid,imports.c.organization==org)).mappings().first()
 if not r:raise HTTPException(404,'主题导入不存在')
 return dict(r)
def install(app):
 @app.get('/api/v1/theme-templates/{theme}')
 def template(theme:str):
  if theme not in SCHEMAS:raise HTTPException(404,'主题不存在')
  return FileResponse(core.ROOT/'data_platform'/'theme_templates'/(theme+'.csv'),media_type='text/csv',filename=theme+'.csv')
 @app.post('/api/v1/theme-imports/{theme}/preview',status_code=201)
 async def preview(theme:str,file:UploadFile,data_kind:str=Form('uploaded')):
  if theme not in SCHEMAS:raise HTTPException(404,'主题不存在')
  suffix=Path(file.filename or '').suffix.lower()
  if suffix not in ('.csv','.xlsx'):raise HTTPException(422,'仅支持CSV/XLSX')
  raw=await file.read(10485761)
  if len(raw)>10485760:raise HTTPException(413,'文件超过10MB')
  db,org=scope()
  try:
   if suffix=='.xlsx':
    from data_platform.theme_imports import parse_xlsx
    p=parse_xlsx(raw,theme,org,data_kind)
   else:p=parse_csv(raw,theme,org,data_kind)
   p['source']['format']=suffix[1:]
  except (ValueError,UnicodeError):raise HTTPException(422,'CSV字段、编码或数据类型无效') from None
  p['snapshot_hash']=fingerprint(p)
  if not 1<=len(p['accepted'])+len(p['quarantined'])<=10000:raise HTTPException(422,'须1至10000行')
  try:
   with controls.LOCK,db.begin() as c:
    old=c.execute(select(imports).where(imports.c.file_key==p['file_key'],imports.c.organization==org)).mappings().first()
    if old:
     if json.loads(old['payload'])['data_kind']!=data_kind:raise HTTPException(409,'相同文件来源类型冲突')
     return {'preview_id':old['id'],'status':old['status'],'snapshot':json.loads(old['payload'])}
    jid=core.uid();c.execute(imports.insert().values(id=jid,organization=org,file_key=p['file_key'],status='preview',payload=json.dumps(p)));controls.append(c,'theme_preview',jid,{'theme':theme,'source_sha256':p['source']['sha256']})
  except IntegrityError:raise HTTPException(409,'并发文件重放，请重试') from None
  return {'preview_id':jid,'status':'preview','snapshot':p}
 @app.get('/api/v1/theme-imports/{jid}')
 def detail(jid:str):
  r=get(jid);return {**r,'payload':json.loads(r['payload'])}
 @app.get('/api/v1/theme-imports/{jid}/source')
 def source(jid:str):
  p=json.loads(get(jid)['payload']);fmt=p['source'].get('format','csv');return Response(base64.b64decode(p['source']['original_base64']),media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="source.{fmt}"'})
 @app.post('/api/v1/theme-imports/{jid}/confirm')
 def confirm(jid:str,body:Confirmation=Confirmation()):
  r=get(jid);p=json.loads(r['payload']);db,org=scope()
  from data_platform.source_manifest import reconcile
  with db.connect() as c:stored=c.execute(select(manifests.c.payload).where(manifests.c.id==jid,manifests.c.organization==org)).scalar()
  if stored and reconcile(p,json.loads(stored))['status']!='matched':raise HTTPException(409,'源清单差异阻止确认')
  if r['status']=='revoked':raise HTTPException(409,'已撤销批次不可重新确认')
  if not p['accepted']:raise HTTPException(422,'无可接收记录')
  if p['quarantined'] and not body.acknowledge_quarantine:raise HTTPException(409,'须显式确认隔离记录')
  raw=base64.b64decode(p['source']['original_base64'])
  if hashlib.sha256(raw).hexdigest()!=p['source']['sha256'] or p.get('schema_version')!='theme-v1' or p.get('snapshot_hash')!=fingerprint(p):raise HTTPException(409,'原文或规范快照变化，请重新预览')
  if body.expected_snapshot_hash and body.expected_snapshot_hash!=p['snapshot_hash']:raise HTTPException(409,'预览版本变化')
  if r['status']=='confirmed':return {'id':jid,'status':'confirmed'}
  try:
   with controls.LOCK,db.begin() as c:
    controls.assert_open(c,{x['normalized']['date'][:7] for x in p['accepted']})
    for x in p['accepted']:
     old=c.execute(select(records).where(records.c.business_key==x['business_key'],records.c.organization==org)).mappings().first()
     if old:
      if old['row_hash']!=x['row_hash']:raise HTTPException(409,'跨文件业务键内容冲突')
     else:c.execute(records.insert().values(business_key=x['business_key'],organization=org,row_hash=x['row_hash'],payload=json.dumps(x)))
    if c.execute(imports.update().where(imports.c.id==jid,imports.c.status=='preview',imports.c.organization==org).values(status='confirmed')).rowcount!=1:raise HTTPException(409,'确认状态变化')
    controls.append(c,'theme_confirmed',jid,{'source_sha256':p['source']['sha256'],'accepted':len(p['accepted']),'quarantined':len(p['quarantined'])})
  except IntegrityError:raise HTTPException(409,'并发业务键冲突，请重试') from None
  return {'id':jid,'status':'confirmed','accepted':len(p['accepted']),'quarantined':len(p['quarantined'])}

 @app.post('/api/v1/theme-imports/{jid}/revoke')
 def revoke(jid:str,body:dict):
  who=core.request_actor.get()
  if not who or who['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要认证管理员')
  if set(body)!={'reason'} or not isinstance(body['reason'],str) or not 3<=len(body['reason'].strip())<=300:raise HTTPException(422,'须提供撤销原因')
  r=get(jid);p=json.loads(r['payload']);db,org=scope()
  if r['status']=='revoked':return {'id':jid,'status':'revoked'}
  with controls.LOCK,db.begin() as c:
   controls.assert_open(c,{x['normalized']['date'][:7] for x in p['accepted']})
   if c.execute(imports.update().where(imports.c.id==jid,imports.c.organization==org,imports.c.status=='confirmed').values(status='revoked')).rowcount!=1:raise HTTPException(409,'仅已确认批次可撤销')
   controls.append(c,'theme_revoked',jid,{'reason':body['reason'],'source_sha256':p['source']['sha256'],'scope':'logical only; originals and ledger unchanged'})
  return {'id':jid,'status':'revoked'}

 @app.put('/api/v1/theme-imports/{jid}/source-manifest')
 def manifest_put(jid:str,body:dict):
  who=core.request_actor.get()
  if not who or who['role'] not in ('org_admin','platform_admin'):raise HTTPException(403,'需要管理员')
  from data_platform.source_manifest import reconcile
  r=get(jid);db,org=scope()
  try:report=reconcile(json.loads(r['payload']),body)
  except ValueError:raise HTTPException(422,'清单格式无效') from None
  raw=json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':'));digest=hashlib.sha256(raw.encode()).hexdigest()
  with controls.LOCK,db.begin() as c:
   old=c.execute(select(manifests.c.sha256).where(manifests.c.id==jid,manifests.c.organization==org)).scalar()
   if old and old!=digest:raise HTTPException(409,'原始清单不可覆盖')
   if not old:
    if r['status']!='preview':raise HTTPException(409,'确认后不可补换清单')
    c.execute(manifests.insert().values(id=jid,organization=org,payload=raw,sha256=digest));controls.append(c,'theme_manifest_saved',jid,{'sha256':digest,'status':report['status']})
  return {'sha256':digest,'report':report}
 @app.get('/api/v1/theme-imports/{jid}/source-manifest')
 def manifest_get(jid:str):
  from data_platform.source_manifest import reconcile
  r=get(jid);db,org=scope()
  with db.connect() as c:value=c.execute(select(manifests).where(manifests.c.id==jid,manifests.c.organization==org)).mappings().first()
  return {'manifest':json.loads(value['payload']) if value else None,'sha256':value['sha256'] if value else None,'report':reconcile(json.loads(r['payload']),json.loads(value['payload']) if value else None)}
