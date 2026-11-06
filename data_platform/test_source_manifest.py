import unittest,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data_platform.theme_imports import parse_csv,SCHEMAS
from data_platform.source_manifest import reconcile,observe
from data_platform.test_theme_imports import fixture

def manifest(parsed):
 observed,_=observe(parsed)
 return {'version':'source-control-v1','organization_id':parsed['organization_id'],'theme':parsed['theme'],**observed}
class Controls(unittest.TestCase):
 def test_eight_themes(self):
  for theme in SCHEMAS:
   parsed=parse_csv(fixture(theme),theme,'org','simulated')
   self.assertEqual(reconcile(parsed)['status'],'not_assessed')
   self.assertEqual(reconcile(parsed,manifest(parsed))['status'],'matched')
 def test_external_mismatches(self):
  p=parse_csv(fixture('bank'),'bank','org','simulated');m=manifest(p)
  for key,bad in [('organization_id','other'),('theme','budget'),('row_count',2),('business_key_count',0),('source_sha256','0'*64),('currency_totals',{'CNY':{'amount':'99.00'}})]:
   changed=copy.deepcopy(m);changed[key]=bad
   self.assertEqual(reconcile(p,changed)['status'],'mismatched')
 def test_quarantined_duplicates_counted(self):
  raw=fixture('invoices');raw+=raw.splitlines(keepends=True)[1]
  p=parse_csv(raw,'invoices','org','simulated');o,_=observe(p)
  self.assertEqual(o['row_count'],2);self.assertEqual(o['business_key_count'],1)
  self.assertEqual(o['currency_totals']['CNY']['amount'],'24.60');self.assertFalse(p['accepted'])
 def test_currency_separation(self):
  a=fixture('bank');b=fixture('bank',external_id='other',currency='USD',amount='0.10')
  p=parse_csv(a+b.splitlines(keepends=True)[1],'bank','org','simulated');o,_=observe(p)
  self.assertEqual(o['currency_totals'],{'CNY':{'amount':'12.30'},'USD':{'amount':'0.10'}})
 def test_invalid_not_assessed(self):
  p=parse_csv(fixture('invoices',amount='NaN'),'invoices','org','simulated')
  self.assertEqual(reconcile(p,manifest(p))['status'],'not_assessed')
 def test_float_manifest_rejected(self):
  p=parse_csv(fixture('bank'),'bank','org','simulated');m=manifest(p);m['currency_totals']['CNY']['amount']=12.3
  with self.assertRaises(ValueError):reconcile(p,m)
if __name__=='__main__':unittest.main()
