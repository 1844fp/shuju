"""Tenant scope is exclusively the current_db context."""
import json
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from agents.semantic import Semantic
engine=Semantic()
def install(app):
 @app.get('/api/v1/knowledge/semantic-status')
 def status(): return engine.info()
 @app.post('/api/v1/knowledge/semantic-initialize')
 def initialize(): return engine.initialize()
 @app.get('/api/v1/knowledge/semantic-search')
 def search(q:str,as_of:date|None=None,version:str|None=None,limit:int=5):
  if engine.status!='ready':raise HTTPException(503,engine.info())
  db=core.current_db();meta.create_all(db)
  with db.connect() as c: items=[json.loads(x) for x in c.execute(select(docs.c.payload)).scalars()]
  try:
   matches=engine.search(q,items,as_of.isoformat() if as_of else None,version,limit)
   return {**engine.info(),'matches':matches,'evidence_status':'matches_found' if matches else 'no_matching_evidence'}
  except ValueError as exc:raise HTTPException(422,str(exc))

# Resolve the host after install() is defined so direct module tests cannot cycle.
import app as core
from knowledge_vectors import docs,meta
