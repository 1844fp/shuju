import unittest,io,csv,zipfile
from pathlib import Path
from openpyxl import Workbook
from theme_imports import parse_xlsx,parse_csv,SCHEMAS
from test_theme_imports import fixture
OUT=Path('work/redesign/xlsx-themes');OUT.mkdir(parents=True,exist_ok=True)
def book(theme):
 w=Workbook();s=w.active
 for row in csv.reader(io.StringIO(fixture(theme).decode())):s.append(row)
 b=io.BytesIO();w.save(b);return b.getvalue()
def patch(raw,name,content):
 out=io.BytesIO()
 with zipfile.ZipFile(io.BytesIO(raw)) as z,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as dest:
  for n in z.namelist():dest.writestr(n,content if n==name else z.read(n))
 return out.getvalue()
class Xlsx(unittest.TestCase):
 def test_eight_actual_files(self):
  import base64
  for theme in SCHEMAS:
   raw=book(theme);(OUT/(theme+'.xlsx')).write_bytes(raw)
   a=parse_xlsx(raw,theme,'org','simulated');b=parse_csv(fixture(theme),theme,'org','simulated')
   self.assertEqual(a['accepted'],b['accepted']);self.assertEqual(base64.b64decode(a['source']['original_base64']),raw)
 def test_formula(self):
  raw=book('invoices')
  with zipfile.ZipFile(io.BytesIO(raw)) as z:xml=z.read('xl/worksheets/sheet1.xml').replace(b'<sheetData>',b'<sheetData><row r="99"><c r="A99"><f>1+1</f><v>2</v></c></row>')
  with self.assertRaisesRegex(ValueError,'formula'):parse_xlsx(patch(raw,'xl/worksheets/sheet1.xml',xml),'invoices','org','simulated')
 def test_external(self):
  raw=book('bank')
  xml=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="x" Target="https://example.com" TargetMode="External" Type="x"/></Relationships>'
  with self.assertRaisesRegex(ValueError,'external'):parse_xlsx(patch(raw,'_rels/.rels',xml),'bank','org','simulated')
 def test_zip_limit(self):
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   for i in range(1001):z.writestr(str(i),'x')
  with self.assertRaisesRegex(ValueError,'zip_limit'):parse_xlsx(raw.getvalue(),'bank','org','simulated')
 def test_raw_xml_precision(self):
  raw=book('invoices')
  with zipfile.ZipFile(io.BytesIO(raw)) as z:xml=z.read('xl/worksheets/sheet1.xml').replace(b'<c r="F2" t="inlineStr"><is><t>12.30</t></is></c>',b'<c r="F2" t="n"><v>999999999999999999.99</v></c>')
  # Amount column is last; patch by matching its text representation irrespective coordinate.
  import re
  with zipfile.ZipFile(io.BytesIO(raw)) as z:xml=re.sub(rb'<c r="([A-Z]+2)" t="inlineStr"><is><t>12.30</t></is></c>',rb'<c r="\1" t="n"><v>999999999999999999.99</v></c>',z.read('xl/worksheets/sheet1.xml'))
  r=parse_xlsx(patch(raw,'xl/worksheets/sheet1.xml',xml),'invoices','org','simulated')
  self.assertEqual(r['accepted'][0]['normalized']['amount'],'999999999999999999.99')
if __name__=='__main__':unittest.main()
