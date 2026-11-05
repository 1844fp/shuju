"""Trusted operator worker. Server-side organization mapping, no client database paths."""
import os,sys,time,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for folder in ('runtime','agent-runtime','export-runtime','semantic-runtime'):sys.path.insert(0,str(root/'work'/folder))
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'backend'))
from configuration import load
load(root)
import app as core,identity,leased_jobs
from sqlalchemy import select

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--organization',default='local-demo');p.add_argument('--once',action='store_true');a=p.parse_args()
 core.app.state.db=core.engine()
 if a.organization=='local-demo':
  if os.getenv('FINAGENT_AUTH_MODE')=='users':p.error('用户模式必须指定服务器中已存在的组织UUID')
  db=core.app.state.db
 else:
  with identity.ctl().connect() as c:exists=c.execute(select(identity.organizations.c.id).where(identity.organizations.c.id==a.organization)).first()
  if not exists:p.error('组织不存在')
  db=identity.tenant_engine(a.organization)
 leased_jobs.initialize(db)
 try:
  while True:
   processed=leased_jobs.run_once(db,a.organization)
   if a.once:break
   if not processed:time.sleep(1)
 finally:db.dispose()
if __name__=='__main__':main()
