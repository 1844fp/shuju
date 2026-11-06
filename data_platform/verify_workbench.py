import os,uuid
import psycopg
with psycopg.connect(os.environ['DATABASE_URL']) as c:
 batch=c.execute("select id from metadata.data_batch where organization_id='demo' limit 1").fetchone()[0]
 args=('demo',batch,'test-invoice','invoice','a'*64,b'original', '{"amount":"12.30"}','quarantined','["duplicate_invoice"]','v1')
 stmt='INSERT INTO ods.workbench_evidence(organization_id,batch_id,document_id,document_kind,source_sha256,original_content,original_payload,validation_status,quality_errors,schema_version) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,%s) ON CONFLICT DO NOTHING'
 c.execute(stmt,args);c.execute(stmt,args)
 assert c.execute("select count(*) from ods.workbench_evidence where document_id='test-invoice'").fetchone()[0]==1
 assert c.execute("select original_content from ods.workbench_evidence where document_id='test-invoice'").fetchone()[0]==b'original'
 for query,params,error in [("UPDATE ods.workbench_evidence SET original_content='changed'",(),psycopg.errors.CheckViolation),(stmt,('other',*args[1:]),psycopg.errors.ForeignKeyViolation),("INSERT INTO metadata.workbench_risk_evidence VALUES('other',%s,'test-invoice',%s,'risk','v1','{}',now())",(batch,'a'*64),psycopg.errors.ForeignKeyViolation)]:
  try:
   with c.transaction():c.execute(query,params)
  except error:pass
  else:raise AssertionError('constraint missing')
print('PASS: evidence bytes, quarantine, idempotence, immutable original, cross-organization snapshot/risk denial')
