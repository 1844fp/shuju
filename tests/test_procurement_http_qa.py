import unittest,threading,socket,time,json
from pathlib import Path
import test_identity as fixture
import app as core,httpx,uvicorn
class ProcurementHTTPQA(unittest.TestCase):
 def test_exact_five_documents_permissions_and_mismatch(self):
  f=fixture.IdentityTests();f.setUp();server=None;thread=None
  try:
   with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
   server=uvicorn.Server(uvicorn.Config(core.app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run);thread.start()
   for _ in range(100):
    if server.started:break
    time.sleep(.02)
   with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as c:
    base='/api/v1/finance-workbench/procurement';path=base+'/evidence'
    p=dict(case_id='QA-exact',kind='contract',external_id='qa',version='v1',date='2026-11-07',currency='CNY',amount='999999999999.99',supplier='SIM-S',quantity='2.000001',source_reference='simulated:source<&>',data_kind='simulated')
    self.assertEqual(c.post(path,json=p).status_code,401)
    def login(name):self.assertEqual(c.post('/api/v1/auth/login',json={'username':name,'password':'Test-password-123'}).status_code,200)
    login('reader-a');self.assertEqual(c.post(path,json=p).status_code,403);login('admin-a')
    a=c.post(path,json=p);self.assertEqual(a.status_code,201,a.text);self.assertEqual(c.post(path,json=p).json()['status'],'already_registered');self.assertEqual(c.post(path,json={**p,'amount':'999999999999.98'}).status_code,409)
    partial=c.get(base+'/QA-exact/match').json();self.assertEqual(partial['status'],'quarantined');self.assertEqual(len(partial['missing']),4)
    for kind in ('purchase_order','receipt','invoice','payment'):self.assertEqual(c.post(path,json={**p,'kind':kind}).status_code,201)
    exact=c.get(base+'/QA-exact/match').json();self.assertEqual(exact['status'],'matched');self.assertEqual(len(exact['evidence']),5)
    for e in exact['evidence'].values():self.assertEqual(e['source']['amount'],'999999999999.99');self.assertEqual(e['source']['quantity'],'2.000001');self.assertEqual(len(e['sha256']),64)
    self.assertEqual(c.get(base+'/QA-exact/match',params={'currency':'USD'}).status_code,404)
    login('admin-b');self.assertEqual(c.get(base+'/QA-exact/match').status_code,404);login('admin-a')
    for kind in ('contract','purchase_order','receipt','invoice','payment'):
     self.assertEqual(c.post(path,json={**p,'case_id':'QA-mismatch','kind':kind,'amount':'999999999999.98' if kind=='payment' else p['amount']}).status_code,201)
    mismatch=c.get(base+'/QA-mismatch/match').json();self.assertEqual(mismatch['status'],'quarantined');self.assertEqual([x['field'] for x in mismatch['differences']],['amount'])
    # Independently supplied manifest controls, not computed by reconcile/observe.
    raw=b'external_id,date,currency,department,amount\nSIM-QA,2026-11-07,CNY,D01,12.30\n'
    preview=c.post('/api/v1/theme-imports/budget/preview',files={'file':('qa.csv',raw)},data={'data_kind':'simulated'});self.assertEqual(preview.status_code,201,preview.text);jid=preview.json()['preview_id'];mbase='/api/v1/theme-imports/'+jid
    self.assertEqual(c.get(mbase+'/source-manifest').json()['report']['status'],'not_assessed')
    import hashlib
    manifest=dict(version='source-control-v1',organization_id=f.a['id'],theme='budget',source_sha256=hashlib.sha256(raw).hexdigest(),row_count=1,business_key_count=1,currency_totals={'CNY':{'amount':'12.30'}})
    login('reader-a');self.assertEqual(c.put(mbase+'/source-manifest',json=manifest).status_code,403);login('admin-b');self.assertEqual(c.get(mbase+'/source-manifest').status_code,404);login('admin-a')
    mr=c.put(mbase+'/source-manifest',json=manifest);self.assertEqual(mr.status_code,200,mr.text);self.assertEqual(mr.json()['report']['status'],'matched');self.assertEqual(c.put(mbase+'/source-manifest',json={**manifest,'row_count':2}).status_code,409);self.assertEqual(c.post(mbase+'/confirm').status_code,200)
    raw2=raw.replace(b'SIM-QA',b'SIM-BAD');p2=c.post('/api/v1/theme-imports/budget/preview',files={'file':('qa.csv',raw2)},data={'data_kind':'simulated'}).json();badbase='/api/v1/theme-imports/'+p2['preview_id'];badmanifest={**manifest,'source_sha256':hashlib.sha256(raw2).hexdigest(),'row_count':2}
    br=c.put(badbase+'/source-manifest',json=badmanifest);self.assertEqual(br.json()['report']['status'],'mismatched');self.assertEqual(c.post(badbase+'/confirm').status_code,409)
    Path('work/redesign/manifest-http-qa.json').write_text(json.dumps({'transport':'real TCP HTTP','matched':mr.json(),'mismatched':br.json(),'mismatch_confirmation':409,'immutable_overwrite':409},indent=2),encoding='utf-8')
    out=Path('work/redesign/procurement-http-qa.json');out.write_text(json.dumps({'transport':'real TCP HTTP','matched':exact,'mismatch':mismatch,'permission_checks':'anonymous401 reader403 other_org404 other_currency404','amount_delta':'0.01'},indent=2),encoding='utf-8')
  finally:
   if server:server.should_exit=True
   if thread:thread.join(10)
   f.tearDown()
if __name__=='__main__':unittest.main(verbosity=2)
