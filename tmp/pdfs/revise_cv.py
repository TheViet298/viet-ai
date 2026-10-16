from pathlib import Path
from copy import deepcopy
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ContentStream, NameObject, ArrayObject
from reportlab.lib import colors

root=Path('D:/142.AI20K/P-142')
source=next(Path('D:/Downloads').glob('2A202602633_*.pdf'))
reader=PdfReader(source)
original=reader.pages[0]
text=original.extract_text()
for name,file in [('CV','times.ttf'),('CV-Bold','timesbd.ttf'),('CV-Italic','timesi.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('CV',normal='CV',bold='CV-Bold',italic='CV-Italic',boldItalic='CV-Bold')
body=ParagraphStyle('body',fontName='CV',fontSize=10,leading=11.3,alignment=TA_LEFT)
bold=ParagraphStyle('bold',parent=body,fontName='CV-Bold')
italic=ParagraphStyle('italic',parent=body,fontName='CV-Italic',fontSize=9.7)
heading=ParagraphStyle('heading',parent=bold,fontSize=12,leading=14,spaceBefore=8,spaceAfter=2)
right=ParagraphStyle('right',parent=body,alignment=TA_RIGHT)
bullet=ParagraphStyle('bullet',parent=body,leftIndent=13,firstLineIndent=0,bulletIndent=3,spaceAfter=1.5)
story=[]
def p(s,style=body): return Paragraph(escape(s),style)
def section(s):
    story.extend([p(s,heading),HRFlowable(width='100%',thickness=.5,color=colors.black,spaceAfter=4)])
def row(title,date):
    t=Table([[p(title,bold),p(date,right)]],colWidths=[385,142])
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),1)]))
    story.append(t)
def bullets(s):
    for chunk in s.split('•')[1:]:
        story.append(Paragraph(escape(' '.join(chunk.split())),bullet,bulletText='•'))

section('SUMMARY')
story.append(p(' '.join(text.split('SUMMARY\n')[1].split('\nEDUCATION')[0].split())))
section('EDUCATION')
row('University of Transport Technology (UTT)','2022 – 2026')
story.append(p('Major: Information Technology'))
story.append(Spacer(1,6))
row('VinUniversity (VinUni)','Sep 2026 – Present')
story.append(p('AI Practical Talent Development Program – Cohort 4'))
section('EXPERIENCE')
row('Kaigents Corp','Sep 2025 – Feb 2026')
story.append(p('AI Engineer Intern',bold))
bullets(text.split('AI Engineer Intern\n')[1].split('\nSKILLS')[0])
section('SKILLS')
skill_rows=[
('Programming','Python, SQL'),
('AI & Machine Learning','RAG, NLP, LLM Integration, Transformers, Multi-Agent Systems, Fine-Tuning, Prompt Engineering'),
('Frameworks & Libraries','LangGraph, LangChain, PyTorch, TensorFlow, FastAPI'),
('Data & Databases','PostgreSQL, MySQL, ChromaDB, Pandas, NumPy'),
('Tools & Deployment','Git/GitHub, Docker, Kubernetes, n8n, Langfuse'),
('Languages','English (technical reading and workplace communication), Vietnamese (native)')]
t=Table([[p(a),p(b)] for a,b in skill_rows],colWidths=[138,389])
t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),1.5),('BOTTOMPADDING',(0,0),(-1,-1),1.5)]))
story.append(t)
section('PROJECTS')
row('VFServ | AI Engineer','Sep 2026 – Present')
story.append(p('Python, FastAPI, LangGraph, LangChain, Langfuse, ChromaDB, PostgreSQL, Docker, Vercel',italic))
story.append(Paragraph('<b>GitHub:</b> <link href="https://github.com/AI20K-Build-Phase-Cohort-4/P-142">github.com/AI20K-Build-Phase-Cohort-4/P-142</link>',body))
story.append(Paragraph('<b>Demo:</b> <link href="https://vfserv-ai.vercel.app/">vfserv-ai.vercel.app</link>',body))
bullets(text.split('Demo: vfserv-ai.vercel.app\n')[1].split('\nHomeNest')[0])
story.append(Spacer(1,5))
row('HomeNest','Mar 2026 – May 2026')
story.append(p('Python, LangChain, ChromaDB, FAISS, JavaScript, FastAPI, MySQL, Docker',italic))
story.append(Paragraph('<b>GitHub:</b> <link href="https://github.com/may31st/HomeNest">github.com/may31st/HomeNest</link>',body))
bullets(text.split('GitHub: github.com/may31st/HomeNest\n')[1])
temp=root/'tmp/pdfs/cv-body.pdf'
w,h=float(original.mediabox.width),float(original.mediabox.height)
def draw_header(c,doc):
    c.saveState()
    c.drawImage(str(root/'tmp/pdfs/cv-header.png'),0,h-84,width=w,height=84)
    hidden=c.beginText(72,h-73)
    hidden.setFont('CV',1)
    hidden.setTextRenderMode(3)
    hidden.textOut('Dinh Duc Long | AI Engineer | 0867556109 | longduc31st@gmail.com | Ha Dong, Ha Noi | github.com/may31st | linkedin.com/in/may31st/')
    c.drawText(hidden)
    c.restoreState()
    for a in original.get('/Annots',[]):
        obj=a.get_object()
        rect=list(map(float,obj['/Rect']))
        if rect[1]>h-84 and obj.get('/A',{}).get('/URI'):
            c.linkURL(str(obj['/A']['/URI']),rect,relative=0,thickness=0)
SimpleDocTemplate(str(temp),pagesize=(w,h),leftMargin=28,rightMargin=28,topMargin=88,bottomMargin=24).build(story,onFirstPage=draw_header)
body_reader=PdfReader(temp)
assert len(body_reader.pages)==1, 'CV exceeds one page'
header=deepcopy(original)
stream=ContentStream(original.get_contents(),reader)
for index,(args,op) in enumerate(stream.operations):
    if op==b'TJ' and ''.join(str(a) for a in args[0] if isinstance(a,str))=='SUMMARY':
        summary_index=index
        break
last_text=max(i for i,(args,op) in enumerate(stream.operations[:summary_index]) if op in (b'TJ',b'Tj'))
ops=stream.operations[:last_text+1]
if sum(op==b'BT' for _,op in ops)>sum(op==b'ET' for _,op in ops): ops.append(([],b'ET'))
depth=sum(op==b'q' for _,op in ops)-sum(op==b'Q' for _,op in ops)
ops.extend([([],b'Q')]*depth)
stream.operations=ops
header[NameObject('/Contents')]=stream
# Keep only contact links, which lie in the preserved header strip.
header[NameObject('/Annots')]=ArrayObject([a for a in header.get('/Annots',[]) if float(a.get_object()['/Rect'][1])>h-84])
page=body_reader.pages[0]
# The original contact strip is already preserved by draw_header.
writer=PdfWriter();writer.add_page(page)
writer.add_metadata({'/Title':'Dinh Duc Long - AI Engineer CV','/Author':'Dinh Duc Long'})
out=root/'output/pdf/Dinh-Duc-Long-CV.pdf'
with out.open('wb') as f: writer.write(f)
check=PdfReader(out)
assert len(check.pages)==1
assert 'VFServ | AI Engineer' in check.pages[0].extract_text()
assert check.pages[0].extract_text().count('SUMMARY')==1
print('Saved',out,'pages',len(check.pages))
