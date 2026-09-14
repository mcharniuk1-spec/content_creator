from pathlib import Path
import argparse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
src = args.source
dst = args.output
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=8.5, leading=11))
styles.add(ParagraphStyle(name='Card', parent=styles['Heading2'], textColor='#183B56', spaceBefore=10))
story=[]
for raw in src.read_text(encoding='utf-8').splitlines():
    line=raw.strip()
    if not line:
        story.append(Spacer(1, 3)); continue
    if line.startswith('# '): style='Title'
    elif line.startswith('## '): style='Heading1'
    elif line.startswith('### '): style='Card'
    elif line.startswith('- '): line='• '+line[2:]; style='Small'
    else: style='Small'
    text=line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('**','').replace('`','')
    story.append(Paragraph(text, styles[style]))
doc=SimpleDocTemplate(str(dst), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=15*mm, title='M2 Lab reconciled analysis and ten cards')
doc.build(story)
print(dst)
