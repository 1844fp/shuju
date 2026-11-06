"""Exact, formula-free finance snapshots. Host installs routes and auth middleware."""
import io
from xml.sax.saxutils import escape
from fastapi.responses import Response
FIELDS=['period','currency','revenue','cost','expense','gross_profit','operating_profit','gross_margin','metric_version','data_kind','batch_ids']
NOTICE='已核算文本快照，不含公式、不进行二次计算；模拟数据见data_kind；经营利润不等于净利润。'

def snapshot(start_period,end_period,currency):
    import app as core
    # finance resolves the request-bound organization engine via current_db.
    rows=core.finance(start_period,end_period,currency)
    return rows

def xlsx_bytes(rows,start,end,currency):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    w=Workbook();s=w.active;s.title='Finance snapshot'
    s.append([NOTICE]);s.append([f'{start} — {end}',currency,'metric_version=1.0']);s.append(FIELDS)
    for r in rows:s.append([', '.join(str(v) for v in r[k]) if isinstance(r.get(k),list) else str(r.get(k) if r.get(k) is not None else '') for k in FIELDS])
    for row in s:
        for c in row:
            if c.value is not None:c.value=str(c.value);c.data_type='s';c.number_format='@'
            c.font=Font(name='Arial',size=10);c.alignment=Alignment(vertical='top',wrap_text=True)
    for c in s[3]:c.fill=PatternFill('solid',fgColor='16324F');c.font=Font(name='Arial',color='FFFFFF',bold=True)
    for i in range(1,len(FIELDS)+1):s.column_dimensions[get_column_letter(i)].width=24 if i<9 else 42
    s.freeze_panes='C4';s.auto_filter.ref=f'A3:K{max(3,s.max_row)}';s.row_dimensions[1].height=40
    b=io.BytesIO();w.save(b);return b.getvalue()

def pdf_bytes(rows,start,end,currency):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    style=ParagraphStyle('Chinese',fontName='STSong-Light',fontSize=10,leading=16,wordWrap='CJK')
    b=io.BytesIO();story=[]
    def p(t):return Paragraph(escape(str(t)),style)
    story += [p('财务经营报告 · 文本快照'),p(f'期间 {start} 至 {end} / {currency} / 指标版本 1.0'),p(NOTICE),Spacer(1,18)]
    if not rows:story.append(p('该期间及币种无数据。'))
    for r in rows:
        from decimal import Decimal
        margin='不适用' if r['gross_margin'] is None else format(Decimal(r['gross_margin'])*100,'.2f')+'%'
        block=[p(f"期间 {r['period']} · {r['currency']}"),p(f"收入 {r['revenue']}；成本 {r['cost']}；费用 {r['expense']}"),p(f"毛利润 {r['gross_profit']}；经营利润 {r['operating_profit']}；毛利率 {margin}" )]
        block += [p('指标版本：'+str(r['metric_version'])),p('数据类型：'+', '.join(r['data_kind']))]
        for bid in r['batch_ids']:block.append(p('来源批次：'+bid))
        story.append(KeepTogether(block))
        story.append(Spacer(1,14))
    def footer(c,d):
        c.setFont('STSong-Light',9);c.drawString(42,24,f'财务快照 · 第 {d.page} 页')
    SimpleDocTemplate(b,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    return b.getvalue()

def install(app):
    @app.get('/api/v1/exports/finance.docx')
    def word(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'):
        return Response(docx_bytes(snapshot(start_period,end_period,currency),start_period,end_period,currency),media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',headers={'Content-Disposition':'attachment; filename="finance.docx"'})
    @app.get('/api/v1/exports/finance.xlsx')
    def excel(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'):
        return Response(xlsx_bytes(snapshot(start_period,end_period,currency),start_period,end_period,currency),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="finance.xlsx"'})
    @app.get('/api/v1/exports/finance.pdf')
    def pdf(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'):
        return Response(pdf_bytes(snapshot(start_period,end_period,currency),start_period,end_period,currency),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="finance.pdf"'})

def docx_bytes(rows,start,end,currency):
    """Minimal OpenXML text report; exact financial strings, no executable fields."""
    from zipfile import ZipFile,ZIP_DEFLATED
    def paragraph(value,title=False,keep=False):
        clean=''.join(c for c in str(value) if c in '\t\n\r' or 32<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD or 0x10000<=ord(c)<=0x10FFFF)
        properties='<w:pPr><w:keepLines/>'+('<w:keepNext/>' if title or keep else '')+'</w:pPr>'
        style='<w:b/><w:sz w:val="28"/>' if title else '<w:sz w:val="22"/>'
        return '<w:p>'+properties+'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="Microsoft YaHei"/>'+style+'</w:rPr><w:t xml:space="preserve">'+escape(clean)+'</w:t></w:r></w:p>'
    body=[paragraph('财务经营报告 · 文本快照',True),paragraph(f'期间 {start} 至 {end} / {currency}'),paragraph(NOTICE)]
    if not rows:body.append(paragraph('该期间及币种无数据。'))
    labels={'period':'期间','currency':'币种','revenue':'收入','cost':'成本','expense':'费用','gross_profit':'毛利润','operating_profit':'经营利润','gross_margin':'毛利率（比例）','metric_version':'指标版本','data_kind':'数据类型','batch_ids':'来源批次'}
    for row in rows:
        body.append(paragraph(str(row['period'])+' · '+str(row['currency']),True))
        entries=[]
        for key in FIELDS:
            value=row.get(key)
            values=value if isinstance(value,list) else [value]
            for item in values:entries.append(labels[key]+'：'+('不适用' if item is None else str(item)))
        for index,entry in enumerate(entries):body.append(paragraph(entry,keep=index<len(entries)-1))
    document='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join(body)+'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'
    output=io.BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml',document)
    return output.getvalue()
