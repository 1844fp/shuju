import io,sys,zipfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in ('work/runtime','work/export-runtime','backend'):sys.path.insert(0,str(ROOT/p))
import report_exports as exports
class DocxExports(unittest.TestCase):
 def test_precision_source_and_package(self):
  row=dict(period='2026-01',currency='CNY',revenue='999999999999.99',cost='0.00',expense='0.01',gross_profit='999999999999.99',operating_profit='999999999999.98',gross_margin=None,metric_version='1.0',data_kind=['simulated'],batch_ids=['source<&>'])
  data=exports.docx_bytes([row],'2026-01','2026-12','CNY')
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   self.assertIsNone(z.testzip());self.assertIn('[Content_Types].xml',z.namelist());self.assertIn('_rels/.rels',z.namelist())
   for name in z.namelist():ET.fromstring(z.read(name))
   doc=ET.fromstring(z.read('word/document.xml'));text=''.join(doc.itertext())
   for expected in (row['revenue'],row['operating_profit'],'source<&>','simulated','不适用'):self.assertIn(expected,text)
   self.assertFalse(doc.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fldChar'))
  out=ROOT/'work/redesign/finance-preview.docx';out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
if __name__=='__main__':unittest.main(verbosity=2)
