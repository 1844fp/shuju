"""Server-registered ERP read sources. Clients supply IDs, never DSNs or SQL."""
import base64,json,os,re,time
from datetime import datetime,date
from decimal import Decimal
from urllib.parse import urlparse,urljoin,urlencode,parse_qsl,urlunparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict
from sqlalchemy import create_engine,MetaData,Table,select,text,Float
from sqlalchemy.engine import make_url
import erp_imports as etl

class Pull(BaseModel):
 model_config=ConfigDict(extra='forbid')
 source_id:str
 profile:str='generic'
 ledger_id:str
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('ERP重定向被拒绝')

def registry():
 try:items=json.loads(os.getenv('FINAGENT_ERP_SOURCES_JSON','[]'))
 except ValueError:raise HTTPException(503,'ERP源注册配置无效') from None
 if not isinstance(items,list) or len(items)>100:raise HTTPException(503,'ERP源注册配置无效')
 return [v for v in items if isinstance(v,dict) and v.get('organization_id')==etl.core.request_organization.get()]
def configured(identifier):
 hits=[s for s in registry() if s.get('id')==identifier]
 if len(hits)!=1:raise HTTPException(404,'当前组织无此授权数据源')
 source=hits[0]
 if source.get('read_only_verified') is not True:raise HTTPException(503,'管理员尚未确认源账号只读权限')
 return source
def env_secret(name):
 if not re.fullmatch(r'FINAGENT_ERP_[A-Z0-9_]+',str(name)):raise ValueError('无效凭据变量名称')
 value=os.getenv(name)
 if not value:raise ValueError('源配置缺失')
 return value
def scalar(value):
 if value is None:return ''
 if isinstance(value,datetime):return value.date().isoformat()
 if isinstance(value,date):return value.isoformat()
 if isinstance(value,Decimal):return format(value,'f')
 return str(value)

def database_rows(source):
 dsn=env_secret(source.get('dsn_env'));url=make_url(dsn);dialect=url.get_backend_name()
 if dialect not in ('postgresql','mysql','mssql'):raise ValueError('只允许PostgreSQL/MySQL/SQL Server注册源')
 name=source.get('table','');schema=source.get('schema');columns=source.get('columns',[])
 if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}',name) or schema and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}',schema):raise ValueError('数据实体名称无效')
 if not isinstance(columns,list) or not 1<=len(columns)<=100 or len(columns)!=len(set(columns)):raise ValueError('须登记1至100个不同只读列')
 if any(not isinstance(c,str) or not re.fullmatch(r'[\w\u4e00-\u9fff]{1,100}',c) for c in columns):raise ValueError('列标识无效')
 args={'connect_timeout':5}
 if dialect=='postgresql':args['options']='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=3000'
 elif dialect=='mssql':args={'timeout':5,'readonly':True}
 engine=create_engine(url,connect_args=args,pool_pre_ping=False)
 try:
  with engine.connect() as connection:
   if dialect=='mysql':connection.execute(text('SET TRANSACTION READ ONLY'));connection.execute(text('SET SESSION MAX_EXECUTION_TIME=5000'))
   if dialect=='mssql':
    connection.connection.driver_connection.timeout=5
    connection.execute(text('SET LOCK_TIMEOUT 5000'))
   table=Table(name,MetaData(),schema=schema,autoload_with=connection)
   if any(c not in table.c for c in columns):raise ValueError('注册列在源实体中不存在')
   # SQLAlchemy builds the SELECT AST; no client SQL, expressions or filters are accepted.
   query=select(*(table.c[c] for c in columns)).limit(etl.MAX_ROWS+1)
   keys=source.get('order_by',[])
   if not isinstance(keys,list) or not keys or any(k not in columns for k in keys):raise ValueError('须登记确定性排序列')
   query=query.order_by(*(table.c[k] for k in keys))
   records=[];size=0
   for i,row in enumerate(connection.execution_options(stream_results=True).execute(query).mappings()):
    record=dict(row_number=i+1,values={c:scalar(row[c]) for c in columns},cell_types={c:'database_float' if isinstance(table.c[c].type,Float) else 'database_exact' for c in columns})
    size+=len(etl.dump(record).encode());records.append(record)
    if len(records)>etl.MAX_ROWS or size>10*1024*1024:raise ValueError('源数据超过10000行/10MB，不截断凭证')
   if not records:raise ValueError('源数据为空')
   return columns,records,dict(kind='database',dialect=dialect,source_id=source['id'],schema=schema,table=name,read_only=True,row_count=len(records))
 finally:engine.dispose()

def endpoint(value):
 u=urlparse(value)
 if u.username or u.password or u.fragment or u.scheme!='https' and not (u.scheme=='http' and u.hostname in ('127.0.0.1','localhost')):raise ValueError('ERP接口须HTTPS或本机测试地址')
 return u
def flatten(value,prefix=''):
 result={}
 for key,item in value.items():
  name=(prefix+'.' if prefix else '')+key
  if isinstance(item,dict):result.update(flatten(item,name))
  elif isinstance(item,list):raise ValueError('嵌套分录数组须通过ERP只读明细视图展开后接入')
  else:result[name]=item
 return result
def at(value,path):
 for key in path.split('.') if path else []:value=value[key]
 return value
def http_rows(source):
 base=source.get('url','');origin=endpoint(base);kind=source.get('kind','rest_json')
 headers={'Accept':'application/json'}
 if source.get('headers_env'):
  extra=json.loads(env_secret(source['headers_env']))
  if not isinstance(extra,dict) or set(k.lower() for k in extra)-{'authorization','cookie','x-api-key','accesstoken','appkey'}:raise ValueError('不支持的授权头')
  headers.update(extra)
 collected=[];pages=0;raw_size=0;raw_pages=[];next_url=base;seen=set();start=time.monotonic();body=None
 if dict(parse_qsl(origin.query)).get('offset','0')!='0':raise ValueError('快照必须从offset=0开始')
 if kind=='kingdee_bill_query':
  suffix='/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.ExecuteBillQuery.common.kdsvc'
  if not origin.path.endswith(suffix):raise ValueError('金蝶仅允许ExecuteBillQuery只读操作')
  query=source.get('query',{})
  if query.get('FormId')!='GL_VOUCHER' or set(query)-{'FormId','FieldKeys','FilterString','OrderString','StartRow','Limit','TopRow','SubSystemId'}:raise ValueError('只允许总账凭证明细查询配置')
  if not query.get('OrderString'):raise ValueError('须配置稳定排序')
  body=dict(query);body.update(StartRow=0,Limit=1000)
 elif kind not in ('rest_json','sap_odata','oracle_rest'):raise ValueError('未知HTTP源类型')
 while next_url:
  if time.monotonic()-start>15 or pages>=11 or next_url in seen and kind!='kingdee_bill_query':raise ValueError('ERP分页超时、循环或超过限额')
  if kind!='kingdee_bill_query':seen.add(next_url)
  u=endpoint(next_url)
  if (u.scheme,u.hostname,u.port)!=(origin.scheme,origin.hostname,origin.port) or u.path!=origin.path:raise ValueError('分页越过已登记接口边界')
  request_headers=headers.copy();payload=None
  if body is not None:
   mode=source.get('data_encoding','json_string')
   if mode not in ('json_string','object'):raise ValueError('未知金蝶data序列化模式')
   payload=json.dumps({'data':json.dumps(body) if mode=='json_string' else body}).encode();request_headers['Content-Type']='application/json'
  request=Request(next_url,data=payload,headers=request_headers)
  with build_opener(NoRedirect()).open(request,timeout=5) as response:
   raw=response.read(2_000_001)
   if len(raw)>2_000_000:raise ValueError('ERP单页响应超过2MB')
  raw_pages.append(base64.b64encode(raw).decode('ascii'))
  raw_size+=len(raw)
  if raw_size>10*1024*1024:raise ValueError('ERP快照超过10MB')
  # Financial JSON numbers are parsed as Decimal, never binary float.
  data=json.loads(raw,parse_float=Decimal);pages+=1
  rows=at(data,source.get('rows_path',{'sap_odata':'d.results','oracle_rest':'items'}.get(kind,'')))
  if not isinstance(rows,list):raise ValueError('未找到凭证明细数组')
  if kind=='kingdee_bill_query':
   columns=source.get('columns',[])
   if not columns or any(not isinstance(r,list) or len(r)!=len(columns) for r in rows):raise ValueError('金蝶列定义与查询返回不一致')
   rows=[dict(zip(columns,r)) for r in rows]
  if any(not isinstance(r,dict) for r in rows):raise ValueError('分录记录不是对象')
  collected.extend(flatten(row) for row in rows)
  if len(collected)>etl.MAX_ROWS:raise ValueError('超过10000行，不允许截断后入库')
  if kind=='sap_odata':next_url=data.get('d',{}).get('__next') or data.get('@odata.nextLink');next_url=urljoin(base,next_url) if next_url else None
  elif kind=='oracle_rest' and data.get('hasMore'):
   if not rows:raise ValueError('空分页仍声明hasMore')
   params=dict(parse_qsl(urlparse(next_url).query));params.update(offset=str(len(collected)),limit='1000');next_url=urlunparse(origin._replace(query=urlencode(params)))
  elif kind=='kingdee_bill_query' and len(rows)==body['Limit']:body['StartRow']=len(collected)
  else:
   if kind=='rest_json' and isinstance(data,dict) and any(data.get(k) for k in ('hasMore','next','nextLink','@odata.nextLink')):raise ValueError('通用JSON源未声明完整分页协议，拒绝部分导入')
   next_url=None
 if not collected:raise ValueError('ERP未返回数据')
 columns=list(dict.fromkeys(k for r in collected for k in r))
 if len(columns)>100:raise ValueError('ERP列数超过100')
 records=[dict(row_number=i+1,values={c:scalar(r.get(c)) for c in columns},cell_types={c:'api_decimal' for c in columns}) for i,r in enumerate(collected)]
 return columns,records,dict(kind=kind,source_id=source['id'],pages=pages,row_count=len(records),read_only=True,_raw_pages_base64=raw_pages)

def pull(body):
 source=configured(body.source_id)
 if source.get('ledger_id')!=body.ledger_id:raise HTTPException(409,'账套标识与管理员登记源不一致')
 try:
  columns,records,info=database_rows(source) if source.get('kind')=='database' else http_rows(source)
 except HTTPException:raise
 except Exception:raise HTTPException(503,'ERP读取失败：请管理员检查只读授权、注册字段、驱动、分页及网络；未写入源系统') from None
 raw_pages=info.pop('_raw_pages_base64',None)
 content=etl.dump(dict(source_id=source['id'],columns=columns,records=records,original_response_pages_base64=raw_pages)).encode()
 if len(content)>10*1024*1024:raise HTTPException(413,'包含原始响应的ERP快照超过10MB，请由管理员缩小只读视图或期间范围')
 return etl.preview(content,'registered-source:'+source['id'],body.profile,body.ledger_id,columns,records,info)
def install(app):
 @app.get('/api/v1/erp/sources')
 def listing():return [dict(id=s.get('id'),name=s.get('name',s.get('id')),kind=s.get('kind'),ledger_id=s.get('ledger_id'),read_only_verified=s.get('read_only_verified') is True) for s in registry()]
 @app.post('/api/v1/erp/source-preview',status_code=201)
 def preview(body:Pull):return pull(body)
