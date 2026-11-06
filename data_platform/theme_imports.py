"""Pure standard-library theme CSV parser; never posts financial entries."""
import csv,io,json,hashlib,base64
from decimal import Decimal,InvalidOperation
from datetime import date
SCHEMAS={
 'balances':{'account_code':'text','opening_debit':'money','opening_credit':'money','closing_debit':'money','closing_credit':'money'},
 'statements':{'statement':'statement','item_code':'text','amount':'signed'},
 'receivables':{'counterparty':'text','due_date':'date','amount':'money','settled':'money'},
 'payables':{'counterparty':'text','due_date':'date','amount':'money','settled':'money'},
 'budget':{'department':'text','amount':'money'},
 'invoices':{'invoice_number':'text','supplier':'text','amount':'money'},
 'reimbursements':{'employee':'text','department':'text','invoice_number':'text','amount':'money'},
 'bank':{'account':'text','direction':'direction','amount':'money','reference':'text'}}
BASE={'external_id':'text','date':'date','currency':'currency'}
def digest(x):return hashlib.sha256(x).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def value(raw,kind):
 raw=raw.strip()
 if not raw:raise ValueError('required')
 if kind in ('money','signed'):
  try:
   n=Decimal(raw)
   if not n.is_finite() or abs(n)>=Decimal('1000000000000000000') or n!=n.quantize(Decimal('.01')) or (kind=='money' and n<0):raise ValueError('invalid_amount')
   return format(n,'.2f')
  except InvalidOperation:raise ValueError('invalid_amount') from None
 if kind=='date':return date.fromisoformat(raw).isoformat()
 if kind=='currency' and (len(raw)!=3 or not raw.isascii() or not raw.isalpha() or raw!=raw.upper()):raise ValueError('invalid_currency')
 if kind=='statement' and raw not in ('income','balance','cashflow'):raise ValueError('invalid_statement')
 if kind=='direction' and raw not in ('inflow','outflow'):raise ValueError('invalid_direction')
 return raw

def parse_csv(content,theme,organization,data_kind):
 if not isinstance(content,bytes) or not organization or data_kind not in ('simulated','uploaded'):raise ValueError('invalid_context')
 schema={**BASE,**SCHEMAS[theme]}
 reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig'),newline=''))
 if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or set(reader.fieldnames)!=set(schema):raise ValueError('invalid_columns')
 rows=list(reader);counts={}
 for row in rows:
  key=(row.get('external_id') or '').strip();counts[key]=counts.get(key,0)+1
 accepted=[];quarantined=[]
 for number,row in enumerate(rows,2):
  errors=[];normalized={}
  if None in row:errors.append({'field':'row','code':'extra_cells'})
  for field,kind in schema.items():
   try:normalized[field]=value(row.get(field) or '',kind)
   except (ValueError,AttributeError):errors.append({'field':field,'code':'invalid_'+kind})
  if counts[(row.get('external_id') or '').strip()]>1:errors.append({'field':'external_id','code':'duplicate_business_key'})
  if not errors and theme in ('receivables','payables') and Decimal(normalized['settled'])>Decimal(normalized['amount']):errors.append({'field':'settled','code':'exceeds_amount'})
  item={'source_row':number,'original_payload':row}
  if errors:quarantined.append({**item,'errors':errors})
  else:
   normalized['data_kind']=data_kind
   accepted.append({**item,'normalized':normalized,'business_key':digest(canonical([organization,theme,normalized['external_id']])),'row_hash':digest(canonical(normalized))})
 sha=digest(content)
 return {'schema_version':'theme-v1','organization_id':organization,'theme':theme,'data_kind':data_kind,'source':{'sha256':sha,'original_base64':base64.b64encode(content).decode()},'file_key':digest(canonical([organization,theme,sha])),'accepted':accepted,'quarantined':quarantined}

def parse_xlsx(content,theme,organization,data_kind,sheet=None):
 """Reuse ERP exact-XML reader after stricter whole-package safety checks."""
 import zipfile
 from xml.etree import ElementTree as ET
 if not isinstance(content,bytes) or len(content)>10*1024*1024:raise ValueError('xlsx_size_limit')
 with zipfile.ZipFile(io.BytesIO(content)) as archive:
  items=archive.infolist();names=[i.filename for i in items]
  if len(items)>1000 or len(names)!=len(set(names)) or sum(i.file_size for i in items)>50*1024*1024:raise ValueError('xlsx_zip_limit')
  for item in items:
   name=item.filename.lower()
   if item.flag_bits&1 or '..' in name.split('/') or name.startswith('/') or (item.compress_size and item.file_size/item.compress_size>200):raise ValueError('xlsx_unsafe_archive')
   if 'externallink' in name or 'vbaproject' in name:raise ValueError('xlsx_external_or_macro')
   if name.endswith(('.xml','.rels')):
    raw=archive.read(item)
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('xlsx_dtd')
    tree=ET.fromstring(raw)
    for node in tree.iter():
     if node.tag.split('}')[-1]=='f':raise ValueError('xlsx_formula')
     if node.attrib.get('TargetMode','').lower()=='external':raise ValueError('xlsx_external_relationship')
 from erp_imports import parse
 columns,records,info=parse(content,'theme.xlsx',sheet=sheet,header_row=1)
 text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=columns);writer.writeheader()
 for record in records:writer.writerow(record['values'])
 result=parse_csv(text.getvalue().encode('utf8'),theme,organization,data_kind)
 sha=digest(content);result['source']={'sha256':sha,'original_base64':base64.b64encode(content).decode()}
 result['file_key']=digest(canonical([organization,theme,sha]));result['parser']=info
 return result
