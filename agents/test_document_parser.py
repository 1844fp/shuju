import unittest,io,zipfile
from agents.document_parser import parse_document
class ParserTests(unittest.TestCase):
 def docx(self,text):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p></w:body></w:document>')
  return b.getvalue()
 def test_docx(self):
  d=parse_document(self.docx('应收账款催收'),'x.docx',title='制度',version='1',effective_date='2026-01-01')
  self.assertEqual(d[0]['text'],'应收账款催收');self.assertIn('paragraph 1',d[0]['locator']);self.assertNotIn('page',d[0]);self.assertEqual(len(d[0]['source_sha256']),64)
 def test_bomb_size_date(self):
  with self.assertRaises(ValueError):parse_document(self.docx('a'*100000),'x.docx',title='x',version='1',effective_date='2026-01-01')
  with self.assertRaises(ValueError):parse_document(b'x'*(5*1024*1024+1),'x.pdf',title='x',version='1',effective_date='2026-01-01')
  with self.assertRaises(ValueError):parse_document(b'x','x.docx',title='x',version='1',effective_date='invalid')
 def test_pdf_pages(self):
  from reportlab.pdfgen.canvas import Canvas
  b=io.BytesIO();c=Canvas(b);c.drawString(10,700,'Page one policy');c.showPage();c.drawString(10,700,'Page two evidence');c.save()
  docs=parse_document(b.getvalue(),'x.pdf',title='policy',version='2',effective_date='2026-01-01')
  self.assertEqual([d['page'] for d in docs],[1,2]);self.assertIn('Page two',docs[1]['text'])
if __name__=='__main__':unittest.main()
