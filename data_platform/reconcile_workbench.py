"""Read-only, organization-scoped reconciliation; amounts remain Decimal strings."""
import argparse,json,hashlib,os
from collections import Counter

def report(connection,organization):
 rows=connection.execute('SELECT document_id,document_kind,source_sha256,original_content,original_payload,validation_status,quality_errors FROM ods.workbench_evidence WHERE organization_id=%s',(organization,)).fetchall()
 kinds=Counter();quality=Counter();mismatches=[];sources=Counter()
 for doc,kind,digest,raw,payload,status,errors in rows:
  kinds[kind]+=1;quality[status]+=1;sources[payload.get('data_kind','unspecified')]+=1
  if hashlib.sha256(bytes(raw)).hexdigest()!=digest:mismatches.append(doc)
 return {'organization_id':organization,'basis':'stored immutable snapshots, not external source completeness','document_count':len(rows),'topics':dict(kinds),'quality':dict(quality),'data_kind':dict(sources),'hash_mismatch_ids':mismatches,'source_completeness':'not_assessed_without_source_manifest','risk_evidence_count':connection.execute('SELECT count(*) FROM metadata.workbench_risk_evidence WHERE organization_id=%s',(organization,)).fetchone()[0]}
if __name__=='__main__':
 import psycopg
 p=argparse.ArgumentParser();p.add_argument('--organization',required=True);a=p.parse_args()
 with psycopg.connect(os.environ['DATABASE_URL']) as c:
  c.execute('SET TRANSACTION READ ONLY')
  print(json.dumps(report(c,a.organization),ensure_ascii=False,indent=2))
