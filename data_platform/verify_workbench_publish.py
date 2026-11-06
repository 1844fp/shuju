"""Backend route -> isolated SQLite -> PostgreSQL contract exercise."""
import json,os,hashlib,types,uuid
from pathlib import Path
from sqlalchemy import create_engine
import app as core,finance_workbench as wb,warehouse
import psycopg
from fastapi import FastAPI
from reconcile_workbench import report
root=Path(__file__).resolve().parents[1]
engine=create_engine('sqlite:///'+str(root/'work/redesign'/('source-'+uuid.uuid4().hex+'.sqlite')))
original=core.current_db;core.current_db=lambda:engine
token=core.request_organization.set('demo')
try:
 app=FastAPI();wb.install(app)
 endpoints={r.path:r.endpoint for r in app.routes if hasattr(r,'endpoint')}
 request=types.SimpleNamespace(state=types.SimpleNamespace(identity={'id':'simulated-maker','role':'org_admin'}))
 create=endpoints['/api/v1/finance-workbench/documents']
 result=create(wb.Document(external_id='simulated-pg-test',kind='invoice',date='2026-01-01',amount='12.30',data_kind='simulated'),request)
 with psycopg.connect(os.environ['DATABASE_URL']) as c:batch=str(c.execute("select id from metadata.data_batch where organization_id='demo' limit 1").fetchone()[0])
 old=warehouse.connection;warehouse.connection=lambda:psycopg.connect(os.environ['DATABASE_URL'])
 try:
  publish=endpoints['/api/v1/finance-workbench/documents/{jid}/publish']
  publish(result['id'],{'batch_id':batch},request);publish(result['id'],{'batch_id':batch},request)
 finally:warehouse.connection=old
 with psycopg.connect(os.environ['DATABASE_URL']) as c:
  stored=c.execute('SELECT original_content,source_sha256 FROM ods.workbench_evidence WHERE document_id=%s',(result['id'],)).fetchall()
  assert len(stored)==1 and bytes(stored[0][0])==result['payload'].encode()
  assert stored[0][1]==hashlib.sha256(result['payload'].encode()).hexdigest()
  output=report(c,'demo');assert output['data_kind']['simulated']==1
  assert report(c,'unrelated')['document_count']==0
  (root/'work/redesign/theme-quality.json').write_text(json.dumps(output,indent=2),encoding='utf8')
 print('PASS: backend create/publish route handlers, exact SQLite/PG bytes/hash, replay, simulated label, scoped quality report')
finally:
 core.request_organization.reset(token);core.current_db=original;engine.dispose()
