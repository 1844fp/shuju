"""Public-only, capped real-model annual-report evidence evaluation. No mocks."""
import os,json,hashlib,time,re
from pathlib import Path
from decimal import Decimal
from urllib.request import Request,build_opener
from agents.provider import NoRedirect
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'work/public-company/msft-2016-2025'
OUT=ROOT/'work/public-company/model-evaluation'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 # Load only model configuration, never serialize credentials or endpoints.
 for line in (ROOT/'.env').read_text(encoding='utf-8-sig').splitlines():
  if '=' in line and not line.lstrip().startswith('#'):
   k,v=line.split('=',1);k=k.strip()
   if k in ('FINAGENT_MODEL_API_KEY','FINAGENT_MODEL','FINAGENT_MODEL_BASE_URL','OPENAI_API_KEY','OPENAI_MODEL','OPENAI_BASE_URL'):os.environ.setdefault(k,v.strip().strip('"').strip("'"))
 key=os.getenv('FINAGENT_MODEL_API_KEY') or os.getenv('OPENAI_API_KEY');model=os.getenv('FINAGENT_MODEL') or os.getenv('OPENAI_MODEL');base=os.getenv('FINAGENT_MODEL_BASE_URL') or os.getenv('OPENAI_BASE_URL')
 facts=json.loads((DATA/'facts.json').read_text());manifest=json.loads((DATA/'manifest.json').read_text());checks=[]
 for source in manifest:
  raw=(DATA/source['local_file']).read_bytes();checks.append(hashlib.sha256(raw).hexdigest()==source['source_sha256'])
 for f in facts:
  source=next(x for x in manifest if x['fiscal_year']==f['fiscal_year'])
  checks.append(f['source_sha256']==source['source_sha256'] and f['unit']=='million' and f['currency']=='USD' and f['disclosure_version']==f"FY{f['fiscal_year']}-original-annual-report" and Decimal(f['reported_value'])*1000000==Decimal(f['amount_usd']))
  html=(DATA/f['local_file']).read_text(encoding='utf8')
  from bs4 import BeautifulSoup
  normalized=' '.join(BeautifulSoup(html,'html.parser').stripped_strings)
  checks.append(all(' '.join(str(cell).split()) in normalized for cell in f['source_row'] if str(cell).strip()))
 if not all(checks):raise ValueError('public source validation failed')
 cases=[]
 for year in range(2016,2026):
  selected=[f for f in facts if f['fiscal_year']==year and f['metric'] in ('revenue','operating_income','net_income')]
  cases.append({'id':f'FY{year}','question':f'给出FY{year}收入、经营利润与净利润，不能混淆两种利润。','facts':selected,'expected':selected})
 cases.append({'id':'cross_year','question':'比较FY2016和FY2025的收入，逐年列出，不合并口径。','facts':[f for f in facts if f['fiscal_year'] in (2016,2025) and f['metric']=='revenue']})
 cases[-1]['expected']=cases[-1]['facts']
 cases.append({'id':'missing','question':'FY2030的收入是多少？资料中不存在时拒答。','facts':[],'expected':[]})
 rows=[];start=time.monotonic();calls=0
 if not key or not model or not base:
  (OUT/'results.json').write_text(json.dumps({'status':'model_not_configured','source_checks':len(checks),'calls':0},indent=2));return
 from urllib.parse import urlparse
 u=urlparse(base)
 if u.scheme!='https' or u.username or u.query or u.fragment:raise ValueError('invalid provider URL')
 for case in cases[:12]:
  payload={'model':model,'max_completion_tokens':1200,'temperature':0,'messages':[{'role':'system','content':'Answer only JSON {"status":"answered"|"not_found","facts":[{"fiscal_year":integer,"metric":string,"reported_value":string,"unit":string,"currency":string,"source_sha256":string,"disclosure_version":string}]}. Use only supplied public evidence. Never invent facts. Keep operating_income distinct from net_income. Preserve original-year disclosure and million USD units.'},{'role':'user','content':json.dumps({'question':case['question'],'public_evidence':case['facts']},ensure_ascii=False)}]}
  t=time.monotonic();calls+=1
  # Persist attempt before network, so interrupted runs retain truthful call count.
  (OUT/'progress.json').write_text(json.dumps({'calls':calls,'case':case['id']}))
  try:
   req=Request(base.rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
   with build_opener(NoRedirect()).open(req,timeout=30) as response:
    raw=response.read(65537)
   if len(raw)>65536:raise ValueError('response limit')
   body=json.loads(raw);text=body['choices'][0]['message']['content'];answer=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip()))
   fields=('fiscal_year','metric','reported_value','unit','currency','source_sha256','disclosure_version')
   wanted=sorted([tuple(f[k] for k in fields) for f in case['expected']]);actual=sorted([tuple(f[k] for k in fields) for f in answer['facts']])
   passed=actual==wanted and answer['status']==('answered' if wanted else 'not_found')
   rows.append({'id':case['id'],'passed':passed,'seconds':round(time.monotonic()-t,3),'answer':answer,'usage':body.get('usage'),'expected':case['expected']})
  except Exception as exc:rows.append({'id':case['id'],'passed':False,'seconds':round(time.monotonic()-t,3),'error_type':type(exc).__name__})
  (OUT/'results.json').write_text(json.dumps({'status':'real_model','source_checks':len(checks),'calls':calls,'seconds':round(time.monotonic()-start,3),'passed':sum(x['passed'] for x in rows),'failed':sum(not x['passed'] for x in rows),'cases':rows},ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'calls':calls,'passed':sum(x['passed'] for x in rows),'failed':sum(not x['passed'] for x in rows)}))
if __name__=='__main__':main()
