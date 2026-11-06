"""Download an issuer's public annual statement; never manufacture journal entries."""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = 'https://www.microsoft.com/en-us/Investor/earnings/FY-2025-Q4/income-statements'
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/acceptance/public-msft'
METRICS = {
    'revenue': ('Total revenue', '营业收入'),
    'cost': ('Total cost of revenue', '营业成本'),
    'gross_profit': ('Gross margin', '毛利润金额'),
    'operating_profit': ('Operating income', '经营利润'),
    'net_income': ('Net income', '披露净利润'),
    'research': ('Research and development', '研发费用'),
    'selling': ('Sales and marketing', '销售营销费用'),
    'administration': ('General and administrative', '管理费用'),
    'other_income': ('Other income (expense), net', '其他收益费用净额'),
    'income_tax': ('Provision for income taxes', '所得税费用'),
}

class Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row=[]
        if tag in ('td','th') and self.row is not None: self.cell=[]
    def handle_data(self, value):
        if self.cell is not None: self.cell.append(value)
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row=None

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    request=Request(SOURCE,headers={'User-Agent':'FinAgent-public-data-validation/1.0'})
    with urlopen(request, timeout=30) as response:
        raw=response.read(3_000_001)
        if len(raw)>3_000_000: raise ValueError('source too large')
        if not response.url.startswith('https://www.microsoft.com/'): raise ValueError('unexpected source redirect')
    (OUT/'income-statements.html').write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest()
    parser=Rows(); parser.feed(raw.decode('utf-8-sig'))
    records=[]; documents=[]
    for key,(label,chinese) in METRICS.items():
        candidates=[r for r in parser.rows if any(c.strip()==label for c in r)]
        if len(candidates)!=1: raise ValueError(f'ambiguous statement row: {label}')
        row=candidates[0]; index=next(i for i,c in enumerate(row) if c.strip()==label)
        values=[c.replace('$','').replace(',','').strip() for c in row[index+1:] if c.strip()]
        if len(values)!=3: raise ValueError(f'expected three annual columns: {label}')
        for year,value in zip((2025,2024,2023),values):
            amount=Decimal(value.replace('(','-').replace(')',''))
            if amount!=amount.to_integral_value(): raise ValueError('expected reported million-dollar integer')
            record=dict(company='Microsoft',ticker='MSFT',fiscal_year=year,start_date=f'{year-1}-07-01',end_date=f'{year}-06-30',currency='USD',unit='million',metric=key,reported_value=str(amount),amount_usd=format(amount*Decimal(1000000),'.2f'),source_url=SOURCE,source_sha256=digest,source_row=label,data_kind='public_disclosure',basis='issuer annual income statement; not journal entries')
            records.append(record)
            text=f"微软 Microsoft MSFT，{year} 财年（{year-1}-07 至 {year}-06），{chinese} {label}：{amount} 百万美元 USD million。年度汇总，非单月，非凭证明细；净利润与经营利润为不同指标。"
            documents.append(dict(title=f'MSFT FY{year} {key}',version='FY25Q4-as-disclosed',effective_date='2025-07-30',locator=f'MSFT FY25Q4/{year}/{label}',text=text))
    # These two identities check extraction and units; they are not investment advice.
    by={(r['fiscal_year'],r['metric']):Decimal(r['reported_value']) for r in records}
    for year in (2025,2024,2023):
        if by[year,'revenue']-by[year,'cost']!=by[year,'gross_profit']:raise ValueError('gross profit reconciliation failed')
        if by[year,'gross_profit']-sum(by[year,k] for k in ('research','selling','administration'))!=by[year,'operating_profit']:raise ValueError('operating profit reconciliation failed')
        if by[year,'operating_profit']+by[year,'other_income']-by[year,'income_tax']!=by[year,'net_income']:raise ValueError('disclosed net income reconciliation failed')
    manifest=dict(source_url=SOURCE,retrieved_at=datetime.now(timezone.utc).isoformat(),source_sha256=digest,years=[2025,2024,2023],currency='USD',unit='million',record_count=len(records),documents=documents,records=records,scope='public financial statement facts only; never imported as genuine vouchers')
    (OUT/'corpus.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    result=prepare(); print(json.dumps({k:result[k] for k in ('source_url','source_sha256','record_count')},ensure_ascii=False))
