import unittest,tempfile,shutil
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import public_company as p
class Tests(unittest.TestCase):
 def test_real_snapshot(self):
  a=FastAPI();p.install(a);c=TestClient(a);r=c.get('/api/v1/public-company');self.assertEqual(r.status_code,200);self.assertEqual(len(r.json()['fiscal_years']),10)
  rows=c.get('/api/v1/public-company/annual-metrics').json()['years'];self.assertIsNone(rows[0]['ratios']['revenue_growth']['value']);v=rows[0]['amounts'];self.assertEqual(rows[0]['ratios']['net_margin']['value'],str(Decimal(v['net_income'])/Decimal(v['revenue'])))
  b=c.get('/api/v1/public-company/backtest').json();self.assertEqual(len(b['predictions']),7)
  for x in b['predictions']:self.assertEqual(x['training_years'],list(range(x['year']-3,x['year'])));self.assertTrue(all(y<x['year'] for y in x['training_years']))
  x=b['predictions'][0];expected=sum((Decimal(y['amounts']['revenue']) for y in rows[:3]),Decimal(0))/3;self.assertEqual(Decimal(x['rolling3mean']),expected)
  self.assertEqual(c.get('/api/v1/public-company/annual-metrics?start_year=2000').status_code,422)
  self.assertEqual(c.get('/api/v1/public-company/sources/2016').headers['x-source-sha256'],rows[0]['source']['source_sha256'])
  with tempfile.TemporaryDirectory(dir='work') as d:
   target=Path(d)
   for f in p.ROOT.iterdir():
    if f.suffix in ('.json','.html'):shutil.copyfile(f,target/f.name)
   with (target/'ar2016.html').open('ab') as f:f.write(b'tamper')
   with patch.object(p,'ROOT',target):self.assertEqual(c.get('/api/v1/public-company').status_code,503)
if __name__=='__main__':unittest.main()
