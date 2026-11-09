import hashlib,json,re,sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,urlopen
import pymupdf
from a_share_annual import ROOT,COMPANIES

API='https://www.cninfo.com.cn/new/hisAnnouncement/query'
HOST='static.cninfo.com.cn'
LEGAL={'000028':'国药集团一致药业股份有限公司','002340':'格林美股份有限公司','300146':'汤臣倍健股份有限公司'}
TITLES={'balance':'合并资产负债表','income':'合并利润表','cashflow':'合并现金流量表'}

def request(url,data=None):
    req=Request(url,data=data,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.cninfo.com.cn/'})
    with urlopen(req,timeout=60) as response:
        if urlsplit(response.url).hostname!=urlsplit(url).hostname:
            raise ValueError('Unexpected redirect host')
        raw=response.read(50_000_001)
        if len(raw)>50_000_000:raise ValueError('Source size limit exceeded')
        return raw

def discover(code):
    query=dict(stock='',searchkey=COMPANIES[code],column='szse',category='category_ndbg_szsh;',seDate='2022-01-01~2026-12-31',pageNum=1,pageSize=30,tabName='fulltext')
    index=ROOT/'official-index.json'
    response={'announcements':json.loads(index.read_text(encoding='utf-8-sig'))} if index.exists() else json.loads(request(API,urlencode(query).encode()))
    found={}
    for row in response.get('announcements') or []:
        match=re.fullmatch(r'(20\d{2})年年度报告',row['announcementTitle'])
        if row['secCode']!=code or not match:continue
        year=int(match[1]);path=row['adjunctUrl']
        if not re.fullmatch(r'finalpage/\d{4}-\d{2}-\d{2}/\d+\.pdf',path,re.I):raise ValueError(path)
        if year in found and found[year]!=path:raise ValueError(f'Ambiguous report {code}/{year}')
        found[year]=path
    return [(code,year,'https://'+HOST+'/'+found[year]) for year in range(2021,2026)]

def validate(raw,code,year):
    with pymupdf.open(stream=raw,filetype='pdf') as pdf:
        pages=[page.get_text(sort=True) for page in pdf]
    cover=re.sub(r'\s+','',''.join(pages[:20]));assert LEGAL[code] in cover and (f'{year}年年度报告' in cover or (code=='300146' and year==2022 and f'{year}年' in cover)),(code,year,cover[:150])
    assert len(pages)>60,(code,year,len(pages))
    located={}
    for kind,title in TITLES.items():
        candidates=[i for i,p in enumerate(pages) if title in re.sub(r'\s+','',p) and re.search(r'\d{1,3}(?:,\d{3})+\.\d{2}',p) and i>20]
        if not candidates:raise ValueError(f'Missing {kind} {code}/{year}')
        located[kind]=candidates[0]+1
    assert list(located.values())==sorted(located.values()),(code,year,located)
    return pages,located

def collect(job,known):
    code,year,url=job;key=f'{code}-{year}';path=ROOT/(key+'.pdf');old=known.get(key)
    cached=path.read_bytes() if path.exists() else None
    if old and old['url']==url and cached and hashlib.sha256(cached).hexdigest()==old['sha256']:
        raw=cached;retrieved=old.get('retrieved_at')
    else:raw=request(url);retrieved=datetime.now(timezone.utc).isoformat()
    pages,located=validate(raw,code,year)
    if raw!=cached:
        temporary=path.with_suffix('.pdf.part');temporary.write_bytes(raw);temporary.replace(path)
    out=ROOT/'statement-text';out.mkdir(exist_ok=True)
    for kind,page in located.items():
        text='\n'.join(f'\n[PDF page {i+1}]\n{pages[i]}' for i in range(page-1,min(page+2,len(pages))))
        (out/f'{key}-{kind}.txt').write_text(text,encoding='utf-8')
    return dict(key=key,ticker=code,company=COMPANIES[code],fiscal_year=year,url=url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),pdf_pages=len(pages),statement_pdf_pages=located,retrieved_at=retrieved,verified_at=datetime.now(timezone.utc).isoformat(),data_kind='public_disclosure')

def main():
    full=ROOT/'full-manifest.json';known={r['key']:r for p in [ROOT/'manifest.json',full] if p.exists() for r in json.loads(p.read_text(encoding='utf-8'))}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs=[job for group in pool.map(discover,COMPANIES) for job in group]
        rows=list(pool.map(lambda job:collect(job,known),jobs))
    assert len(rows)==15 and len({r['sha256'] for r in rows})==15
    full.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Verified 15 official PDFs and 45 statement text extracts')
if __name__=='__main__':main()




