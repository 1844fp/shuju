"""Extract bounded financial highlights from six reviewed CNINFO reports."""

from decimal import Decimal
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / 'work/public-company/a-share'
COMPANIES = {'000028': '国药一致', '002340': '格林美', '300146': '汤臣倍健'}
PAGES = {'000028-2022': 7, '000028-2025': 7, '002340-2023': 8,
         '002340-2025': 7, '300146-2023': 13, '300146-2025': 12}
METRICS = {'revenue': '营业收入', 'parent_net_income': '归母净利润',
           'operating_cashflow': '经营活动现金流量净额', 'assets': '总资产'}
MONEY = re.compile(r'-?\d{1,3}(?:,\d{3})+\.\d{2}')


def extract_metrics(page_text, report_year):
    page_text = re.sub(r'-?[\d,]+\.\d+\s*%', '', page_text)
    text = re.sub(r'\s+', '', page_text)
    text = text[text.index('主要会计数据和财务指标'):]
    header = text[:text.index('营业收入（元）')]
    years = [int(year) for year in re.findall(r'(20\d{2})年', header)]
    if years != [report_year, report_year - 1, report_year - 2] or '调整前' in header:
        raise ValueError('Unrecognized annual statement columns')
    revenue, rest = text.split('营业收入（元）', 1)[1].split('归属于上市公司股东', 1)
    profit, rest = rest.split('归属于上市公司股东', 1)
    cashflow = rest.split('经营活动产生的现金', 1)[1].split('基本每股收益', 1)[0]
    assets = re.split(r'(?:总资产|资产总额)（元）', rest, maxsplit=1)[1].split('归属于上市公司股东', 1)[0]
    columns = {}
    for metric, segment in zip(METRICS, (revenue, profit, cashflow, assets), strict=True):
        values = MONEY.findall(segment)
        if len(values) != 3:
            raise ValueError(f'Unexpected column count for {metric}')
        columns[metric] = [Decimal(value.replace(',', '')) for value in values]
    return {year: {metric: format(values[index], '.2f') for metric, values in columns.items()}
            for index, year in enumerate(years)}


def build():
    import pymupdf

    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    if {source['key'] for source in manifest} != PAGES.keys() or len(manifest) != len(PAGES):
        raise ValueError('Incomplete report manifest')
    rows = {}
    for source in sorted(manifest, key=lambda item: item['key']):
        key = source['key']
        code, year_text = key.split('-')
        report_year = int(year_text)
        data = (ROOT / (key + '.pdf')).read_bytes()
        digest = sha256(data).hexdigest()
        if digest != source['sha256']:
            raise ValueError(f'Report hash mismatch: {key}')
        page = PAGES[key]
        with pymupdf.open(stream=data, filetype='pdf') as doc:
            metrics = extract_metrics(doc[page - 1].get_text(sort=True), report_year)
        for year, values in metrics.items():
            if year not in range(2021, 2026):
                continue
            previous = rows.get((code, year))
            if previous and previous['amounts'] != values:
                raise ValueError(f'Comparative columns disagree: {code}/{year}')
            if previous:
                continue
            rows[code, year] = dict(ticker=code, company=COMPANIES[code], year=year,
                                   currency='CNY', unit='元', data_kind='public_disclosure',
                                   amounts=values, report_year=report_year, page=page,
                                   source_url=source['url'], source_sha256=digest)
    expected = {(code, year) for code in COMPANIES for year in range(2021, 2026)}
    if rows.keys() != expected:
        raise ValueError('Company-year coverage gap')
    result = [rows[key] for key in sorted(rows)]
    (ROOT / 'facts.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'report.html').write_text(render(result), encoding='utf-8')
    return result


def render(rows):
    headers = ''.join(f'<th>{escape(label)}</th>' for label in METRICS.values())
    body = []
    for row in rows:
        amounts = ''.join(f'<td>{Decimal(row["amounts"][metric]):,.2f}</td>' for metric in METRICS)
        source = escape(row['source_url'], quote=True)
        body.append(f'<tr><td>{escape(row["company"])} {escape(row["ticker"])}</td><td>{row["year"]}</td>{amounts}'
                    f'<td><a href="{source}#page={row["page"]}">{row["report_year"]}年报 · PDF 第{row["page"]}页</a></td></tr>')
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>A股公开财报测试集</title><style>body{font:16px system-ui;margin:24px;color:#17233a}table{border-collapse:collapse;white-space:nowrap}'
            'td,th{padding:10px;border-bottom:1px solid #d9e1ed;text-align:right}th{background:#eef3f9}section{overflow:auto}</style>'
            '<h1>A股公开财报测试集</h1><p>3家公司 · 2021–2025年 · 人民币元。数据来自公开年报的主要会计数据表。</p>'
            '<p>每行对应一个公司和财年，保留当年或年报比较列来源。测试集独立于企业凭证明细。</p>'
            '<p><a href="?format=json">查看结构化数据与 SHA256</a></p><section><table><thead><tr><th>公司</th><th>财年</th>'
            f'{headers}<th>年报来源</th></tr></thead><tbody>{"".join(body)}</tbody></table></section></html>')


if __name__ == '__main__':
    print(f'Validated {len(build())} company-year rows')
