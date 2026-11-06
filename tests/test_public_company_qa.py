import unittest,json,tempfile,shutil
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
import test_identity as fixture
import public_company as pc
@unittest.skipUnless((pc.ROOT/'facts.json').is_file() and (pc.ROOT/'manifest.json').is_file(), 'Public annual corpus absent; run python data_platform/msft_annual.py')
class PublicCompanyQA(unittest.TestCase):
 def setUp(self):
  self.f=fixture.IdentityTests();self.f.setUp();self.addCleanup(self.f.tearDown)
  if not any(r.path=='/api/v1/public-company' for r in fixture.app.app.routes):pc.install(fixture.app.app)
 def test_auth_all_100_facts_and_ratios(self):
  c=self.f.client;self.assertEqual(c.get('/api/v1/public-company').status_code,401);self.f.login('reader-a')
  r=c.get('/api/v1/public-company');self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['fact_count'],100)
  data=c.get('/api/v1/public-company/annual-metrics').json();self.assertEqual(data['data_kind'],'public_disclosure');self.assertIn('not harmonized',data['comparability_warning']);self.assertEqual(len(data['years']),10)
  self.assertIsNone(data['years'][0]['ratios']['revenue_growth']['value'])
  for y in data['years']:
   self.assertEqual(len(y['facts']),10);a={k:Decimal(v) for k,v in y['amounts'].items()};self.assertEqual(a['total_assets'],a['total_liabilities']+a['equity'])
   for ratio,n,d in [('net_margin','net_income','revenue'),('operating_margin','operating_income','revenue'),('debt_ratio','total_liabilities','total_assets')]:self.assertEqual(Decimal(y['ratios'][ratio]['value']),a[n]/a[d])
  last=data['years'][-1];self.assertEqual(last['amounts']['revenue'],'281724000000.00');self.assertEqual(last['amounts']['net_income'],'101832000000.00')
  source=c.get('/api/v1/public-company/sources/2025');import hashlib
  self.assertEqual(hashlib.sha256(source.content).hexdigest(),source.headers['x-source-sha256'])
 def test_source_tamper_fails_closed(self):
  with tempfile.TemporaryDirectory(dir='work') as d:
   target=Path(d)/'corpus';shutil.copytree(pc.ROOT,target)
   with (target/'ar2025.html').open('ab') as f:f.write(b'QA-TAMPER')
   self.f.login('admin-a')
   with patch.object(pc,'ROOT',target):
    for path in ('','/annual-metrics','/backtest','/sources/2025'):
     r=self.f.client.get('/api/v1/public-company'+path);self.assertEqual(r.status_code,503,r.text)
 def test_backtest_no_future_leakage_and_exact_baseline(self):
  self.f.login('admin-a');r=self.f.client.get('/api/v1/public-company/backtest');self.assertEqual(r.status_code,200,r.text);r=r.json();self.assertEqual(len(r['predictions']),7)
  facts=json.loads((pc.ROOT/'facts.json').read_text());revenue={f['fiscal_year']:Decimal(f['amount_usd']) for f in facts if f['metric']=='revenue'}
  errors=[];naive=[]
  for p in r['predictions']:
   year=p['year'];self.assertEqual(p['training_years'],list(range(year-3,year)));self.assertTrue(all(x<year for x in p['training_years']))
   expected=sum((revenue[x] for x in range(year-3,year)),Decimal(0))/3
   self.assertEqual(Decimal(p['rolling3mean']),expected);self.assertEqual(Decimal(p['naive']),revenue[year-1]);errors.append(abs(revenue[year]-expected));naive.append(abs(revenue[year]-revenue[year-1]))
  self.assertEqual(Decimal(r['rolling_mae']),sum(errors)/7);self.assertEqual(Decimal(r['naive_mae']),sum(naive)/7)
  original=pc.load;loaded=original();changed=[dict(f) for f in loaded[0]]
  for f in changed:
   if f['fiscal_year']==2025 and f['metric']=='revenue':f['amount_usd']='999999999999999.00'
  with patch.object(pc,'load',return_value=(changed,loaded[1],loaded[2])):altered=pc.backtest()
  self.assertEqual(r['predictions'][:-1],altered['predictions'][:-1]);self.assertEqual(r['predictions'][-1]['rolling3mean'],altered['predictions'][-1]['rolling3mean'])
if __name__=='__main__':unittest.main(verbosity=2)
