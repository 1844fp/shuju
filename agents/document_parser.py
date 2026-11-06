"""Bounded local PDF/DOCX text extraction; no network, OCR or synthetic pages."""
import io,zipfile,hashlib
from datetime import date
from xml.etree import ElementTree as ET
MAX_INPUT=5*1024*1024

def parse_document(data:bytes,filename:str,*,title:str,version:str,effective_date:str)->list[dict]:
 date.fromisoformat(effective_date)
 if not title or len(title)>120 or not version or len(version)>40:raise ValueError('invalid metadata')
 if not isinstance(data,bytes) or not 0<len(data)<=MAX_INPUT:raise ValueError('file size limit')
 source=hashlib.sha256(data).hexdigest();parts=[]
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
 else:raise ValueError('unsupported document type')
 result=[]
 for text,locator,page in parts:
  for start in range(0,len(text),1800):
   chunk=text[start:start+2000]
   if len(result)>=100:raise ValueError('chunk limit')
   item=dict(id=hashlib.sha256((source+version+locator+str(start)).encode()).hexdigest(),title=title,version=version,effective_date=effective_date,locator=f'{locator}; characters {start}:{start+len(chunk)}',text=chunk,source_sha256=source,content_sha256=hashlib.sha256(chunk.encode()).hexdigest())
   if page is not None:item['page']=page
   result.append(item)
 if not result:raise ValueError('no extractable text; OCR not performed')
 return result
