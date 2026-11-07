"""Tenant file preservation and locally extracted knowledge chunks."""
import base64,hashlib,json
from datetime import date
from fastapi import UploadFile,Form,HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from sqlalchemy import MetaData,Table,Column,String,Text,select
import app as core
from knowledge_vectors import docs,meta as knowledge_meta,vector
meta=MetaData();sources=Table('knowledge_original_file',meta,Column('id',String,primary_key=True),Column('organization',String),Column('payload',Text))
def install(app):
 @app.post('/api/v1/knowledge/upload',status_code=201)
 async def upload(file:UploadFile,title:str=Form(...),version:str=Form(...),effective_date:date=Form(...),ocr_scanned_pdf:bool=Form(False),ocr_pdf_pages:str=Form('',max_length=32)):
  if not 1<=len(title)<=120 or not 1<=len(version)<=40:raise HTTPException(422,'标题或版本无效')
  raw=await file.read(5*1024*1024+1)
  if len(raw)>5*1024*1024:raise HTTPException(413,'文件超过5MiB')
  from agents.document_parser import parse_document,selected_pdf_pages
  from agents.image_ocr import OCRUnavailable
  from pypdf.errors import PdfReadError
  try:pages=selected_pdf_pages(ocr_pdf_pages)
  except ValueError:raise HTTPException(422,'请输入最多四个用英文逗号分隔的页码') from None
  try:chunks=await run_in_threadpool(parse_document,raw,file.filename or '',title=title,version=version,effective_date=effective_date.isoformat(),ocr_scanned_pdf=ocr_scanned_pdf,ocr_pdf_pages=pages)
  except OCRUnavailable:raise HTTPException(503,'本机图像识别暂不可用') from None
  except (ValueError,UnicodeError,PdfReadError):raise HTTPException(422,'文档无法解析、无可识别文字或超出限制') from None
  db=core.current_db();org=core.request_organization.get();meta.create_all(db);knowledge_meta.create_all(db)
  mode='|pdf-ocr' if ocr_scanned_pdf else ''
  if pages:mode+='|ocr-pages:'+','.join(map(str,pages))
  digest=hashlib.sha256(raw).hexdigest();sid=hashlib.sha256((org+'|'+digest+'|'+title+'|'+version+'|'+effective_date.isoformat()+mode).encode()).hexdigest()
  result={'source_id':sid,'chunks':len(chunks),'source_sha256':digest}
  ocr_chunk=next((chunk for chunk in chunks if chunk.get('requires_review')),None)
  if ocr_chunk:
   result.update({key:ocr_chunk[key] for key in ('extraction_method','ocr_language','requires_review')})
  import enterprise_controls as controls
  controls.initialize(db)
  with controls.LOCK,db.begin() as c:
   old=c.execute(select(sources.c.id).where(sources.c.id==sid,sources.c.organization==org)).scalar()
   if old:return {**result,'status':'already_imported'}
   if len(c.execute(select(docs.c.id).limit(101)).all())+len(chunks)>100:raise HTTPException(422,'本组织知识片段上限100')
   c.execute(sources.insert().values(id=sid,organization=org,payload=json.dumps({'filename':file.filename,'source_sha256':digest,'original_base64':base64.b64encode(raw).decode()})))
   for chunk in chunks:
    chunk['id']=hashlib.sha256((sid+'|'+chunk['id']).encode()).hexdigest();chunk['source_id']=sid;chunk['vector']=vector(chunk['text']);c.execute(docs.insert().values(id=chunk['id'],payload=json.dumps(chunk,ensure_ascii=False)))
   controls.append(c,'knowledge_file_imported',sid,{'source_sha256':digest,'chunks':len(chunks)})
  return {**result,'status':'imported'}
 @app.get('/api/v1/knowledge/sources/{sid}')
 def source(sid:str):
  db=core.current_db();meta.create_all(db)
  with db.connect() as c:value=c.execute(select(sources.c.payload).where(sources.c.id==sid,sources.c.organization==core.request_organization.get())).scalar()
  if not value:raise HTTPException(404,'原文件不存在')
  p=json.loads(value);return Response(base64.b64decode(p['original_base64']),media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="original-document"'})
