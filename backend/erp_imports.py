"""ERP export ETL with immutable source snapshots and explicit reviewed commits."""
import csv,hashlib,io,json,re,threading,unicodedata,zipfile
from collections import defaultdict
from datetime import datetime,date,timedelta,timezone
from decimal import Decimal,InvalidOperation
from urllib.parse import quote
from xml.etree import ElementTree as ET
from fastapi import HTTPException,UploadFile,Form
from fastapi.responses import Response
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import MetaData,Table,Column,String,Text,LargeBinary,select
from sqlalchemy.exc import IntegrityError

META=MetaData()
FILES=Table('ods_erp_file',META,Column('id',String,primary_key=True),Column('digest',String,unique=True),Column('content',LargeBinary),Column('metadata',Text))
RUNS=Table('metadata_erp_run',META,Column('id',String,primary_key=True),Column('payload',Text))
LEDGER=Table('metadata_erp_ledger',META,Column('id',String,primary_key=True),Column('name',String))
RECEIPTS=Table('metadata_erp_receipt',META,Column('id',String,primary_key=True),Column('configuration',String),Column('batch_id',String))
LOCK=threading.RLock()
VERSION='erp-cleaning-1.0'
MAX_ROWS=10000
ALIASES={
 'posting_date':['posting_date','日期','凭证日期','制单日期','记账日期','dbill_date','FDate','PostingDate','AccountingDate','ACCOUNTING_DATE','BUDAT'],
 'voucher_no':['voucher_no','凭证号','凭证编号','ino_id','FNumber','AccountingDocument','JournalName','JE_HEADER_ID','BELNR'],
 'voucher_type':['voucher_type','凭证字','凭证类别','csign','FVoucherGroup','DocumentType','AccountingDocumentType','JournalCategory'],
 'line_no':['line_no','分录号','行号','分录行号','inid','FEntryID','LedgerGLLineItem','AccountingDocumentItem','JournalLineNumber','JE_LINE_NUM','BUZEI'],
 'account_code':['account_code','科目编码','科目代码','ccode','FAccountNumber','GLAccount','Account','ACCOUNT_CODE','HKONT'],
 'department_code':['department_code','部门编码','部门代码','cdept_id','FDepartmentNumber','CostCenter','Department','KOSTL'],
 'currency':['currency','币种','币别','币种编码','cexch_name','FCurrencyNumber','TransactionCurrency','CurrencyCode','CURRENCY_CODE','WAERS'],
 'debit':['debit','借方','借方金额','md','FDebit','DebitAmount','EnteredDr','ENTERED_DR'],
 'credit':['credit','贷方','贷方金额','mc','FCredit','CreditAmount','EnteredCr','ENTERED_CR'],
 'amount':['amount','金额','原币金额','AmountInTransactionCurrency','WRBTR'],
 'direction':['direction','借贷方向','方向','DebitCreditCode','ControllingDebitCreditCode','SHKZG'],
}
PROFILES={
 'generic':('通用凭证明细',['posting_date','voucher_type','voucher_no','line_no','account_code','department_code','currency','debit','credit']),
 'yonyou_u8':('用友 U8/U8+',['dbill_date','csign','ino_id','inid','ccode','cdept_id','cexch_name','md','mc']),
 'yonyou_bip':('用友 BIP/NC/U9',['凭证日期','凭证类别','凭证号','分录号','科目编码','部门编码','币种','借方金额','贷方金额']),
 'kingdee':('金蝶 星空/K3/KIS/星辰',['FDate','FVoucherGroup','FNumber','FEntryID','FAccountNumber','FDepartmentNumber','FCurrencyNumber','FDebit','FCredit']),
 'chanjet':('畅捷通 T+/好会计',['日期','凭证字','凭证号','行号','科目代码','部门代码','币别','借方','贷方']),
 'sap':('SAP',['PostingDate','DocumentType','AccountingDocument','LedgerGLLineItem','GLAccount','CostCenter','TransactionCurrency','DebitAmount','CreditAmount']),
 'oracle':('Oracle Fusion/EBS',['AccountingDate','JournalCategory','JournalName','JournalLineNumber','Account','Department','CurrencyCode','EnteredDr','EnteredCr']),
}
def norm(v):return unicodedata.normalize('NFKC',str(v if v is not None else '')).strip()
def hk(v):return re.sub(r'[\s_\-]+','',norm(v)).casefold()
def dump(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(v):return hashlib.sha256(v).hexdigest()
def db():META.create_all(core.current_db());return core.current_db()
def suggest(columns):
 mapping={};ambiguous={}
 for field,aliases in ALIASES.items():
  hits=[c for c in columns if hk(c) in {hk(a) for a in aliases}]
  if len(hits)==1:mapping[field]=hits[0]
  elif hits:ambiguous[field]=hits
 return mapping,ambiguous

class Options(BaseModel):
 model_config=ConfigDict(extra='forbid')
 mapping:dict[str,str]=Field(default_factory=dict)
 account_map:dict[str,str]=Field(default_factory=dict)
 currency_map:dict[str,str]=Field(default_factory=dict)
 default_currency:str|None=None
 default_department:str='UNASSIGNED'
 fill_down_headers:bool=False
 generate_line_numbers:bool=False
 amount_mode:str='split'
 data_kind:str='uploaded'
class Confirmation(BaseModel):
 model_config=ConfigDict(extra='forbid')
 cleaning_token:str
 acknowledge_quarantine:bool=False

def parse(content,name,sheet=None,header_row=None):
 if len(content)>10*1024*1024:raise HTTPException(413,'文件超过10MB')
 grid=[];types=[];info={}
 if name.lower().endswith('.csv'):
  if b'\0' in content:raise ValueError('CSV包含空字节')
  for encoding in ('utf-8-sig','gb18030'):
   try:text=content.decode(encoding);break
   except UnicodeError:pass
  else:raise ValueError('仅支持UTF-8/GB18030编码')
  try:delimiter=csv.Sniffer().sniff(text[:20000],delimiters=',;\t').delimiter
  except csv.Error:delimiter=','
  for row in csv.reader(io.StringIO(text),delimiter=delimiter,strict=True):
   if len(grid)>=MAX_ROWS+20 or len(row)>100:raise ValueError('超过10000数据行或100列')
   grid.append(row);types.append({})
  info=dict(encoding=encoding,delimiter=delimiter,sheets=[],sheet=None)
 elif name.lower().endswith('.xlsx'):
  from openpyxl import load_workbook
  if not zipfile.is_zipfile(io.BytesIO(content)):raise ValueError('无效XLSX文件')
  with zipfile.ZipFile(io.BytesIO(content)) as z:
   if len(z.infolist())>1000 or sum(x.file_size for x in z.infolist())>50*1024*1024:raise ValueError('XLSX展开超过限额')
   if any('vbaproject' in n.lower() for n in z.namelist()):raise ValueError('不接受含宏文件')
   # Raw numeric XML is retained as decimal text, never calculated with floats.
   exact={};ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
   for path in z.namelist():
    if path.startswith('xl/worksheets/') and path.endswith('.xml'):
     root=ET.fromstring(z.read(path))
     exact[path]={c.attrib['r']:c.find('s:v',ns).text for c in root.findall('.//s:c',ns) if c.attrib.get('t','n')=='n' and c.find('s:v',ns) is not None}
  w=load_workbook(io.BytesIO(content),read_only=True,data_only=False,keep_links=False)
  try:
   if len(w.sheetnames)>20:raise ValueError('工作表超过20个')
   if sheet and sheet not in w.sheetnames:raise ValueError('工作表不存在')
   ws=w[sheet or w.sheetnames[0]]
   if (ws.max_column or 0)>100 or (ws.max_row or 0)>MAX_ROWS+20:raise ValueError('超过行列上限')
   numeric=exact.get(getattr(ws,'_worksheet_path',''),{})
   for cells in ws.iter_rows():
    if len(grid)>=MAX_ROWS+20:raise ValueError('实际工作表行数超过上限')
    row=[];kind={}
    for i,c in enumerate(cells):
     value=c.value;kind[i]=c.data_type
     if isinstance(value,datetime):value=value.date().isoformat()
     elif isinstance(value,date):value=value.isoformat()
     elif c.data_type=='n' and getattr(c,'coordinate',None) in numeric:value=numeric[c.coordinate]
     row.append('' if value is None else str(value))
    grid.append(row);types.append(kind)
   info=dict(encoding='xlsx',sheet=ws.title,sheets=w.sheetnames)
  finally:w.close()
 else:raise ValueError('仅支持CSV/XLSX；XLS或BAK/MDF等账套须先导出')
 if not grid:raise ValueError('空文件')
 if header_row is None:
  score,index=max(((len(suggest(r)[0]),i) for i,r in enumerate(grid[:20])),key=lambda x:(x[0],-x[1]))
  if score<4:raise ValueError('未识别表头，请明确表头行')
  header_row=index+1
 if not 1<=header_row<=min(20,len(grid)):raise ValueError('表头须在前20行')
 columns=[norm(x) for x in grid[header_row-1]]
 while columns and not columns[-1]:columns.pop()
 if not columns or any(not x for x in columns) or len(set(map(hk,columns)))!=len(columns):raise ValueError('表头缺失或重复')
 records=[]
 for index,row in enumerate(grid[header_row:],header_row+1):
  if len(row)>len(columns) and any(norm(x) for x in row[len(columns):]):raise ValueError('数据行超出表头')
  records.append(dict(row_number=index,values={k:row[i] if i<len(row) else '' for i,k in enumerate(columns)},cell_types={k:types[index-1].get(i,'text') for i,k in enumerate(columns)}))
 if not 1<=len(records)<=MAX_ROWS:raise ValueError('数据须为1至10000行')
 return columns,records,{**info,'header_row':header_row}

def preview(content,name,profile,ledger,columns,records,info):
 if profile not in PROFILES:raise ValueError('未知字段预设')
 if not re.fullmatch(r'[A-Za-z0-9_.-]{1,50}',ledger):raise ValueError('账套标识须为1至50位字母数字或_.-')
 if not 1<=len(records)<=MAX_ROWS:raise ValueError('记录数超限')
 digest=sha(content);database=db()
 with LOCK,database.begin() as c:
  fid=c.execute(select(FILES.c.id).where(FILES.c.digest==digest)).scalar()
  if not fid:
   fid=core.uid();c.execute(FILES.insert().values(id=fid,digest=digest,content=content,metadata=dump(dict(name=name,created_at=core.now(),parser=info))))
  mapping,ambiguous=suggest(columns)
  v=dict(id=core.uid(),file_id=fid,file_sha256=digest,source_name=name,profile=profile,ledger_id=ledger,status='preview',columns=columns,source_rows=records,suggested_mapping=mapping,ambiguous_fields=ambiguous,parser=info,created_at=core.now(),cleaning_version=VERSION)
  c.execute(RUNS.insert().values(id=v['id'],payload=dump(v)))
 return public(v)
def get(identifier):
 with db().connect() as c:value=c.execute(select(RUNS.c.payload).where(RUNS.c.id==identifier)).scalar()
 if not value:raise HTTPException(404,'当前组织不存在该导入')
 return json.loads(value)
def public(value):return {k:v for k,v in value.items() if k not in ('source_rows','cleaned_rows','options')}|{'sample_rows':value['source_rows'][:5],'cleaning_options':value.get('options')}
def save(value):
 with db().begin() as c:c.execute(RUNS.update().where(RUNS.c.id==value['id']).values(payload=dump(value)))

def amount(value,currency):
 text=norm(value).replace('\u2212','-').replace(' ','')
 if not text:return Decimal(0)
 for prefix,expected in [('RMB','CNY'),('CNY','CNY'),('USD','USD'),('EUR','EUR'),('$','USD'),('€','EUR')]:
  if text.upper().startswith(prefix):
   if currency!=expected:raise ValueError('金额币种符号不匹配')
   text=text[len(prefix):];break
 if text.startswith('¥'):
  if currency not in ('CNY','JPY'):raise ValueError('金额币种符号不匹配')
  text=text[1:]
 if text.startswith('(') and text.endswith(')'):text='-'+text[1:-1]
 if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',text):raise ValueError('金额格式或千分位不规范')
 value=Decimal(text.replace(',',''))
 if not value.is_finite() or value!=value.quantize(Decimal('.01')):raise ValueError('金额须精确到分，不自动舍入')
 core.cents(abs(value));return value
def day(value):
 value=norm(value)
 odata=re.fullmatch(r'/Date\((-?\d+)([+-]\d{4})?\)/',value)
 if odata:
  offset=odata[2] or '+0000';hours,minutes=int(offset[1:3]),int(offset[3:5])
  if hours>23 or minutes>59:raise ValueError('OData日期时区无效')
  try:return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=int(odata[1]),minutes=(hours*60+minutes)*(1 if offset[0]=='+' else -1))).date().isoformat()
  except OverflowError:raise ValueError('OData日期超出范围') from None
 if 'T' in value:
  try:return datetime.fromisoformat(value.replace('Z','+00:00')).date().isoformat()
  except ValueError:pass
 for fmt in ('%Y-%m-%d','%Y/%m/%d','%Y.%m.%d','%Y年%m月%d日','%Y%m%d','%Y-%m-%d %H:%M:%S'):
  try:return datetime.strptime(value,fmt).date().isoformat()
  except ValueError:pass
 raise ValueError('日期须包含明确年月日')

def clean(identifier,options):
 with LOCK:
  v=get(identifier)
  if v['status']=='committed':raise HTTPException(409,'已入库批次不能重新清洗')
  o=options.model_dump();mapping=v['suggested_mapping'].copy()
  for field,column in o['mapping'].items():
   if column:mapping[field]=column
   else:mapping.pop(field,None)
  if set(mapping)-set(ALIASES) or any(c not in v['columns'] for c in mapping.values()):raise ValueError('字段映射无效')
  if len(set(mapping.values()))!=len(mapping):raise ValueError('同一源列不能重复映射')
  required={'posting_date','voucher_no','account_code'}
  if not o['generate_line_numbers']:required.add('line_no')
  if o['amount_mode']=='split':required|={'debit','credit'}
  elif o['amount_mode'] in ('signed_by_direction','absolute_by_direction'):required|={'amount','direction'}
  else:raise ValueError('未知金额结构')
  if required-set(mapping):raise ValueError('缺少映射：'+','.join(sorted(required-set(mapping))))
  o['mapping']=mapping
  from erp_accounts import catalog
  approved_accounts=catalog();catalog_digest=sha(dump(approved_accounts).encode())
  if o['data_kind'] not in ('uploaded','simulated'):raise ValueError('未知数据类型')
  if any(x not in approved_accounts for x in o['account_map'].values()):raise ValueError('科目映射目标未核准')
  if '__data_kind' in v['columns']:o['data_kind']='simulated'
  records=[];previous={};counts=defaultdict(int);blocked=False
  for source in v['source_rows']:
   raw=source['values'];f={k:norm(raw.get(c,'')) for k,c in mapping.items()}
   r=dict(row_number=source['row_number'],raw=raw,source_cell_types=source['cell_types'],normalized=None,status='pending',errors=[],changes=[],warnings=[],group_hint=[f.get('voucher_type',''),f.get('voucher_no','')]);records.append(r)
   if not any(norm(x) for x in raw.values()):r['status']='excluded_blank';continue
   markers=('合计','本月合计','本年累计','小计','Total','Grand Total')
   if any(f.get(k) in markers for k in ('posting_date','voucher_no','account_code')) and not f.get('line_no') and f.get('account_code','') in ('',*markers):r['status']='excluded_summary';previous={};continue
   try:
    for key in ('account_code','voucher_no'):
     if source['cell_types'].get(mapping.get(key,''))=='n':r['warnings'].append('源'+key+'为Excel数值单元格；不会猜测或补回可能丢失的前导零')
    if any(source['cell_types'].get(c) in ('f','e') for c in mapping.values()):raise ValueError('禁止公式或错误单元格')
    if '__data_kind' in raw and norm(raw['__data_kind'])!='simulated':raise ValueError('模拟模板标记无效')
    if o['fill_down_headers']:
     for k in ('voucher_no','voucher_type','posting_date'):
      if not f.get(k) and previous and (f.get('line_no') not in ('1','1.0') or k=='posting_date' and f.get('voucher_no')==previous.get('voucher_no')):
       f[k]=previous.get(k,'');r['changes'].append(dict(field=k,rule='explicit_fill_down',after=f[k]))
    previous=f.copy();r['group_hint']=[f.get('voucher_type',''),f.get('voucher_no','')]
    if not f.get('voucher_no'):blocked=True;raise ValueError('缺失凭证号，无法可靠分组')
    when=day(f.get('posting_date',''));account=o['account_map'].get(f['account_code'],f['account_code'])
    if account not in approved_accounts:raise ValueError('未知科目，须核准目录或明确映射：'+f['account_code'])
    currency=f.get('currency') or o['default_currency'] or ''
    currency=o['currency_map'].get(currency,{'人民币':'CNY','RMB':'CNY','美元':'USD','欧元':'EUR','日元':'JPY'}.get(currency,currency)).upper()
    if not re.fullmatch('[A-Z]{3}',currency):raise ValueError('缺失或无效币种，须明确映射或默认值')
    monetary=('debit','credit') if o['amount_mode']=='split' else ('amount',)
    if any(source['cell_types'].get(mapping.get(k,''))=='database_float' for k in monetary):raise ValueError('数据库浮点金额不可精确导入，请使用DECIMAL/NUMERIC或文本导出')
    if o['amount_mode']=='split':debit,credit=amount(f.get('debit'),currency),amount(f.get('credit'),currency)
    else:
     value=amount(f['amount'],currency);direction=f['direction'].upper()
     if direction not in ('借','借方','D','DEBIT','S','贷','贷方','C','CREDIT','H'):raise ValueError('未知借贷方向')
     if o['amount_mode']=='absolute_by_direction':value=abs(value)
     debit,credit=(value,Decimal(0)) if direction in ('借','借方','D','DEBIT','S') else (Decimal(0),value)
    if bool(debit)==bool(credit):raise ValueError('每行须且仅须借贷一方非零')
    if debit<0:credit,debit=-debit,Decimal(0)
    elif credit<0:debit,credit=-credit,Decimal(0)
    voucher=when[:7]+'|'+quote(f.get('voucher_type',''),safe='')+'|'+quote(f['voucher_no'],safe='')
    if len(voucher)>100:raise ValueError('规范凭证号超过100字符')
    key=(when,voucher,currency);counts[key]+=1
    number=f.get('line_no') or (str(counts[key]) if o['generate_line_numbers'] else '')
    line=Decimal(number)
    if line!=line.to_integral_value() or not 1<=line<=1000000:raise ValueError('分录行号须为正整数')
    row=dict(posting_date=when,voucher_no=voucher,line_no=str(int(line)),account_code=account,department_code=f.get('department_code') or o['default_department'],currency=currency,debit=format(debit,'.2f'),credit=format(credit,'.2f'),ledger_id=v['ledger_id'],erp_profile=v['profile'],source_voucher_no=f['voucher_no'],source_voucher_type=f.get('voucher_type',''),source_account_code=f['account_code'],source_row_number=source['row_number'],source_file_sha256=v['file_sha256'],cleaning_version=VERSION)
    for field in core.FIELDS:
     before=raw.get(mapping.get(field,''),'')
     if norm(before)!=row[field]:r['changes'].append(dict(field=field,before=before,after=row[field],rule='normalize_or_explicit_map'))
    r.update(normalized=row,status='valid')
   except (ValueError,InvalidOperation,TypeError) as ex:
    r.update(status='quarantined');r['errors'].append(dict(code='row_invalid',message=str(ex)))
    if not r['group_hint'][1]:blocked=True
  bad={tuple(r['group_hint']) for r in records if r['status']=='quarantined' and r['group_hint'][1]}
  groups=defaultdict(list)
  for r in records:
   if r['status']=='valid':
    if tuple(r['group_hint']) in bad:r.update(status='quarantined');r['errors'].append(dict(code='voucher_invalid',message='同凭证存在异常明细，整张隔离'))
    else:
     n=r['normalized'];groups[(n['posting_date'],n['voucher_no'],n['currency'])].append(r)
  for group in groups.values():
   numbers=[r['normalized']['line_no'] for r in group]
   balance=sum((Decimal(r['normalized']['debit'])-Decimal(r['normalized']['credit']) for r in group),Decimal(0))
   if balance or len(numbers)!=len(set(numbers)):
    for r in group:r.update(status='quarantined');r['errors'].append(dict(code='balance_or_duplicate',message='借贷不平衡或行号重复，整张隔离'))
  totals=defaultdict(lambda:{'debit':Decimal(0),'credit':Decimal(0)})
  for r in records:
   if r['status']=='valid':
    n=r['normalized'];totals[n['currency']]['debit']+=Decimal(n['debit']);totals[n['currency']]['credit']+=Decimal(n['credit'])
  quality=dict(source_rows=len(records),valid_rows=sum(r['status']=='valid' for r in records),quarantined_rows=sum(r['status']=='quarantined' for r in records),excluded_rows=sum(r['status'].startswith('excluded') for r in records),changed_rows=sum(bool(r['changes']) for r in records),commit_blocked=blocked,totals={c:{k:format(x,'.2f') for k,x in t.items()} for c,t in totals.items()},data_kind=o['data_kind'],metric_version='1.0')
  token=sha(dump(dict(file=v['file_sha256'],ledger=v['ledger_id'],profile=v['profile'],options=o,version=VERSION,account_catalog=catalog_digest)).encode())
  v.update(status='cleaned',options=o,cleaned_rows=records,quality=quality,cleaning_token=token,account_catalog_sha256=catalog_digest,cleaned_at=core.now());save(v)
  return public(v)

def commit(identifier,body):
 with LOCK:
  v=get(identifier)
  if v.get('cleaning_token')!=body.cleaning_token:raise HTTPException(409,'清洗版本已变化，请重新核对')
  if v['status']=='committed':return public(v)
  from erp_accounts import catalog
  approved_accounts=catalog()
  if v.get('account_catalog_sha256')!=sha(dump(approved_accounts).encode()):raise HTTPException(409,'核准科目目录已变化，请重新清洗')
  if v['status']!='cleaned' or v['quality']['commit_blocked'] or not v['quality']['valid_rows']:raise HTTPException(422,'没有合格凭证或凭证身份不明，请修正源文件')
  if v['quality']['quarantined_rows'] and not body.acknowledge_quarantine:raise HTTPException(409,'须确认仅入库合格凭证，异常凭证保留隔离')
  database=db();digest=sha(('erp-v1|'+v['ledger_id']+'|'+v['file_sha256']).encode())
  normalized=[r['normalized'] for r in v['cleaned_rows'] if r['status']=='valid']
  source_system='erp-'+sha(v['ledger_id'].encode())[:24]
  # Missing voucher categories must not create a second identity for an existing voucher.
  with database.connect() as c:existing=[json.loads(x) for x in c.execute(select(core.facts.c.payload).where(core.facts.c.business_key.like('["'+source_system+'",%'))).scalars()]
  identities=defaultdict(set)
  for row in existing+normalized:
   if row.get('ledger_id')==v['ledger_id']:
    key=(row['posting_date'][:7],row['source_voucher_no']);identities[key].add(row.get('source_voucher_type',''))
  if any('' in types and len(types)>1 for types in identities.values()):raise HTTPException(409,'同月份凭证号存在缺失/已知类别混用，请统一凭证字映射，避免重复计数')
  try:
   with database.begin() as c:
    active=c.execute(select(LEDGER.c.name).where(LEDGER.c.id=='active')).scalar()
    if active and active!=v['ledger_id']:raise HTTPException(409,'当前组织已绑定其他账套，请另建组织以免指标混算')
    if not active:c.execute(LEDGER.insert().values(id='active',name=v['ledger_id']))
    receipt=c.execute(select(RECEIPTS).where(RECEIPTS.c.id==digest)).mappings().first()
    if receipt and receipt['configuration']!=v['cleaning_token']:raise HTTPException(409,'同一文件已按其他清洗配置提交，不允许静默重复入库')
    if not receipt:c.execute(RECEIPTS.insert().values(id=digest,configuration=v['cleaning_token']))
   batch=core.ingest(database,normalized,digest,v['source_name'],source_system,kind=v['quality']['data_kind'],account_catalog=approved_accounts)
   for error in batch['errors']:
    original=normalized[error['row_number']-2]['source_row_number']
    row=next(r for r in v['cleaned_rows'] if r['row_number']==original)
    row.update(status='quarantined_at_commit');row['errors'].append(dict(code='core_rejected',message=error['message']))
   v.update(status='committed',batch=batch,source_system=source_system,committed_at=core.now());save(v)
   with database.begin() as c:c.execute(RECEIPTS.update().where(RECEIPTS.c.id==digest).values(batch_id=batch['batch_id']))
   return public(v)
  except IntegrityError:raise HTTPException(409,'并发提交，请重试获取已存在批次；不会重复计入') from None

def install(app):
 @app.get('/api/v1/erp/profiles')
 def profiles():
  from erp_accounts import catalog
  return dict(profiles=[dict(id=k,name=v[0],columns=v[1],scope='常见导出字段预设，非全版本认证') for k,v in PROFILES.items()],fields=list(ALIASES),accounts=catalog(),cleaning_version=VERSION)
 @app.get('/api/v1/erp/templates/{profile}')
 def template(profile:str):
  if profile not in PROFILES:raise HTTPException(404,'模板不存在')
  columns=PROFILES[profile][1];mapping,_=suggest(columns);out=io.StringIO();writer=csv.DictWriter(out,fieldnames=columns+['__data_kind']);writer.writeheader()
  for line,account,debit,credit in [('1','1002','100.00','0.00'),('2','6001','0.00','100.00')]:
   fields=dict(posting_date='2026-01-31',voucher_type='记',voucher_no='001',line_no=line,account_code=account,department_code='D01',currency='CNY',debit=debit,credit=credit)
   writer.writerow({column:fields.get(field,'') for field,column in mapping.items()}|{'__data_kind':'simulated'})
  return Response(out.getvalue().encode('utf-8-sig'),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{profile}-simulated.csv"'})
 @app.post('/api/v1/erp/preview',status_code=201)
 async def upload(file:UploadFile,profile:str=Form('generic'),ledger_id:str=Form(...),sheet:str|None=Form(None),header_row:int|None=Form(None)):
  content=await file.read(10*1024*1024+1);name=(file.filename or '')[:200]
  try:columns,records,info=parse(content,name,sheet,header_row)
  except (csv.Error,zipfile.BadZipFile,ET.ParseError,KeyError):raise ValueError('文件结构损坏，无法安全解析') from None
  return preview(content,name,profile,ledger_id,columns,records,info)
 @app.get('/api/v1/erp/runs')
 def listing():
  with db().connect() as c:values=[json.loads(x) for x in c.execute(select(RUNS.c.payload)).scalars()]
  return [{k:v.get(k) for k in ('id','source_name','profile','ledger_id','status','quality','batch','created_at')} for v in values[-100:][::-1]]
 @app.get('/api/v1/erp/runs/{identifier}')
 def detail(identifier:str):return public(get(identifier))
 @app.post('/api/v1/erp/runs/{identifier}/clean')
 def cleaning(identifier:str,body:Options):return clean(identifier,body)
 @app.post('/api/v1/erp/runs/{identifier}/commit')
 def confirm(identifier:str,body:Confirmation):return commit(identifier,body)
 @app.get('/api/v1/erp/runs/{identifier}/rows')
 def rows(identifier:str,status:str|None=None,offset:int=0,limit:int=50):
  if not 0<=offset<=MAX_ROWS or not 1<=limit<=200:raise ValueError('分页范围无效')
  v=get(identifier);records=v.get('cleaned_rows',v['source_rows'])
  if status:records=[r for r in records if r.get('status')==status]
  return dict(total=len(records),rows=records[offset:offset+limit])
 @app.get('/api/v1/erp/runs/{identifier}/errors.csv')
 def errors(identifier:str):
  value=get(identifier);out=io.StringIO();writer=csv.writer(out);writer.writerow(['source_row','status','errors','raw_record'])
  for r in value.get('cleaned_rows',[]):
   if r['errors']:writer.writerow([r['row_number'],r['status'],dump(r['errors']),dump(r['raw'])])
  return Response(out.getvalue().encode('utf-8-sig'),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="erp-quarantine-review.csv"'})

# Resolve host only after definitions, so direct module tests do not form a cycle.
import app as core
