"""Download original-year Microsoft annual reports; no restatement stitching."""
import sys,json,re,hashlib,time
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from infrastructure.public_corpus import Rows
OUT=ROOT/'work/public-company/msft-2016-2025'
METRICS={'income':{'revenue':['Total revenue'],'cost_of_revenue':['Total cost of revenue'],'operating_income':['Operating income'],'net_income':['Net income']},'balance':{'total_assets':['Total assets'],'total_liabilities':['Total liabilities'],'equity':["Total stockholders’ equity","Total stockholders' equity","Total shareholders’ equity","Total shareholders\' equity"]},'cashflow':{'operating_cashflow':['Net cash from operations'],'investing_cashflow':['Net cash used in investing','Net cash used in investing activities'],'financing_cashflow':['Net cash used in financing','Net cash used in financing activities','Net cash from (used in) financing']}}
def numbers(row):
 values=[]
 for c in row[1:]:
  s=c.replace('$','').replace(',','').replace('\xa0','').strip()
  if not s:continue
  if not re.fullmatch(r'\(?-?\d+\)?',s):return []
  values.append(Decimal(s.replace('(','-').replace(')','')))
 return values

class LocatedRows(Rows):
 def __init__(self):
  super().__init__();self.tables=[];self.active=[];self.locations=[]
 def handle_starttag(self,tag,attrs):
  if tag=='table':
   self.tables.append({'table_index':len(self.tables),'attributes':dict(attrs),'rows':[]});self.active.append(len(self.tables)-1)
  super().handle_starttag(tag,attrs)
 def handle_endtag(self,tag):
  before=len(self.rows);super().handle_endtag(tag)
  if tag=='tr' and len(self.rows)>before:
   table=self.active[-1] if self.active else None
   self.locations.append(table)
   if table is not None:self.tables[table]['rows'].append(self.rows[-1])
  if tag=='table' and self.active:self.active.pop()

def main():
 offline='--offline' in sys.argv
 OUT.mkdir(parents=True,exist_ok=True);manifest=[];facts=[]
 previous=json.loads((OUT/'manifest.json').read_text()) if offline else []
 previous_hash={r['fiscal_year']:r.get('source_sha256') for r in previous}
 old_facts=json.loads((OUT/'facts.json').read_text()) if offline else None
 for year in range(2016,2026):
  url=f'https://www.microsoft.com/investor/reports/ar{year%100:02d}/index.html';path=OUT/f'ar{year}.html'
  try:
   if offline and not path.exists():raise ValueError('offline source missing')
   if not path.exists():
    with urlopen(Request(url,headers={'User-Agent':'FinAgent-public-research/1.0'}),timeout=60) as response:
     if not response.url.lower().startswith('https://www.microsoft.com/'):raise ValueError('unexpected redirect')
     raw=response.read(20_000_001)
     if len(raw)>20_000_000:raise ValueError('oversized')
     path.write_bytes(raw)
    (OUT/f'ar{year}.retrieved.txt').write_text(datetime.now(timezone.utc).isoformat())
   raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest();parser=LocatedRows();parser.feed(raw.decode('utf-8-sig'))
   if offline and previous_hash.get(year)!=sha:raise ValueError('offline SHA256 mismatch')
   source={'fiscal_year':year,'source_url':url,'source_sha256':sha,'retrieved_at':(OUT/f'ar{year}.retrieved.txt').read_text(),'local_file':path.name,'disclosure_version':f'FY{year}-original-annual-report','currency':'USD','unit':'million','fiscal_year_end':f'{year}-06-30'}
   manifest.append(source)
   for statement,metrics in METRICS.items():
    for metric,labels in metrics.items():
     candidates=[]
     for idx,row in enumerate(parser.rows):
      if not row or row[0] not in labels or len(numbers(row))<(2 if statement=='balance' else 3):continue
      ti=parser.locations[idx];table=parser.tables[ti] if ti is not None else {'rows':[]}
      headers=[r for r in table['rows'] if any(str(year)==c.strip() for c in r)]
      units=[r for r in table['rows'] if any('in millions' in c.lower() for c in r)]
      valid=any([c.strip() for c in h if re.fullmatch(r'20\d{2}',c.strip())][:1]==[str(year)] for h in headers) and bool(units)
      candidates.append({'row_index':idx,'table_index':ti,'table_attributes':table.get('attributes',{}),'row':row,'year_headers':headers,'unit_rows':units,'current_year_value':str(numbers(row)[0]),'validated':valid})
     valid=[c for c in candidates if c['validated']]
     distinct={c['current_year_value'] for c in valid}
     common={**source,'company':'Microsoft','ticker':'MSFT','statement':statement,'metric':metric,'candidates':candidates,'candidate_count':len(candidates),'data_kind':'public_disclosure','comparability_warning':'Original-year disclosures may use different accounting policies; revenue recognition adoption and restatements require separate review. Not a constant-accounting-basis time series.'}
     if len(distinct)==1:
      chosen=valid[0];v=Decimal(chosen['current_year_value'])
      facts.append({**common,'reported_value':str(v),'amount_usd':format(v*Decimal(1000000),'.2f'),'source_row':chosen['row'],'source_table_index':chosen['table_index'],'selection_rule':'all validated current-year candidates agree; first locator retained','status':'extracted','basis':'current-year column in original-year report; not vouchers'})
     else:facts.append({**common,'reported_value':None,'status':'quarantined' if len(distinct)>1 else 'missing','reason':'conflicting validated candidates' if len(distinct)>1 else 'year/unit header validation failed'})
   print(year,'downloaded',len(raw),'bytes',flush=True)
  except Exception as e:
   manifest.append({'fiscal_year':year,'source_url':url,'status':'failed','error':type(e).__name__+': '+str(e)});print(year,'FAILED',str(e),flush=True)
  if not offline:
   (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8');(OUT/'facts.json').write_text(json.dumps(facts,indent=2),encoding='utf8')
 checks=[]
 for year in range(2016,2026):
  by={f['metric']:Decimal(f['reported_value']) for f in facts if f['fiscal_year']==year and f['status']=='extracted'}
  checks.append({'fiscal_year':year,'extracted':len(by),'balance_identity':(by['total_assets']==by['total_liabilities']+by['equity']) if {'total_assets','total_liabilities','equity'}<=by.keys() else None})
 if offline:
  assert len(facts)==100 and len(manifest)==10,'incomplete offline corpus'
  assert all(f['status']=='extracted' for f in facts),'unresolved facts'
  assert [(f['fiscal_year'],f['metric'],f['reported_value']) for f in facts]==[(f['fiscal_year'],f['metric'],f['reported_value']) for f in old_facts],'stored fact mismatch'
  print('PASS offline SHA256, headers, units, candidate agreement, 100 stored values')
 (OUT/'validation.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks))
if __name__=='__main__':main()

