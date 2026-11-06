"""Isolated Compose validation; no .env loading or inherited model secrets."""
import subprocess,os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
exe=Path('C:/Users/82038/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe')
env={k:v for k,v in os.environ.items() if not k.startswith(('FINAGENT_','POSTGRES_','COMPOSE_'))};env['COMPOSE_DISABLE_ENV_FILE']='1'
base=[str(exe),'compose','--project-directory',str(ROOT),'-p','finagent-qa-isolated','-f',str(ROOT/'work/redesign/compose-isolated.json')]
# Explicit full configuration prevents port-list merging with shared Compose.
config={'services':{'backend':{'build':{'context':str(ROOT),'dockerfile':'infrastructure/Dockerfile.backend'},'ports':['127.0.0.1:18123:8000'],'environment':{'FINAGENT_AUTH_MODE':'demo','FINAGENT_TENANT_ROOT':'/data/tenants','FINAGENT_HARNESS_PATH':'/data/harness/checkpoints.sqlite'},'volumes':['qa_data:/data']},'next':{'build':{'context':str(ROOT),'dockerfile':'infrastructure/Dockerfile.next'},'ports':['127.0.0.1:13123:3000']},'postgres':{'image':'postgres:16-alpine','environment':{'POSTGRES_HOST_AUTH_METHOD':'trust','POSTGRES_DB':'finagent'},'volumes':['qa_pg:/var/lib/postgresql/data'] }},'volumes':{'qa_data':{},'qa_pg':{}}}
out=ROOT/'work/redesign';out.mkdir(parents=True,exist_ok=True);(out/'compose-isolated.json').write_text(json.dumps(config),encoding='utf-8')
results=[]
for cmd in [[str(exe),'version','--format','{{json .Server.Version}}'],base+['config','--quiet']]:
 try:
  r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=25);results.append({'check':'engine' if len(results)==0 else 'compose_config','code':r.returncode,'stderr':r.stderr[:1500]})
 except subprocess.TimeoutExpired:results.append({'check':'timeout','code':124})
(out/'docker-diagnostic.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(results,indent=2))
