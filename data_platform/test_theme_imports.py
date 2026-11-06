"""Cross-theme simulated fixtures and parser acceptance. Run from project root."""
import unittest,csv,io,base64
from pathlib import Path
from theme_imports import SCHEMAS,BASE,parse_csv
ROOT=Path(__file__).resolve().parent

def fixture(theme,**changes):
 row={k:'SIM-'+k for k in {**BASE,**SCHEMAS[theme]}}
 for k,t in {**BASE,**SCHEMAS[theme]}.items():
  if t in ('money','signed'):row[k]='12.30' if k!='settled' else '0.00'
  elif t=='date':row[k]='2026-01-01'
  elif t=='currency':row[k]='CNY'
  elif t=='statement':row[k]='income'
  elif t=='direction':row[k]='inflow'
 row.update(changes)
 stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=list(row));w.writeheader();w.writerow(row)
 return stream.getvalue().encode()
class Themes(unittest.TestCase):
 def test_all_themes(self):
  for theme in SCHEMAS:
   with self.subTest(theme=theme):
    raw=fixture(theme);result=parse_csv(raw,theme,'org-a','simulated')
    self.assertEqual(len(result['accepted']),1);self.assertFalse(result['quarantined'])
    self.assertEqual(base64.b64decode(result['source']['original_base64']),raw)
    self.assertEqual(result,parse_csv(raw,theme,'org-a','simulated'))
    self.assertNotEqual(result['file_key'],parse_csv(raw,theme,'org-b','simulated')['file_key'])
 def test_precision_and_nonfinite(self):
  for bad in ['1.001','NaN','Infinity','-1','1000000000000000000']:
   r=parse_csv(fixture('invoices',amount=bad),'invoices','org','simulated')
   self.assertEqual(len(r['quarantined']),1);self.assertFalse(r['accepted'])
 def test_duplicate_atomic(self):
  raw=fixture('invoices');raw+=raw.splitlines(keepends=True)[1]
  self.assertEqual(len(parse_csv(raw,'invoices','org','simulated')['quarantined']),2)
 def test_settlement(self):
  self.assertEqual(len(parse_csv(fixture('payables',settled='99.00'),'payables','org','simulated')['quarantined']),1)
 def test_schema(self):
  with self.assertRaises(ValueError):parse_csv(b'unknown\n1\n','bank','org','simulated')
if __name__=='__main__':
 for theme in SCHEMAS:
  (ROOT/'theme_templates'/(theme+'.csv')).write_bytes(fixture(theme))
 unittest.main()
