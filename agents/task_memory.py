"""Structured public/simulated task memory. Caller authenticates organization."""
import json,re,sqlite3,hashlib
from contextlib import closing
from agents.runtime import Query
PLANS={'finance':('analysis',),'budget':('budget',),'risk':('audit',),'full':('analysis','budget','audit')}
class TaskMemory:
 def __init__(self,path):
  from pathlib import Path
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  with closing(sqlite3.connect(self.path)) as db:
   db.execute('CREATE TABLE IF NOT EXISTS task_memory(org TEXT,task TEXT,payload TEXT,PRIMARY KEY(org,task))');db.commit()
 def load(self,org,task):
  with closing(sqlite3.connect(self.path)) as db:row=db.execute('SELECT payload FROM task_memory WHERE org=? AND task=?',(org,task)).fetchone()
  return json.loads(row[0]) if row else None
 def run(self,harness,task_id,organization_id,query,tools,*,intent,data_kind,references,resolve_source,approved=False,max_calls=10):
  if intent not in PLANS or data_kind not in ('public_disclosure','simulated'):raise ValueError('unsupported task memory')
  if not organization_id or not task_id or not callable(resolve_source) or len(references)>100:raise ValueError('invalid scope')
  refs=[]
  for ref in references:
   if set(ref)!={'id','sha256'} or not re.fullmatch('[a-zA-Z0-9_-]{1,128}',ref['id']) or not re.fullmatch('[0-9a-f]{64}',ref['sha256']):raise ValueError('invalid reference')
   if resolve_source(organization_id,ref['id'])!=ref['sha256']:return {'status':'stale_source','task_id':task_id}
   refs.append(ref.copy())
  plan={'query':Query(**query).model_dump(),'intent':intent,'data_kind':data_kind,'references':sorted(refs,key=lambda x:x['id'])}
  fingerprint=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
  with closing(sqlite3.connect(self.path,timeout=5)) as db:
   db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT payload FROM task_memory WHERE org=? AND task=?',(organization_id,task_id)).fetchone()
   if old and json.loads(old[0])['fingerprint']!=fingerprint:raise ValueError('task plan changed')
   if not old:db.execute('INSERT INTO task_memory VALUES(?,?,?)',(organization_id,task_id,json.dumps(dict(plan,fingerprint=fingerprint,status='planned'))))
   db.commit()
  result=harness.run(task_id,organization_id,plan['query'],tools,approved=approved,max_calls=max_calls,selected_roles=PLANS[intent])
  summary=dict(plan,fingerprint=fingerprint,status=result['status'],completed_roles=sorted(result['results']),trace=[{k:v for k,v in e.items() if k in ('node','status','attempts','duration_ms')} for e in result['trace']])
  with closing(sqlite3.connect(self.path)) as db:db.execute('UPDATE task_memory SET payload=? WHERE org=? AND task=?',(json.dumps(summary),organization_id,task_id));db.commit()
  return result
