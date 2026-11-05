import io, unittest
from pathlib import Path
from openpyxl import load_workbook
import report_exports as e
class Tests(unittest.TestCase):
 def test_exports(self):
  r=dict(period='2026-01',currency='CNY',revenue='999999999999.99',cost='0.00',expense='0.00',gross_profit='999999999999.99',operating_profit='999999999999.99',gross_margin=None,metric_version='1.0',data_kind=['simulated'],batch_ids=['=HYPERLINK("bad")','+cmd','-cmd','@cmd'])
  out=Path('work/exports');out.mkdir(parents=True,exist_ok=True)
  data=e.xlsx_bytes([r],'2026-01','2026-12','CNY');(out/'qa.xlsx').write_bytes(data)
  w=load_workbook(io.BytesIO(data));self.assertEqual(w.active['C4'].value,r['revenue']);self.assertEqual(w.active['C4'].data_type,'s');self.assertTrue(all(c.data_type!='f' for row in w.active for c in row));self.assertTrue(w.active['K4'].value.startswith('='))
  pdf=e.pdf_bytes([r]*30,'2026-01','2026-12','CNY');(out/'qa.pdf').write_bytes(pdf)
  import fitz
  d=fitz.open(stream=pdf,filetype='pdf');self.assertGreater(len(d),1);self.assertIn('财务',d[0].get_text());self.assertIn(r['revenue'],d[0].get_text())
  for i in (0,len(d)-1):d[i].get_pixmap(matrix=fitz.Matrix(1,1)).save(str(out/f'page-{i+1}.png'))
  print('PDF pages:',len(d))
if __name__=='__main__':unittest.main()
