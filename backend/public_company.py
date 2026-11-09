"""Fixed-server public annual disclosure snapshots; never monthly ledger data."""
import hashlib,json
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException
from fastapi.responses import Response
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'work'/'public-company'/'msft-2016-2025'
VERSION='public-annual-1.0'
METRICS={'revenue':'income','cost_of_revenue':'income','operating_income':'income','net_income':'income','total_assets':'balance','total_liabilities':'balance','equity':'balance','operating_cashflow':'cashflow','investing_cashflow':'cashflow','financing_cashflow':'cashflow'}
WARNING='Original-year disclosures, not harmonized restatements; accounting policy, scope and presentation changes may affect comparability. No annual-to-month conversion.'
def load():
 try:
  raw=(ROOT/'facts.json').read_bytes();manifest_raw=(ROOT/'manifest.json').read_bytes();facts=json.loads(raw);manifest=json.loads(manifest_raw)
  sources={}
  for s in manifest:
   y=s['fiscal_year']
   if type(y)!=int or not 2016<=y<=2025 or s.get('local_file')!=f'ar{y}.html' or y in sources:raise ValueError('source')
   if hashlib.sha256((ROOT/f'ar{y}.html').read_bytes()).hexdigest()!=s['source_sha256']:raise ValueError('hash')
   sources[y]=s
  if set(sources)!=set(range(2016,2026)):raise ValueError('incomplete sources')
  seen=set()
  for f in facts:
   key=(f['fiscal_year'],f['metric'])
   if key in seen:raise ValueError('duplicate fact')
   seen.add(key);s=sources[f['fiscal_year']]
   if any(f.get(k)!=s.get(k) for k in ('source_sha256','source_url','local_file','disclosure_version','fiscal_year_end')) or f.get('data_kind')!='public_disclosure':raise ValueError('provenance')
   if f['metric'] not in METRICS or f.get('statement')!=METRICS[f['metric']] or f.get('status') not in ('extracted','missing'):raise ValueError('metric/status')
   if f['status']=='missing' and (not f.get('reason') or f.get('reported_value') is not None):raise ValueError('missing reason')
   if f['status']=='extracted':
    if not isinstance(f.get('amount_usd'),str) or not isinstance(f.get('reported_value'),str):raise ValueError('decimal strings required')
    n=Decimal(f['amount_usd'])
    if not n.is_finite() or n!=Decimal(f['reported_value'])*1000000 or f.get('currency')!='USD' or f.get('unit')!='million':raise ValueError('amount')
  return facts,sources,hashlib.sha256(raw+manifest_raw).hexdigest()
 except (OSError,KeyError,ValueError,InvalidOperation,TypeError):raise HTTPException(503,'public_disclosure_snapshot_invalid_or_unavailable') from None
def envelope(batch):return {'ticker':'MSFT','company':'Microsoft','currency':'USD','amount_unit':'USD','data_kind':'public_disclosure','batch_version':batch,'metric_version':VERSION,'comparability_warning':WARNING,'validation_scope':'local byte hashes, provenance links and numeric consistency only; not independent semantic verification of annual report facts'}
def annual(start,end):
 if not 2016<=start<=end<=2025:raise HTTPException(422,'年度须2016至2025')
 facts,sources,batch=load();out=[]
 for year in range(start,end+1):
  selected=[f for f in facts if f['fiscal_year']==year];v={f['metric']:Decimal(f['amount_usd']) for f in selected if f['status']=='extracted'};prior=next((Decimal(f['amount_usd']) for f in facts if f['fiscal_year']==year-1 and f['metric']=='revenue' and f['status']=='extracted'),None)
  def ratio(a,b):return {'value':str(a/b) if a is not None and b else None,'reason':None if a is not None and b else 'missing_input_or_zero_denominator'}
  out.append({'fiscal_year':year,'fiscal_year_end':sources[year]['fiscal_year_end'],'amounts':{k:str(n) for k,n in v.items()},'missing_metrics':{k:next((f.get('reason','not extracted') for f in selected if f['metric']==k and f['status']=='missing'),'fact not provided') for k in METRICS if k not in v},'ratios':{'revenue_growth':ratio(v.get('revenue')-prior if 'revenue' in v and prior is not None else None,prior),'net_margin':ratio(v.get('net_income'),v.get('revenue')),'operating_margin':ratio(v.get('operating_income'),v.get('revenue')),'debt_ratio':ratio(v.get('total_liabilities'),v.get('total_assets'))},'source':sources[year],'facts':selected})
 return {**envelope(batch),'years':out}
def backtest():
 a=annual(2016,2025);years=a['years'];pred=[]
 if any('revenue' not in y['amounts'] for y in years):raise HTTPException(422,'收入年度缺失')
 for i in range(3,len(years)):
  history=years[i-3:i];forecast=sum((Decimal(x['amounts']['revenue']) for x in history),Decimal(0))/3;naive=Decimal(history[-1]['amounts']['revenue']);actual=Decimal(years[i]['amounts']['revenue'])
  pred.append({'year':years[i]['fiscal_year'],'training_years':[x['fiscal_year'] for x in history],'actual':str(actual),'rolling3mean':str(forecast),'naive':str(naive),'rolling_error':str(abs(actual-forecast)),'naive_error':str(abs(actual-naive)),'sources':[x['source'] for x in history]+[years[i]['source']]})
 return {**{k:v for k,v in a.items() if k!='years'},'method':'annual rolling3yearmean vs previous-year naive; baseline, not trained model','predictions':pred,'rolling_mae':str(sum((Decimal(x['rolling_error']) for x in pred),Decimal(0))/len(pred)),'naive_mae':str(sum((Decimal(x['naive_error']) for x in pred),Decimal(0))/len(pred))}
def install(app):
 @app.get('/api/v1/public-company/a-share')
 def a_share(format: str = 'html'):
  from fastapi.responses import HTMLResponse
  from data_platform.a_share_annual import ROOT as corpus, render
  try:
   rows=json.loads((corpus/'facts.json').read_text(encoding='utf-8'))
  except (OSError, ValueError):
   raise HTTPException(503,'A 股公开财报测试集尚未准备') from None
  if format=='json':return {'data_kind':'public_disclosure','rows':rows}
  if format!='html':raise HTTPException(422,'format 仅支持 html 或 json')
  return HTMLResponse(render(rows))

 @app.get('/api/v1/public-company')
 def overview():
  f,s,b=load();return {**envelope(b),'fiscal_years':sorted(s),'fact_count':len(f),'sources':list(s.values())}
 @app.get('/api/v1/public-company/annual-metrics')
 def metrics(start_year:int=2016,end_year:int=2025):return annual(start_year,end_year)
 @app.get('/api/v1/public-company/backtest')
 def forecast():return backtest()
 @app.get('/api/v1/public-company/sources/{year}')
 def source(year:int):
  f,s,b=load()
  if year not in s:raise HTTPException(404,'年度不存在')
  return Response((ROOT/f'ar{year}.html').read_bytes(),media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="ar{year}.html"','X-Source-SHA256':s[year]['source_sha256'],'X-Batch-Version':b})

