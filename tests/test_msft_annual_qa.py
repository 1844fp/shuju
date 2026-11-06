"""Independent table-context audit of saved issuer reports, without network calls."""
import unittest,json,hashlib,re
from pathlib import Path
from decimal import Decimal
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'work/public-company/msft-2016-2025'
class Tables(HTMLParser):
 def __init__(self):super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None
 def handle_starttag(self,t,a):
  if t=='table':self.table=[]
  elif t=='tr':self.row=[]
  elif t in ('td','th'):self.cell=[]
 def handle_data(self,d):
  if self.cell is not None:self.cell.append(d)
 def handle_endtag(self,t):
  if t in ('td','th') and self.cell is not None:
   if self.row is not None:self.row.append(' '.join(''.join(self.cell).split()))
   self.cell=None
  elif t=='tr' and self.row is not None:
   if self.table is not None:self.table.append(self.row)
   self.row=None
  elif t=='table' and self.table is not None:self.tables.append(self.table);self.table=None

def number(row):
 values=[]
 for cell in row[1:]:
  text=cell.replace('$','').replace(',','').strip()
  if text and re.fullmatch(r'\(?-?\d+\)?',text):values.append(Decimal(text.replace('(','-').replace(')','')))
 return values

def audit():
 facts=json.loads((BASE/'facts.json').read_text());manifest=json.loads((BASE/'manifest.json').read_text());checks=[];warnings=[]
 for source in manifest:
  year=source['fiscal_year'];raw=(BASE/source['local_file']).read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest==source['source_sha256']
  parser=Tables();parser.feed(raw.decode('utf-8-sig'));annual=[f for f in facts if f['fiscal_year']==year];assert len(annual)==10
  for f in annual:
   assert f['source_sha256']==digest and f['unit']=='million' and f['currency']=='USD' and f['fiscal_year_end']==f'{year}-06-30'
   assert Decimal(f['amount_usd'])==Decimal(f['reported_value'])*1000000
   matches=[]
   for index,table in enumerate(parser.tables):
    text=' '.join(' '.join(r) for r in table)
    signatures={'income':('Total cost of revenue','Earnings per share'),'balance':('Total liabilities','Total assets'),'cashflow':('Net cash from operations','Cash and cash equivalents')}
    if not all(s.lower() in text.lower() for s in signatures[f['statement']]):continue
    if 'million' not in text.lower() or str(year) not in ' '.join(' '.join(r) for r in table[:6]):continue
    for row in table:
     if row and row[0]==f['source_row'][0] and number(row):matches.append((index,number(row)[0]))
   ok=bool(matches) and all(v==Decimal(f['reported_value']) for _,v in matches)
   checks.append({'year':year,'metric':f['metric'],'passed':ok,'statement_table_candidates':[i for i,_ in matches],'reported_value':f['reported_value']})
   if f['candidate_count']>1:warnings.append({'year':year,'metric':f['metric'],'global_candidates':f['candidate_count'],'note':'collector chooses first globally; authoritative statement context checked separately'})
  values={f['metric']:Decimal(f['reported_value']) for f in annual};assert values['total_assets']==values['total_liabilities']+values['equity']
 return {'facts_checked':len(checks),'checks':checks,'warnings':warnings,'all_passed':all(x['passed'] for x in checks),'scope':'original-year disclosure; not restated comparable series; not vouchers'}
@unittest.skipUnless((BASE/'facts.json').is_file() and (BASE/'manifest.json').is_file(), 'Public annual corpus absent; run python data_platform/msft_annual.py')
class MSFTAnnualQA(unittest.TestCase):
 def test_all_sha_units_years_and_statement_values(self):
  result=audit();out=ROOT/'work/public-company/qa-review.json';out.write_text(json.dumps(result,indent=2),encoding='utf-8');self.assertTrue(result['all_passed'],str([x for x in result['checks'] if not x['passed']]))
if __name__=='__main__':unittest.main(verbosity=2)
