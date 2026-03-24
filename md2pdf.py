#!/usr/bin/env python3
import markdown
from weasyprint import HTML

with open('IMPROVEMENT_PROPOSALS.md', 'r', encoding='utf-8') as f:
    md = f.read()

html = markdown.markdown(md, extensions=['tables', 'fenced_code'])
styled = f'<html><head><meta charset="UTF-8"><style>@page{{size:A4;margin:2cm}}body{{font-family:"Noto Sans CJK KR","Noto Sans CJK","Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-size:11pt;line-height:1.6;color:#333}}h1{{color:#1a365d;border-bottom:3px solid #3182ce;padding-bottom:10px}}h2{{color:#2c5282;border-bottom:2px solid #90cdf4;padding-bottom:8px;margin-top:30px}}h3{{color:#2d3748;margin-top:20px}}pre{{background:#2d3748;color:#e2e8f0;padding:15px;border-radius:8px;font-size:9pt;white-space:pre-wrap;word-wrap:break-word}}table{{width:100%;border-collapse:collapse;margin:15px 0}}th{{background:#3182ce;color:#fff;padding:12px;text-align:left}}td{{padding:10px;border-bottom:1px solid #ddd}}code{{background:#f7fafc;padding:2px 6px;border-radius:3px;color:#e53e3e;font-size:9pt}}ul,ol{{padding-left:25px}}li{{margin:5px 0}}hr{{border:none;border-top:1px solid #e2e8f0;margin:30px 0}}</style></head><body>{html}</body></html>'

HTML(string=styled).write_pdf('IMPROVEMENT_PROPOSALS.pdf')
print("PDF 생성 완료!")