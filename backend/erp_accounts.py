"""Organization-approved accounts. Journal rows never supply their own classification."""
import csv,io
from typing import Literal
from fastapi import UploadFile,Form,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import MetaData,Table,Column,String,select
import erp_imports as etl

META=MetaData();ACCOUNTS=Table('metadata_erp_account',META,Column('code',String,primary_key=True),Column('name',String),Column('category',String))
CATEGORIES={'asset':'资产','liability':'负债','equity':'权益','revenue':'收入','cost':'成本','expense':'费用','other':'其他'}
NAMES={'1002':'银行存款','1122':'应收账款','1405':'库存商品','1601':'固定资产','2001':'短期借款','2202':'应付账款','4001':'实收资本','4103':'本年利润','6001':'主营业务收入','6051':'其他业务收入','6401':'主营业务成本','6601':'销售费用','6602':'管理费用','6603':'财务费用','6111':'投资收益','6301':'营业外收入','6711':'营业外支出','6801':'所得税费用'}
class Account(BaseModel):
 model_config=ConfigDict(extra='forbid')
 code:str=Field(pattern=r'^[A-Za-z0-9_.-]{1,50}$')
 name:str=Field(min_length=1,max_length=120)
 category:Literal['asset','liability','equity','revenue','cost','expense','other']
class Approval(BaseModel):
 model_config=ConfigDict(extra='forbid')
 accounts:list[Account]=Field(min_length=1,max_length=10000)
 approved:bool=False

def listing():
 database=etl.core.current_db();META.create_all(database)
 result={k:dict(code=k,name=NAMES.get(k,k),category=v,builtin=True) for k,v in etl.core.ACCOUNTS.items()}
 with database.connect() as c:
  for row in c.execute(select(ACCOUNTS)).mappings():result[row['code']]={**dict(row),'builtin':False}
 return sorted(result.values(),key=lambda x:x['code'])
def catalog():return {r['code']:r['category'] for r in listing()}
def approve(body,source_digest=None):
 if not body.approved:raise HTTPException(422,'请明确核准科目类别；不根据编码推测')
 records=[a.model_dump() for a in body.accounts]
 if len({r['code'] for r in records})!=len(records):raise ValueError('科目代码重复')
 current={r['code']:r for r in listing()}
 for row in records:
  if row['code'] in current and current[row['code']]['category']!=row['category']:raise HTTPException(409,'已核准科目类别不能静默修改，请单独审核历史重分类')
 database=etl.core.current_db()
 with database.begin() as c:
  for row in records:
   if row['code'] in etl.core.ACCOUNTS:continue
   if row['code'] in current:c.execute(ACCOUNTS.update().where(ACCOUNTS.c.code==row['code']).values(name=row['name']))
   else:c.execute(ACCOUNTS.insert().values(**row))
  c.execute(etl.core.audit.insert().values(id=etl.core.uid(),action='erp_account_approval',resource=source_digest or etl.sha(etl.dump(records).encode()),created=etl.core.now()))
 return dict(accounts=listing(),catalog_sha256=etl.sha(etl.dump(catalog()).encode()),approved_rows=len(records),source_sha256=source_digest)

def install(app):
 @app.get('/api/v1/erp/accounts/template')
 def template():
  output=io.StringIO();writer=csv.writer(output);writer.writerow(['科目代码','科目名称','科目类别'])
  for code,category in etl.core.ACCOUNTS.items():writer.writerow([code,NAMES.get(code,code),CATEGORIES[category]])
  return Response(output.getvalue().encode('utf-8-sig'),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="account-catalog-template.csv"'})
 @app.get('/api/v1/erp/accounts')
 def read():return dict(accounts=listing(),categories=CATEGORIES,catalog_sha256=etl.sha(etl.dump(catalog()).encode()))
 @app.post('/api/v1/erp/accounts')
 def create(body:Approval):return approve(body)
 @app.post('/api/v1/erp/accounts/import')
 async def upload(file:UploadFile,approved:bool=Form(False),header_row:int=Form(1),sheet:str|None=Form(None)):
  content=await file.read(10*1024*1024+1);name=(file.filename or '')[:200];columns,rows,info=etl.parse(content,name,sheet,header_row)
  digest=etl.sha(content)
  with etl.db().begin() as c:
   if not c.execute(select(etl.FILES.c.id).where(etl.FILES.c.digest==digest)).first():c.execute(etl.FILES.insert().values(id=etl.core.uid(),digest=digest,content=content,metadata=etl.dump(dict(name=name,kind='chart_of_accounts',parser=info))))
  aliases={'code':['account_code','code','科目代码','科目编码','ccode','FAccountNumber','GLAccount'],'name':['name','科目名称','AccountName','ccode_name','FAccountName'],'category':['category','科目类别','类别','AccountType']};mapping={}
  for key,options in aliases.items():
   matches=[c for c in columns if etl.hk(c) in {etl.hk(a) for a in options}]
   if len(matches)!=1:raise ValueError('科目表须含唯一的代码、名称和明确类别列')
   mapping[key]=matches[0]
  result=[]
  for row in rows:
   if not any(etl.norm(v) for v in row['values'].values()):continue
   if any(row['cell_types'].get(c) in ('f','e') for c in mapping.values()):raise ValueError('科目表禁止公式或错误单元格')
   item={k:etl.norm(row['values'][c]) for k,c in mapping.items()}
   item['category']={v:k for k,v in CATEGORIES.items()}.get(item['category'],item['category'])
   try:result.append(Account(**item))
   except ValueError:raise ValueError('科目表第'+str(row['row_number'])+'行类别或代码无效；损益须明确拆为收入/费用等，不自动猜测') from None
  return approve(Approval(accounts=result,approved=approved),digest)
