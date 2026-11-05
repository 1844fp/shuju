"""Local normalized hashed character-ngram vectors. Not semantic embeddings."""
import math,hashlib,json
from datetime import date
from fastapi import HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import Table,Column,String,Text,MetaData,select
import app as core
meta=MetaData();docs=Table('knowledge_vector_document',meta,Column('id',String,primary_key=True),Column('payload',Text))
def vector(text):
    text=''.join(text.lower().split());v=[0]*256
    for n in (1,2,3):
        for i in range(max(0,len(text)-n+1)):
            h=int.from_bytes(hashlib.sha256(text[i:i+n].encode()).digest()[:4],'big');v[h%256]+=1 if h&256 else -1
    length=math.sqrt(sum(x*x for x in v));return [x/length if length else 0 for x in v]
class Document(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    version:str=Field(min_length=1,max_length=40)
    effective_date:date
    locator:str=Field(min_length=1,max_length=120)
    text:str=Field(min_length=1,max_length=20000)
def install(app):
    @app.post('/api/v1/knowledge/documents',status_code=201)
    def add(body:Document):
        meta.create_all(core.current_db());value=body.model_dump(mode='json');key=hashlib.sha256((body.title+'\0'+body.version).encode()).hexdigest();value.update(id=key,content_sha256=hashlib.sha256(body.text.encode()).hexdigest(),vector=vector(body.text))
        with core.current_db().begin() as c:
            old=c.execute(select(docs.c.payload).where(docs.c.id==key)).scalar()
            if old:
                if json.loads(old)!=value:raise HTTPException(409,'同名同版本已有不同内容，请提升版本')
                return {k:v for k,v in value.items() if k!='vector'}
            if len(c.execute(select(docs.c.id).limit(100)).all())>=100:raise HTTPException(422,'本地知识库最多100个版本文档')
            c.execute(docs.insert().values(id=key,payload=json.dumps(value,ensure_ascii=False)))
        return {k:v for k,v in value.items() if k!='vector'}
    @app.get('/api/v1/knowledge/vector-search')
    def search(q:str,as_of:date|None=None,version:str|None=None,limit:int=5):
        if not 1<=len(q)<=2000 or not 1<=limit<=20:raise ValueError('查询长度或条数无效')
        meta.create_all(core.current_db());query=vector(q);cutoff=(as_of or date.today()).isoformat()
        with core.current_db().connect() as c:items=[json.loads(x) for x in c.execute(select(docs.c.payload)).scalars()]
        result=[]
        for d in items:
            if d['effective_date']>cutoff or (version and d['version']!=version):continue
            score=sum(a*b for a,b in zip(query,d['vector']))
            if score>0:result.append({**{k:v for k,v in d.items() if k!='vector'},'score':score})
        return {'method':'local_hashed_character_ngram_cosine','semantic_embeddings':False,'matches':sorted(result,key=lambda x:(-x['score'],x['id']))[:limit]}
def retrieve_documents(question,limit=3):
    meta.create_all(core.current_db());q=vector(question);cutoff=date.today().isoformat()
    with core.current_db().connect() as c:items=[json.loads(x) for x in c.execute(select(docs.c.payload)).scalars()]
    scored=[]
    for d in items:
        if d['effective_date']>cutoff:continue
        score=sum(a*b for a,b in zip(q,d['vector']))
        if score>=.15:scored.append({**{k:v for k,v in d.items() if k!='vector'},'score':score,'retrieval_method':'local_hashed_character_ngram_cosine'})
    return sorted(scored,key=lambda x:(-x['score'],x['id']))[:limit]
