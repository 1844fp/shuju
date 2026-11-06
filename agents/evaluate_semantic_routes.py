"""R10 real MiniLM + authenticated upload/hybrid/source routes, no external model."""
import os,sys,json,hashlib,io,zipfile,tempfile,time
from pathlib import Path
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
OUT=ROOT/'work/public-company/semantic-evaluation'
def main():
 import app as core,identity
 from fastapi.testclient import TestClient
 from unittest.mock import patch
 facts=json.loads((ROOT/'work/public-company/msft-2016-2025/facts.json').read_text())
 OUT.mkdir(parents=True,exist_ok=True);paragraphs=[]
 for year in range(2016,2026):
  selected=[f for f in facts if f['fiscal_year']==year and f['metric'] in ('revenue','operating_income','net_income')]
  source=selected[0]
  assert hashlib.sha256((ROOT/'work/public-company/msft-2016-2025'/source['local_file']).read_bytes()).hexdigest()==source['source_sha256']
  text=f'公开年报二次整理，非原年报。微软 Microsoft FY{year} 财年。单位 USD million 百万美元；口径 {source["disclosure_version"]}。'+ ' '.join(f'{f["metric"]}={f["reported_value"]}' for f in selected)+f' 原年报URL {source["source_url"]} 原年报SHA256 {source["source_sha256"]}'
  paragraphs.append(text)
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
  z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join('<w:p><w:r><w:t>'+escape(t)+'</w:t></w:r></w:p>' for t in paragraphs)+'</w:body></w:document>')
 raw=b.getvalue();(OUT/'public-secondary-compilation.docx').write_bytes(raw);checks=[];responses=[];started=time.monotonic()
 def check(name,value):checks.append({'name':name,'passed':bool(value)})
 old=getattr(core.app.state,'db',None);oldroot=getattr(core.app.state,'tenant_root',None)
 with tempfile.TemporaryDirectory(dir=ROOT/'work') as temp:
  core.app.state.db=core.engine('sqlite:///'+str(Path(temp)/'control.sqlite'));core.app.state.tenant_root=Path(temp)/'tenants'
  with patch.dict(os.environ,{'FINAGENT_AUTH_MODE':'users','HF_HUB_OFFLINE':'1','HF_HOME':str(ROOT/'work/model-cache')}):
   try:
    a=identity.create_org('semantic-A');b_org=identity.create_org('semantic-B')
    for name,org in [('semantic-a',a),('semantic-b',b_org)]:identity.create_user(name,'Test-only-semantic-927!',org['id'],'org_admin')
    with TestClient(core.app) as client:
     def login(name):
      r=client.post('/api/v1/auth/login',json={'username':name,'password':'Test-only-semantic-927!'});assert r.status_code==200
     login('semantic-a')
     upload=client.post('/api/v1/knowledge/upload',files={'file':('public-secondary.docx',raw)},data={'title':'微软十年公开财报二次整理','version':'R10-1','effective_date':'2026-11-06'})
     check('upload_201',upload.status_code==201);u=upload.json();check('ten_paragraphs',u.get('chunks')==10);check('file_sha',u.get('source_sha256')==hashlib.sha256(raw).hexdigest())
     init=client.post('/api/v1/knowledge/semantic-initialize');check('real_minilm_ready',init.json().get('status')=='ready')
     queries=[f'微软FY{year}经营利润 operating_income 与净利润 net_income USD million' for year in range(2016,2026)]+['微软FY2016和FY2025收入 revenue对比']
     for index,q in enumerate(queries):
      r=client.get('/api/v1/knowledge/hybrid-search',params={'q':q,'limit':10});payload=r.json();hits=payload.get('matches',[])
      check(f'query_{index}_200',r.status_code==200);check(f'query_{index}_citation',payload.get('citation_validation',{}).get('valid'))
      if index<10:check(f'query_{index}_top1_year',bool(hits) and f'FY{2016+index}' in hits[0]['text'])
      expected=[2016+index] if index<10 else [2016,2025]
      check(f'query_{index}_years',all(any(f'FY{year}' in x['text'] for x in hits) for year in expected))
      check(f'query_{index}_source_locator',bool(hits) and all(x.get('source_sha256')==u.get('source_sha256') and 'DOCX paragraph' in x['locator'] and '原年报SHA256' in x['text'] and x.get('model_revision') for x in hits))
      check(f'query_{index}_real_semantic',any('semantic' in x.get('ranks',{}) for x in hits))
      responses.append({'query':q,'response':payload})
     original=client.get('/api/v1/knowledge/sources/'+u['source_id']);check('source_download_sha',hashlib.sha256(original.content).hexdigest()==hashlib.sha256(raw).hexdigest())
     early=client.get('/api/v1/knowledge/hybrid-search',params={'q':'微软收入','as_of':'2025-01-01'});check('effective_filter',early.json().get('matches')==[])
     login('semantic-b');other=client.get('/api/v1/knowledge/hybrid-search',params={'q':'微软FY2025收入'})
     check('tenant_b_no_matches',other.json().get('matches')==[]);check('tenant_b_source_404',client.get('/api/v1/knowledge/sources/'+u['source_id']).status_code==404)
   finally:
    for key,engine in list(identity.engines.items()):
     if key.startswith(str(Path(temp))):engine.dispose();identity.engines.pop(key)
    core.app.state.db.dispose();core.app.state.db=old
    if oldroot is None:del core.app.state.tenant_root
    else:core.app.state.tenant_root=oldroot
 result={'method':'real authenticated routes + local MiniLM + BM25/RRF','external_model_calls':0,'seconds':round(time.monotonic()-started,3),'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'checks':checks,'responses':responses}
 (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k not in ('checks','responses')}))
if __name__=='__main__':main()
