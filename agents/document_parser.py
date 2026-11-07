"""Bounded local document text extraction with image OCR provenance."""
import io,zipfile,hashlib,re
from datetime import date
from pathlib import PurePath
from xml.etree import ElementTree as ET
MAX_INPUT=5*1024*1024

def selected_pdf_pages(value: str) -> tuple[int, ...]:
 if not value.strip():return ()
 if not re.fullmatch(r'\s*[1-9][0-9]{0,2}(?:\s*,\s*[1-9][0-9]{0,2}){0,3}\s*',value):
  raise ValueError('enter up to four comma-separated page numbers')
 return tuple(sorted({int(page) for page in value.split(',')}))


def parse_document(data:bytes,filename:str,*,title:str,version:str,effective_date:str,ocr_scanned_pdf:bool=False,ocr_pdf_pages:tuple[int,...]=())->list[dict]:
 date.fromisoformat(effective_date)
 if not title or len(title)>120 or not version or len(version)>40:raise ValueError('invalid metadata')
 if not isinstance(data,bytes) or not 0<len(data)<=MAX_INPUT:raise ValueError('file size limit')
 source=hashlib.sha256(data).hexdigest();parts=[];extraction={};page_extraction={}
 if (ocr_scanned_pdf or ocr_pdf_pages) and not filename.lower().endswith('.pdf'):raise ValueError('PDF OCR requires PDF')
 if filename.lower().endswith('.docx'):
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   entries=z.infolist()
   if len(entries)>500 or sum(x.file_size for x in entries)>20*1024*1024:raise ValueError('archive size limit')
   for x in entries:
    if x.file_size>MAX_INPUT or x.file_size/max(x.compress_size,1)>100 or x.flag_bits&1:raise ValueError('archive expansion limit')
   raw=z.read('word/document.xml')
   if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('XML entities forbidden')
   root=ET.fromstring(raw);ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
   for index,p in enumerate(root.iter(ns+'p'),1):
    text=''.join(x.text or '' for x in p.iter(ns+'t'))
    if text.strip():parts.append((text,f'DOCX paragraph {index}',None))
 elif filename.lower().endswith('.pdf'):
  if not data.startswith(b'%PDF-'):raise ValueError('invalid PDF')
  from pypdf import PdfReader
  reader=PdfReader(io.BytesIO(data),strict=True)
  if reader.is_encrypted or len(reader.pages)>100:raise ValueError('encrypted PDF or page limit')
  if any(page<1 or page>len(reader.pages) for page in ocr_pdf_pages):raise ValueError('OCR page outside PDF')
  scan_pages=set(ocr_pdf_pages)
  for index,page in enumerate(reader.pages,1):
   # Conservative compressed stream cap before text extraction.
   contents=page.get('/Contents')
   if contents:
    objects=contents if isinstance(contents,list) else [contents]
    for obj in objects:
     stream=obj.get_object()
     raw=getattr(stream,'_data',b'')
     if len(raw)>1024*1024:raise ValueError('PDF stream size limit')
     filters=stream.get('/Filter',[])
     if isinstance(filters,str):filters=[filters]
     for filter_name in filters:
      if filter_name=='/ASCII85Decode':
       import base64
       raw=base64.a85decode(raw,adobe=True)
      elif filter_name=='/FlateDecode':
       import zlib
       decoder=zlib.decompressobj();raw=decoder.decompress(raw,MAX_INPUT+1)
       if len(raw)>MAX_INPUT or decoder.unconsumed_tail:raise ValueError('PDF expansion limit')
      else:raise ValueError('unsupported bounded PDF filter')
   text=page.extract_text() or ''
   if len(text)>100000:raise ValueError('PDF page text limit')
   if text.strip():parts.append((text,f'PDF page {index}',index))
   elif ocr_scanned_pdf:scan_pages.add(index)
  if len(scan_pages)>4:raise ValueError('PDF OCR supports up to four pages total')
  if scan_pages:
   from agents.image_ocr import recognize
   for index in sorted(scan_pages):
    text,language=recognize(data,'.pdf',pdf_page=index)
    if text.strip():
     locator=f'PDF page {index} OCR'
     parts.append((text,locator,index))
     page_extraction[locator]={'extraction_method':'windows_ocr','ocr_language':language,'requires_review':True}
   parts.sort(key=lambda part:part[2])
 elif PurePath(filename).suffix.lower() in ('.png','.jpg','.jpeg'):
  from agents.image_ocr import recognize
  text,language=recognize(data,PurePath(filename).suffix.lower())
  if text.strip():parts.append((text,'Image OCR',None))
  extraction={'extraction_method':'windows_ocr','ocr_language':language,'requires_review':True}
 else:raise ValueError('unsupported document type')
 result=[]
 for text,locator,page in parts:
  for start in range(0,len(text),1800):
   chunk=text[start:start+2000]
   if len(result)>=100:raise ValueError('chunk limit')
   item=dict(id=hashlib.sha256((source+version+locator+str(start)).encode()).hexdigest(),title=title,version=version,effective_date=effective_date,locator=f'{locator}; characters {start}:{start+len(chunk)}',text=chunk,source_sha256=source,content_sha256=hashlib.sha256(chunk.encode()).hexdigest())
   if page is not None:item['page']=page
   item.update(page_extraction.get(locator,extraction))
   result.append(item)
 if not result:raise ValueError('no extractable text')
 return result
