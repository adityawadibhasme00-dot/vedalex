from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                 PageBreak, Image, KeepTogether, ListFlowable, ListItem,
                                 NextPageTemplate, PageTemplate, Frame, BaseDocTemplate)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os

OUTPUT_DIR = r"C:\Users\adity\OneDrive\Pictures\Desktop\SIH Final\xyz"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "IP_SAKTI_Complete_Documentation.pdf")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGE_W, PAGE_H = A4
MARGIN = 0.6 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

PRIMARY = HexColor('#059669')
DARK = HexColor('#0F172A')
SLATE = HexColor('#334155')
LIGHT_BG = HexColor('#F1F5F9')
ACCENT = HexColor('#D97706')
WHITE = white
BORDER = HexColor('#CBD5E1')
CODE_BG = HexColor('#1E293B')

styles = getSampleStyleSheet()

title_style = ParagraphStyle('TitleX', parent=styles['Title'], fontSize=28, spaceAfter=8,
                             alignment=TA_CENTER, textColor=PRIMARY, fontName='Helvetica-Bold', leading=34)
subtitle_style = ParagraphStyle('SubTitleX', parent=styles['Normal'], fontSize=14, spaceAfter=4,
                                alignment=TA_CENTER, textColor=SLATE, fontName='Helvetica', leading=18)
h1_style = ParagraphStyle('H1X', parent=styles['Heading1'], fontSize=18, spaceAfter=10, spaceBefore=16,
                          textColor=DARK, fontName='Helvetica-Bold', leading=22,
                          borderWidth=0, borderPadding=0)
h2_style = ParagraphStyle('H2X', parent=styles['Heading2'], fontSize=14, spaceAfter=6, spaceBefore=12,
                          textColor=PRIMARY, fontName='Helvetica-Bold', leading=18)
h3_style = ParagraphStyle('H3X', parent=styles['Heading3'], fontSize=11, spaceAfter=4, spaceBefore=8,
                          textColor=SLATE, fontName='Helvetica-Bold', leading=14)
body_style = ParagraphStyle('BodyX', parent=styles['Normal'], fontSize=9.5, spaceAfter=5,
                            alignment=TA_JUSTIFY, leading=13, textColor=HexColor('#1E293B'))
bullet_style = ParagraphStyle('BulletX', parent=styles['Normal'], fontSize=9.5, spaceAfter=3,
                              leftIndent=16, bulletIndent=6, leading=12, textColor=HexColor('#1E293B'))
sub_bullet_style = ParagraphStyle('SubBulletX', parent=styles['Normal'], fontSize=9, spaceAfter=2,
                                  leftIndent=32, bulletIndent=22, leading=11, textColor=HexColor('#475569'))
code_style = ParagraphStyle('CodeX', parent=styles['Code'], fontSize=8, spaceAfter=4,
                            leftIndent=16, fontName='Courier', textColor=HexColor('#E2E8F0'),
                            backColor=CODE_BG, borderPadding=6, leading=11)
caption_style = ParagraphStyle('CaptionX', parent=styles['Normal'], fontSize=8, spaceAfter=8,
                               alignment=TA_CENTER, textColor=HexColor('#64748B'), fontName='Helvetica-Oblique')
table_header_style = ParagraphStyle('THX', parent=styles['Normal'], fontSize=8.5, fontName='Helvetica-Bold',
                                    textColor=white, alignment=TA_LEFT, leading=11)
table_cell_style = ParagraphStyle('TCX', parent=styles['Normal'], fontSize=8.5, alignment=TA_LEFT,
                                  leading=11, textColor=HexColor('#1E293B'))

elements = []

def h1(text):
    elements.append(Paragraph(text, h1_style))
    elements.append(Spacer(1, 4))

def h2(text):
    elements.append(Paragraph(text, h2_style))

def h3(text):
    elements.append(Paragraph(text, h3_style))

def p(text):
    elements.append(Paragraph(text, body_style))

def bullet(text):
    elements.append(Paragraph(f"• {text}", bullet_style))

def sub_bullet(text):
    elements.append(Paragraph(f"– {text}", sub_bullet_style))

def sp(h=8):
    elements.append(Spacer(1, h))

def caption(text):
    elements.append(Paragraph(text, caption_style))

def make_table(data, col_widths, header_bg=PRIMARY):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t

def draw_box(d, x, y, w, h, text, fill=DARK, font_size=7, text_color=white, stroke=PRIMARY):
    rect = Rect(x, y, w, h, fillColor=fill, strokeColor=stroke, strokeWidth=1)
    d.add(rect)
    lines = text.split('\n')
    total_h = len(lines) * (font_size + 2)
    start_y = y + h/2 + total_h/2 - font_size
    for i, line in enumerate(lines):
        s = String(x + w/2, start_y - i * (font_size + 2), line, fontSize=font_size,
                   fillColor=text_color, textAnchor='middle', fontName='Helvetica-Bold')
        d.add(s)

def draw_arrow_down(d, x, y1, y2, color=PRIMARY):
    d.add(Line(x, y1, x, y2, strokeColor=color, strokeWidth=1.2))
    d.add(Polygon([x-3, y2, x+3, y2, x, y2+5], fillColor=color, strokeColor=color))

def draw_arrow_right(d, x1, x2, y, color=PRIMARY):
    d.add(Line(x1, y, x2, y, strokeColor=color, strokeWidth=1.2))
    d.add(Polygon([x2-5, y-3, x2-5, y+3, x2, y], fillColor=color, strokeColor=color))

def vertical_flow_diagram(title, nodes, width=460, node_h=28, gap=18, start_y=None):
    total_h = len(nodes) * (node_h + gap) + 40
    d = Drawing(width, total_h)
    if start_y is None:
        start_y = total_h - 30
    bw = width * 0.7
    bx = (width - bw) / 2
    for i, node in enumerate(nodes):
        y = start_y - i * (node_h + gap)
        if isinstance(node, tuple):
            label, fill = node
        else:
            label, fill = node, DARK
        draw_box(d, bx, y - node_h, bw, node_h, label, fill=fill)
        if i < len(nodes) - 1:
            draw_arrow_down(d, width/2, y - node_h, y - node_h - gap + 3)
    return d

def pipeline_diagram(title, stages, width=460):
    n = len(stages)
    box_w = width / n - 10
    box_h = 50
    d = Drawing(width, 100)
    y = 25
    for i, (label, fill) in enumerate(stages):
        x = i * (box_w + 10) + 5
        draw_box(d, x, y, box_w, box_h, label, fill=fill, font_size=6.5)
        if i < n - 1:
            draw_arrow_right(d, x + box_w, y + box_h/2, x + box_w + 10, y + box_h/2)
    return d

def architecture_diagram():
    d = Drawing(480, 420)
    accent = PRIMARY
    dark = DARK
    mid = SLATE
    light = HexColor('#64748B')

    draw_box(d, 140, 380, 200, 30, "PRESENTATION LAYER", fill=HexColor('#1E40AF'))
    draw_box(d, 140, 340, 200, 30, "Next.js 14 Frontend\nReact + TypeScript + Tailwind", fill=dark, font_size=7)
    draw_arrow_down(d, 240, 380, 370)

    draw_box(d, 140, 300, 200, 30, "API GATEWAY", fill=HexColor('#7C3AED'))
    draw_box(d, 140, 260, 200, 30, "FastAPI + Pydantic v2\nREST Endpoints + Swagger", fill=dark, font_size=7)
    draw_arrow_down(d, 240, 300, 290)

    draw_box(d, 140, 220, 200, 30, "AUTHENTICATION", fill=HexColor('#B91C1C'))
    draw_box(d, 140, 180, 200, 30, "JWT + Password Hashing\nDPDP Consent Logger", fill=dark, font_size=7)
    draw_arrow_down(d, 240, 220, 210)

    draw_box(d, 140, 140, 200, 30, "CORE SERVICES", fill=HexColor('#0E7490'))
    draw_box(d, 140, 100, 200, 30, "Rule Engine | RAG | Botonical\nResolver | Verification", fill=dark, font_size=7)
    draw_arrow_down(d, 240, 140, 130)

    draw_box(d, 140, 60, 200, 30, "DATA LAYER", fill=HexColor('#365314'))
    draw_box(d, 140, 20, 200, 30, "PostgreSQL | FAISS Index\nKnowledge Base | Uploads", fill=dark, font_size=7)

    draw_box(d, 20, 220, 90, 30, "AI Engine", fill=mid, font_size=7)
    draw_arrow_right(d, 110, 140, 235)
    draw_box(d, 370, 220, 90, 30, "Knowledge\nBase", fill=mid, font_size=7)
    draw_arrow_right(d, 340, 370, 235)

    return d

def user_flow_diagram():
    nodes = [
        ("Landing Page", HexColor('#1E40AF')),
        ("Sign Up / Login", HexColor('#7C3AED')),
        ("OTP Verification", HexColor('#B91C1C')),
        ("Dashboard", HexColor('#0E7490')),
        ("Innovation Passport", HexColor('#059669')),
        ("Document Upload", HexColor('#D97706')),
        ("AI Copilot Query", HexColor('#0F172A')),
        ("Patent Analysis", HexColor('#059669')),
        ("Regulatory Roadmap", HexColor('#0E7490')),
        ("Claim Firewall", HexColor('#B91C1C')),
        ("Dossier Export", HexColor('#365314')),
    ]
    return vertical_flow_diagram("User Flow", nodes, width=460, node_h=26, gap=14)

def system_flow_diagram():
    d = Drawing(480, 500)
    accent = PRIMARY
    dark = DARK
    mid = SLATE

    draw_box(d, 150, 460, 180, 28, "USER INPUT\n(Text / Voice / Scanned Docs)", fill=HexColor('#1E40AF'), font_size=7)
    draw_arrow_down(d, 240, 460, 448)

    draw_box(d, 150, 420, 180, 28, "MULTILINGUAL UI\n(10 Languages)", fill=dark, font_size=7)
    draw_arrow_down(d, 240, 420, 408)

    draw_box(d, 150, 380, 180, 28, "INPUT SANDBOXING\nPrompt-Injection Defense", fill=HexColor('#B91C1C'), font_size=7)
    draw_arrow_down(d, 240, 380, 368)

    draw_box(d, 150, 340, 180, 28, "INNOVATION PASSPORT\nFact Origin Tracker", fill=HexColor('#0E7490'), font_size=7)
    draw_arrow_down(d, 240, 340, 328)

    draw_box(d, 150, 300, 180, 28, "BOTANICAL RESOLVER\nFormulation Fingerprint", fill=HexColor('#059669'), font_size=7)
    draw_arrow_down(d, 240, 300, 288)

    draw_box(d, 150, 260, 180, 28, "RULE ENGINE (3-State)\nJurisdiction Router", fill=HexColor('#7C3AED'), font_size=7)
    draw_arrow_down(d, 240, 260, 248)

    draw_box(d, 150, 220, 180, 28, "HYBRID RAG RETRIEVAL\nBM25 + Dense + Rerank", fill=HexColor('#D97706'), font_size=7)
    draw_arrow_down(d, 240, 220, 208)

    draw_box(d, 150, 180, 180, 28, "CITATION VALIDATOR\nUCR Gate (<5%)", fill=HexColor('#B91C1C'), font_size=7)
    draw_arrow_down(d, 240, 180, 168)

    draw_box(d, 150, 140, 180, 28, "VERIFICATION LAYER\nClaim Extract + Entail", fill=mid, font_size=7)
    draw_arrow_down(d, 240, 140, 128)

    draw_box(d, 150, 100, 180, 28, "LLM EXPLANATION\nGrounded by Passages", fill=HexColor('#059669'), font_size=7)
    draw_arrow_down(d, 240, 100, 88)

    draw_box(d, 150, 60, 180, 28, "OUTPUT\nFindings + Dossier", fill=HexColor('#365314'), font_size=7)

    draw_box(d, 20, 260, 100, 28, "Knowledge\nBase", fill=mid, font_size=7)
    draw_arrow_right(d, 120, 150, 274)
    draw_box(d, 360, 260, 100, 28, "FAISS\nIndex", fill=mid, font_size=7)
    draw_arrow_right(d, 330, 360, 274)

    return d

def auth_flow_diagram():
    nodes = [
        ("Registration", HexColor('#1E40AF')),
        ("Email Verification", HexColor('#7C3AED')),
        ("OTP Verification", HexColor('#B91C1C')),
        ("Login", HexColor('#0E7490')),
        ("JWT Token Generated", HexColor('#059669')),
        ("Access Dashboard", HexColor('#D97706')),
        ("Refresh Token", HexColor('#0F172A')),
        ("Logout", HexColor('#B91C1C')),
    ]
    return vertical_flow_diagram("Auth Flow", nodes, width=400, node_h=26, gap=14)

def cicd_diagram():
    stages = [
        ("Developer\nPush", HexColor('#1E40AF')),
        ("GitHub\nRepo", HexColor('#0F172A')),
        ("Build\nDocker", HexColor('#7C3AED')),
        ("Testing\nPytest", HexColor('#B91C1C')),
        ("Deploy\nCloud", HexColor('#059669')),
        ("Monitor\nLogs", HexColor('#D97706')),
    ]
    return pipeline_diagram("CI/CD", stages, width=460)

def tech_stack_diagram():
    d = Drawing(460, 300)
    layers = [
        ("Presentation Layer\nNext.js 14 + React 18 + TypeScript", HexColor('#1E40AF')),
        ("Styling Layer\nTailwind CSS + Glassmorphism", HexColor('#7C3AED')),
        ("API Layer\nFastAPI + Pydantic v2 + Swagger", HexColor('#0E7490')),
        ("AI Layer\nBGE Embeddings + FAISS + RAG", HexColor('#059669')),
        ("Data Layer\nPostgreSQL + SQLAlchemy", HexColor('#D97706')),
        ("Infra Layer\nDocker + AWS ap-south-1", HexColor('#365314')),
    ]
    y = 270
    for label, fill in layers:
        draw_box(d, 80, y, 300, 32, label, fill=fill, font_size=8)
        y -= 40
    return d

def er_diagram():
    d = Drawing(460, 300)
    accent = PRIMARY
    dark = DARK

    draw_box(d, 30, 240, 100, 40, "USERS\nid (PK)\nemail\npassword_hash\nrole", fill=dark, font_size=7)
    draw_box(d, 180, 240, 120, 40, "PASSPORTS\nid (PK)\nuser_id (FK)\ncase_title\nproduct_form\nversion", fill=HexColor('#0E7490'), font_size=7)
    draw_box(d, 350, 240, 100, 40, "INGREDIENTS\nid (PK)\npassport_id (FK)\nbotanical_name\nratio", fill=HexColor('#059669'), font_size=7)

    draw_box(d, 30, 140, 100, 40, "FINDINGS\nid (PK)\npassport_id (FK)\njurisdiction\nstatus\nconfidence", fill=HexColor('#7C3AED'), font_size=7)
    draw_box(d, 180, 140, 120, 40, "CITATIONS\nid (PK)\nfinding_id (FK)\nact_title\nsection_ref", fill=HexColor('#B91C1C'), font_size=7)
    draw_box(d, 350, 140, 100, 40, "RULES\nid (PK)\njurisdiction\nrule_pack\nversion", fill=HexColor('#D97706'), font_size=7)

    draw_box(d, 105, 40, 100, 40, "EVIDENCE\nid (PK)\nfinding_id (FK)\nsource_url\npassage", fill=HexColor('#365314'), font_size=7)
    draw_box(d, 280, 40, 100, 40, "UPLOADS\nid (PK)\nuser_id (FK)\nfile_type\ncontent", fill=HexColor('#475569'), font_size=7)

    d.add(Line(130, 260, 180, 260, strokeColor=accent, strokeWidth=1))
    d.add(Line(300, 260, 350, 260, strokeColor=accent, strokeWidth=1))
    d.add(Line(80, 240, 80, 180, strokeColor=accent, strokeWidth=1))
    d.add(Line(240, 240, 240, 180, strokeColor=accent, strokeWidth=1))
    d.add(Line(400, 240, 400, 180, strokeColor=accent, strokeWidth=1))
    d.add(Line(130, 160, 180, 160, strokeColor=accent, strokeWidth=1))
    d.add(Line(300, 160, 350, 160, strokeColor=accent, strokeWidth=1))
    d.add(Line(155, 140, 155, 80, strokeColor=accent, strokeWidth=1))
    d.add(Line(330, 140, 330, 80, strokeColor=accent, strokeWidth=1))

    return d

def monitoring_diagram():
    stages = [
        ("App\nLogs", HexColor('#1E40AF')),
        ("Error\nTracking", HexColor('#B91C1C')),
        ("Performance\nMetrics", HexColor('#059669')),
        ("User\nFeedback", HexColor('#D97706')),
        ("Alert\nSystem", HexColor('#7C3AED')),
    ]
    return pipeline_diagram("Monitoring", stages, width=460)

def security_diagram():
    d = Drawing(460, 350)
    accent = PRIMARY
    dark = DARK

    draw_box(d, 150, 310, 160, 28, "Incoming Request", fill=HexColor('#1E40AF'), font_size=7)
    draw_arrow_down(d, 230, 310, 298)

    draw_box(d, 150, 270, 160, 28, "HTTPS / TLS 1.3", fill=HexColor('#0E7490'), font_size=7)
    draw_arrow_down(d, 230, 270, 258)

    draw_box(d, 150, 230, 160, 28, "Rate Limiting", fill=HexColor('#D97706'), font_size=7)
    draw_arrow_down(d, 230, 230, 218)

    draw_box(d, 150, 190, 160, 28, "JWT Authentication", fill=HexColor('#7C3AED'), font_size=7)
    draw_arrow_down(d, 230, 190, 178)

    draw_box(d, 150, 150, 160, 28, "Authorization\n(Role-Based)", fill=HexColor('#B91C1C'), font_size=7)
    draw_arrow_down(d, 230, 150, 138)

    draw_box(d, 150, 110, 160, 28, "Input Validation\n(Pydantic)", fill=HexColor('#059669'), font_size=7)
    draw_arrow_down(d, 230, 110, 98)

    draw_box(d, 150, 70, 160, 28, "SQL/XSS Protection\n(Sanitizer)", fill=HexColor('#365314'), font_size=7)
    draw_arrow_down(d, 230, 70, 58)

    draw_box(d, 150, 30, 160, 28, "Response", fill=dark, font_size=7)

    return d

def ai_pipeline_diagram():
    d = Drawing(460, 400)
    accent = PRIMARY
    dark = DARK

    draw_box(d, 150, 360, 160, 28, "Data Collection\nGazettes + Monographs", fill=HexColor('#1E40AF'), font_size=7)
    draw_arrow_down(d, 230, 360, 348)

    draw_box(d, 150, 320, 160, 28, "Preprocessing\nChunk + Tokenize", fill=HexColor('#0E7490'), font_size=7)
    draw_arrow_down(d, 230, 320, 308)

    draw_box(d, 150, 280, 160, 28, "Embedding\nBGE-base-en-v1.5", fill=HexColor('#7C3AED'), font_size=7)
    draw_arrow_down(d, 230, 280, 268)

    draw_box(d, 150, 240, 160, 28, "FAISS Index\nFlat Index", fill=HexColor('#059669'), font_size=7)
    draw_arrow_down(d, 230, 240, 228)

    draw_box(d, 150, 200, 160, 28, "Query\nUser Question", fill=HexColor('#D97706'), font_size=7)
    draw_arrow_down(d, 230, 200, 188)

    draw_box(d, 150, 160, 160, 28, "Retrieval\nTop-5 Chunks", fill=HexColor('#B91C1C'), font_size=7)
    draw_arrow_down(d, 230, 160, 148)

    draw_box(d, 150, 120, 160, 28, "LLM Inference\nGrounded Generation", fill=HexColor('#0F172A'), font_size=7)
    draw_arrow_down(d, 230, 120, 108)

    draw_box(d, 150, 80, 160, 28, "Confidence Score\nUCR Gate", fill=HexColor('#365314'), font_size=7)
    draw_arrow_down(d, 230, 80, 68)

    draw_box(d, 150, 40, 160, 28, "Output\nAnswer + Sources", fill=PRIMARY, font_size=7)

    return d

def decision_tree_diagram():
    d = Drawing(460, 250)
    accent = PRIMARY
    dark = DARK

    draw_box(d, 150, 210, 160, 28, "User Request", fill=HexColor('#1E40AF'), font_size=7)
    draw_arrow_down(d, 230, 210, 198)

    draw_box(d, 150, 170, 160, 28, "Valid Input?", fill=HexColor('#D97706'), font_size=7)
    draw_arrow_down(d, 230, 170, 158)
    draw_box(d, 330, 170, 100, 28, "Error 400\nBad Request", fill=HexColor('#B91C1C'), font_size=7)
    d.add(Line(310, 184, 330, 184, strokeColor=accent, strokeWidth=1))

    draw_box(d, 150, 130, 160, 28, "Authenticated?", fill=HexColor('#D97706'), font_size=7)
    draw_arrow_down(d, 230, 130, 118)
    draw_box(d, 330, 130, 100, 28, "Error 401\nUnauthorized", fill=HexColor('#B91C1C'), font_size=7)
    d.add(Line(310, 144, 330, 144, strokeColor=accent, strokeWidth=1))

    draw_box(d, 150, 90, 160, 28, "Authorized?", fill=HexColor('#D97706'), font_size=7)
    draw_arrow_down(d, 230, 90, 78)
    draw_box(d, 330, 90, 100, 28, "Error 403\nForbidden", fill=HexColor('#B91C1C'), font_size=7)
    d.add(Line(310, 104, 330, 104, strokeColor=accent, strokeWidth=1))

    draw_box(d, 150, 50, 160, 28, "Process Request", fill=PRIMARY, font_size=7)
    draw_arrow_down(d, 230, 50, 38)
    draw_box(d, 150, 10, 160, 28, "Success 200\nResponse", fill=HexColor('#059669'), font_size=7)

    return d

def sequence_diagram():
    d = Drawing(460, 300)
    accent = PRIMARY
    dark = DARK

    headers = ["Client", "API Gateway", "Auth", "Backend", "Database"]
    x_positions = [40, 120, 200, 280, 370]
    for i, (header, x) in enumerate(zip(headers, x_positions)):
        draw_box(d, x, 270, 70, 24, header, fill=HexColor('#1E40AF'), font_size=7)
        d.add(Line(x + 35, 270, x + 35, 20, strokeColor=HexColor('#94A3B8'), strokeWidth=0.5, strokeDashArray=[2, 2]))

    steps = [
        (0, 1, "POST /login"),
        (1, 2, "Verify JWT"),
        (2, 1, "Token Valid"),
        (1, 3, "Forward Request"),
        (3, 4, "SELECT * FROM users"),
        (4, 3, "User Data"),
        (3, 1, "Response JSON"),
        (1, 0, "200 OK + Token"),
    ]
    y_start = 250
    y_gap = 25
    for i, (from_idx, to_idx, label) in enumerate(steps):
        y = y_start - i * y_gap
        x1 = x_positions[from_idx] + 35
        x2 = x_positions[to_idx] + 35
        d.add(Line(x1, y, x2, y, strokeColor=accent, strokeWidth=1))
        d.add(Polygon([x2-4 if x2 > x1 else x2+4, y-3, x2-4 if x2 > x1 else x2+4, y+3, x2, y],
                       fillColor=accent, strokeColor=accent))
        mid_x = (x1 + x2) / 2
        s = String(mid_x, y + 4, label, fontSize=6, fillColor=SLATE, textAnchor='middle', fontName='Helvetica')
        d.add(s)

    return d

def methodology_diagram():
    phases = [
        ("Phase 1\nFoundations", HexColor('#1E40AF')),
        ("Phase 2\nIndia Workflow", HexColor('#0E7490')),
        ("Phase 3\nIP Screening", HexColor('#7C3AED')),
        ("Phase 4\nMultilingual", HexColor('#059669')),
        ("Phase 5\nCross-Jurisdiction", HexColor('#D97706')),
        ("Phase 6\nSimulator", HexColor('#B91C1C')),
        ("Phase 7\nEvaluation", HexColor('#365314')),
        ("Phase 8\nExpansion", HexColor('#475569')),
    ]
    return pipeline_diagram("Methodology", phases, width=460)

def project_structure_diagram():
    d = Drawing(460, 400)
    accent = PRIMARY
    dark = DARK

    draw_box(d, 150, 370, 160, 24, "IP-SAKTI Sahayak", fill=PRIMARY, font_size=8)

    branches = [
        (60, 320, "Frontend\nNext.js 14", HexColor('#1E40AF')),
        (180, 320, "Backend\nFastAPI", HexColor('#0E7490')),
        (300, 320, "Database\nPostgreSQL", HexColor('#059669')),
        (60, 260, "AI Engine\nRAG + FAISS", HexColor('#7C3AED')),
        (180, 260, "Auth\nJWT", HexColor('#B91C1C')),
        (300, 260, "Knowledge\nBase", HexColor('#D97706')),
    ]
    for x, y, label, fill in branches:
        draw_box(d, x, y, 100, 36, label, fill=fill, font_size=7)
        d.add(Line(230, 370, x + 50, y + 36, strokeColor=accent, strokeWidth=0.8))

    sub_branches = [
        (20, 200, "Login", HexColor('#1E40AF')),
        (100, 200, "Dashboard", HexColor('#1E40AF')),
        (180, 200, "Passport", HexColor('#1E40AF')),
        (260, 200, "Copilot", HexColor('#1E40AF')),
        (340, 200, "Analysis", HexColor('#1E40AF')),
    ]
    for x, y, label, fill in sub_branches:
        draw_box(d, x, y, 70, 24, label, fill=fill, font_size=6.5)
        d.add(Line(110, 320, x + 35, y + 24, strokeColor=HexColor('#94A3B8'), strokeWidth=0.5))

    sub_branches2 = [
        (20, 140, "API Routes", HexColor('#0E7490')),
        (100, 140, "Services", HexColor('#0E7490')),
        (180, 140, "Models", HexColor('#0E7490')),
        (260, 140, "RAG", HexColor('#0E7490')),
        (340, 140, "Auth", HexColor('#0E7490')),
    ]
    for x, y, label, fill in sub_branches2:
        draw_box(d, x, y, 70, 24, label, fill=fill, font_size=6.5)
        d.add(Line(230, 320, x + 35, y + 24, strokeColor=HexColor('#94A3B8'), strokeWidth=0.5))

    return d

def user_journey_table():
    data = [
        [Paragraph('<b>User Goal</b>', table_header_style), Paragraph('<b>User Action</b>', table_header_style),
         Paragraph('<b>System Response</b>', table_header_style), Paragraph('<b>Backend Process</b>', table_header_style),
         Paragraph('<b>AI Process</b>', table_header_style), Paragraph('<b>DB Action</b>', table_header_style)],
        [Paragraph('Create Account', table_cell_style), Paragraph('Fill signup form', table_cell_style),
         Paragraph('OTP sent to email', table_cell_style), Paragraph('Validate + hash password', table_cell_style),
         Paragraph('—', table_cell_style), Paragraph('INSERT user', table_cell_style)],
        [Paragraph('Login', table_cell_style), Paragraph('Enter credentials', table_cell_style),
         Paragraph('JWT token issued', table_cell_style), Paragraph('Verify + generate token', table_cell_style),
         Paragraph('—', table_cell_style), Paragraph('SELECT user', table_cell_style)],
        [Paragraph('Create Passport', table_cell_style), Paragraph('Fill 4-step form', table_cell_style),
         Paragraph('Passport created', table_cell_style), Paragraph('Canonicalize botanicals', table_cell_style),
         Paragraph('Language detection', table_cell_style), Paragraph('INSERT passport', table_cell_style)],
        [Paragraph('Upload Document', table_cell_style), Paragraph('Upload PDF/image', table_cell_style),
         Paragraph('Text extracted', table_cell_style), Paragraph('Sandbox + sanitize', table_cell_style),
         Paragraph('OCR + parse', table_cell_style), Paragraph('INSERT upload', table_cell_style)],
        [Paragraph('Query AI Copilot', table_cell_style), Paragraph('Ask question', table_cell_style),
         Paragraph('Answer + sources', table_cell_style), Paragraph('Route to RAG', table_cell_style),
         Paragraph('Retrieve + generate', table_cell_style), Paragraph('SELECT chunks', table_cell_style)],
        [Paragraph('View Analysis', table_cell_style), Paragraph('Click analysis', table_cell_style),
         Paragraph('Scores + findings', table_cell_style), Paragraph('Evaluate rules', table_cell_style),
         Paragraph('Confidence scoring', table_cell_style), Paragraph('SELECT findings', table_cell_style)],
        [Paragraph('Export Dossier', table_cell_style), Paragraph('Click export', table_cell_style),
         Paragraph('PDF downloaded', table_cell_style), Paragraph('Compile report', table_cell_style),
         Paragraph('—', table_cell_style), Paragraph('SELECT all', table_cell_style)],
    ]
    return make_table(data, [0.8*inch, 0.9*inch, 0.9*inch, 1.0*inch, 0.9*inch, 0.8*inch])

def future_scope_table():
    data = [
        [Paragraph('<b>Area</b>', table_header_style), Paragraph('<b>Enhancement</b>', table_header_style), Paragraph('<b>Priority</b>', table_header_style)],
        [Paragraph('Scalability', table_cell_style), Paragraph('Microservices + Kubernetes', table_cell_style), Paragraph('High', table_cell_style)],
        [Paragraph('AI Improvements', table_cell_style), Paragraph('Fine-tuned Ayurveda LLM', table_cell_style), Paragraph('High', table_cell_style)],
        [Paragraph('Mobile App', table_cell_style), Paragraph('React Native + offline sync', table_cell_style), Paragraph('Medium', table_cell_style)],
        [Paragraph('Analytics', table_cell_style), Paragraph('Advanced dashboards + reports', table_cell_style), Paragraph('Medium', table_cell_style)],
        [Paragraph('Enterprise', table_cell_style), Paragraph('Multi-tenant + SSO + audit', table_cell_style), Paragraph('High', table_cell_style)],
        [Paragraph('Integrations', table_cell_style), Paragraph('Patent office APIs + FSSAI', table_cell_style), Paragraph('Medium', table_cell_style)],
        [Paragraph('Voice', table_cell_style), Paragraph('Full voice-based interaction', table_cell_style), Paragraph('Low', table_cell_style)],
    ]
    return make_table(data, [1.2*inch, 3.5*inch, 0.8*inch])

# BUILD DOCUMENT
elements.append(Spacer(1, 60))
elements.append(Paragraph("IP-SAKTI Sahayak", title_style))
elements.append(Paragraph("Complete Software Project Documentation", subtitle_style))
elements.append(Paragraph("Ayurveda IP & Regulatory Decision Engine", subtitle_style))
elements.append(Spacer(1, 20))
elements.append(Paragraph("Version 1.0 | September 2026", ParagraphStyle('Ver', parent=body_style, alignment=TA_CENTER, textColor=SLATE)))
elements.append(Spacer(1, 40))
elements.append(Paragraph("Prepared for: SIH / Hackathon / Engineering Project Report", ParagraphStyle('Prep', parent=body_style, alignment=TA_CENTER, textColor=SLATE)))
elements.append(PageBreak())

# 1. Executive Summary
h1("1. Executive Summary")
h2("1.1 Project Overview")
p("IP-SAKTI Sahayak is a multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes. The system guides Ayurveda researchers, startups, students, MSMEs, and patent professionals from Idea → Innovation Passport → Patent Analysis → Compliance → Commercialization.")
h2("1.2 Problem Statement")
p("Indian pharmaceutical and biotech MSMEs file patents at a low rate (~16%) despite high trademark registration (~61%), citing procedural complexity, high legal fees, and lack of cross-border regulatory clarity as primary bottlenecks. Generic LLMs exhibit 69-88% hallucination rate on verifiable legal queries.")
h2("1.3 Proposed Solution")
p("A citation-grounded decision-support system that prevents hallucinations by decoupling legal logic from language models. The LLM never classifies law — deterministic rule packs do. Every statement is anchored to a statutory passage.")
h2("1.4 Key Features")
bullet("Multilingual formulation input (10 languages)")
bullet("Botanical canonicalization (हरिद्रा → Curcuma longa)")
bullet("Innovation Passport (4-section with QR)")
bullet("Patent Readiness scoring (Novelty / Inventive Step)")
bullet("AI Copilot with RAG-grounded citations")
bullet("Claim Firewall (label analysis)")
bullet("FTO Check (patent metadata simulation)")
bullet("Regulatory Roadmap (6-phase timeline)")
bullet("Dossier Export (HTML report with QR)")
h2("1.5 Expected Impact")
p("Empower 10,000+ Ayurveda MSMEs and researchers to navigate IP and regulatory pathways with confidence, reducing legal consultation costs by an estimated 60% and accelerating time-to-market for Ayurvedic innovations.")
elements.append(PageBreak())

# 2. Problem Statement
h1("2. Problem Statement")
h2("2.1 Existing Problems")
bullet("Low patent filing rate (~16%) among Indian MSMEs despite high innovation")
bullet("Procedural complexity in IP and regulatory compliance")
bullet("High legal fees for patent and regulatory consultation")
bullet("Lack of cross-border regulatory clarity (India, US, Canada)")
bullet("Language barriers — most legal resources available only in English")
h2("2.2 Current Limitations")
bullet("Generic LLMs hallucinate 69-88% on legal queries")
bullet("No unified platform for Ayurveda-specific IP guidance")
bullet("Traditional Knowledge (TK) prior art not easily searchable")
bullet("No multilingual support for regional language users")
h2("2.3 Why Existing Solutions Fail")
bullet("Generic AI tools lack domain-specific grounding")
bullet("Legal tech tools are expensive and not Ayurveda-focused")
bullet("No system combines patent analysis + regulatory compliance + multilingual support")
bullet("Existing RAG systems lack citation validation and abstention mechanisms")
h2("2.4 Real-World Use Cases")
bullet("MSME wants to patent a novel Ayurvedic formulation")
bullet("Startup needs to export herbal product to US/Canada")
bullet("Researcher validating novelty of herbal extract modification")
bullet("Incubator triaging 50+ startup IP cases")
elements.append(PageBreak())

# 3. Objectives
h1("3. Objectives")
h2("3.1 Primary Objectives")
bullet("Build a multilingual AI assistant for Ayurveda IP and regulatory guidance")
bullet("Achieve <5% Unsupported Claim Rate (UCR) on all generated findings")
bullet("Support 10 Indic languages with <3% language-parity gap")
bullet("Provide deterministic, auditable rule evaluation (zero hallucination)")
bullet("Deliver citation-grounded answers with clickable statutory passages")
h2("3.2 Secondary Objectives")
bullet("Create What-If Simulator for claim mutation analysis")
bullet("Build \"Challenge My Innovation\" Red-Team module")
bullet("Implement Living Regulatory-Diff notification service")
bullet("Enable Institutional multi-tenancy for incubators")
h2("3.3 Success Metrics")
bullet("Jurisdiction & Classification Accuracy > 98%")
bullet("Unsupported Claim Rate (UCR) < 1.5%")
bullet("p95 Latency < 12s (cached), < 45s (fresh RAG)")
bullet("Cache-Hit Rate >= 85%")
bullet("Language-Parity Gap <= 0.03")
elements.append(PageBreak())

# 4. Complete Methodology
h1("4. Complete Methodology")
p("The development roadmap is structured into 8 distinct phases:")
elements.append(methodology_diagram())
caption("Figure 4.1: 8-Phase Development Methodology")
sp()

h2("Phase 1 – Foundations & Architecture")
bullet("Pydantic models for InnovationPassport, Fact, Rule, Finding, EvidenceLink")
bullet("Ingestion of primary statutory gazettes (Drugs & Cosmetics Act 1940, FSSAI 2022, Patents Act 1970)")
bullet("API Monograph database for top Ayurvedic botanicals")
bullet("Modular monolith folder layout for backend/ and frontend/")
h2("Phase 2 – India Text Workflow")
bullet("Deterministic evaluation for India ASU Drug (Classical vs Proprietary)")
bullet("Ingredient legality check against FSSAI Ayurveda Aahara positive list")
bullet("Evidence-Gap action checklist with dependency-ordered tasks")
h2("Phase 3 – IP & TK Screening & Citation Gate")
bullet("Formulation fingerprinting comparing canonical botanical ratios against prior art")
bullet("4-Band Confidence & Abstention framework")
bullet("Unsupported Claim Rate (UCR) gatekeeper")
h2("Phase 4 – Multilingual Interaction")
bullet("Core validated workflows for English, Hindi, Marathi")
bullet("Multi-script botanical dictionary (Tamil, Telugu, Kannada, Bengali, Gujarati, Malayalam, Sanskrit)")
bullet("Code-switching detection and botanical entity normalization")
h2("Phase 5 – Cross-Jurisdiction Comparison")
bullet("US FDA DSHEA classifier (Dietary Supplement vs New Drug)")
bullet("Health Canada NHPR evaluator (Product License vs Site License)")
bullet("Per-ingredient legality checks (FDA NDI / NHPID)")
h2("Phase 6 – What-If Simulator & Red-Team")
bullet("Live mutation DAG cloner with instant diffs")
bullet("Examiner-style objections (Section 3(p) TK vulnerabilities)")
bullet("Traceable Decision Workspace (\"Why?\" Provenance View)")
h2("Phase 7 – Evaluation Suite")
bullet("30+ gold standard multi-language cases")
bullet("Ablation comparison (LLM-only vs Basic RAG vs Full)")
bullet("Prompt-injection red-team testing")
h2("Phase 8 – Expansion & Multi-Tenancy")
bullet("Institutional Incubator Dashboard")
bullet("Living Regulatory-Diff & Notification Service")
bullet("Expert Handoff bridge with DPDP consent")
elements.append(PageBreak())

# 5. Hierarchical Project Structure
h1("5. Hierarchical Project Structure")
elements.append(project_structure_diagram())
caption("Figure 5.1: Hierarchical Project Structure")
sp()

h2("5.1 Tree View")
p("""IP-SAKTI Sahayak
├── Frontend (Next.js 14)
│   ├── app/ (Pages: dashboard, login, passport, analysis)
│   ├── components/ (UI components)
│   ├── lib/ (API clients, auth, i18n)
│   └── types/ (TypeScript types)
├── Backend (FastAPI)
│   ├── api/v1/ (All API route handlers)
│   ├── auth/ (JWT + password hashing)
│   ├── rag/ (FAISS index & retriever)
│   ├── models/ (Pydantic + SQLAlchemy models)
│   ├── services/ (Business logic engines)
│   └── knowledge/ (Ayurveda datasets)
├── Database
│   ├── Users
│   ├── Passports
│   ├── Ingredients
│   ├── Findings
│   ├── Citations
│   └── Rules
├── AI Engine
│   ├── Embedding (BGE-base-en-v1.5)
│   ├── FAISS Index
│   ├── RAG Retriever
│   └── LLM Generator
└── Infrastructure
    ├── Docker Compose
    ├── PostgreSQL
    └── Redis (optional)""")
elements.append(PageBreak())

# 6. Complete User Flow
h1("6. Complete User Flow")
elements.append(user_flow_diagram())
caption("Figure 6.1: End-to-End User Flow")
sp()

h2("6.1 Step-by-Step Explanation")
bullet("<b>Landing Page:</b> User arrives at the app, sees hero section with multilingual support")
bullet("<b>Sign Up / Login:</b> User creates account or logs in with existing credentials")
bullet("<b>OTP Verification:</b> Email/phone OTP verification for security")
bullet("<b>Dashboard:</b> Overview cards (Passport, Patent Readiness, Evidence, Next Action)")
bullet("<b>Innovation Passport:</b> 4-step form (basic info → formulation → process → claims)")
bullet("<b>Document Upload:</b> Upload PDF/DOCX/images for extraction and analysis")
bullet("<b>AI Copilot:</b> Ask questions, receive RAG-grounded answers with citations")
bullet("<b>Patent Analysis:</b> View Novelty / Inventive Step / Overall scores")
bullet("<b>Regulatory Roadmap:</b> 6-phase timeline for compliance")
bullet("<b>Claim Firewall:</b> Analyze label copy for compliance risks")
bullet("<b>Dossier Export:</b> Generate and download comprehensive report")
h2("6.2 Alternate Flows")
h3("Login Failure")
bullet("Invalid credentials → Error message → Retry or Forgot Password")
bullet("Account locked after 5 attempts → 30-minute cooldown")
h3("Network Failure")
bullet("Request timeout → Retry with exponential backoff")
bullet("Offline mode → Queue requests in IndexedDB → Sync when online")
h3("Invalid Input")
bullet("Validation errors → Inline field errors → Highlight problematic fields")
bullet("Missing required facts → Clarification prompt with specific questions")
h3("Session Expiry")
bullet("JWT expired → 401 response → Refresh token attempt")
bullet("Refresh failed → Redirect to login with message")
elements.append(PageBreak())

# 7. User Journey Map
h1("7. User Journey Map")
elements.append(user_journey_table())
caption("Table 7.1: Complete User Journey Map")
elements.append(PageBreak())

# 8. Complete Pipeline
h1("8. Complete Pipeline")
h2("8.1 Overall Pipeline")
overall = [
    ("User", HexColor('#1E40AF')),
    ("Frontend", HexColor('#0E7490')),
    ("API Gateway", HexColor('#7C3AED')),
    ("Authentication", HexColor('#B91C1C')),
    ("Backend", HexColor('#059669')),
    ("Database", HexColor('#D97706')),
    ("AI Engine", HexColor('#0F172A')),
    ("Response", HexColor('#365314')),
]
elements.append(vertical_flow_diagram("Overall Pipeline", overall, width=460, node_h=26, gap=14))
caption("Figure 8.1: Overall System Pipeline")
sp()

h2("8.2 Data Pipeline")
data_pipe = [
    ("Input", HexColor('#1E40AF')),
    ("Validation", HexColor('#0E7490')),
    ("Cleaning", HexColor('#7C3AED')),
    ("Processing", HexColor('#059669')),
    ("Storage", HexColor('#D97706')),
    ("Analytics", HexColor('#B91C1C')),
    ("Output", HexColor('#365314')),
]
elements.append(vertical_flow_diagram("Data Pipeline", data_pipe, width=460, node_h=26, gap=14))
caption("Figure 8.2: Data Pipeline")
sp()

h2("8.3 AI Pipeline")
elements.append(ai_pipeline_diagram())
caption("Figure 8.3: AI Processing Pipeline")
sp()

h2("8.4 Security Pipeline")
elements.append(security_diagram())
caption("Figure 8.4: Security Pipeline")
elements.append(PageBreak())

# 9. System Architecture
h1("9. System Architecture")
h2("9.1 High-Level Architecture")
elements.append(architecture_diagram())
caption("Figure 9.1: High-Level System Architecture")
sp()

h2("9.2 Component Architecture")
p("The system follows a modular monolith architecture with clear separation of concerns:")
bullet("<b>Presentation Layer:</b> Next.js 14 with App Router, TypeScript, Tailwind CSS")
bullet("<b>API Layer:</b> FastAPI with Pydantic v2 validation, Swagger documentation")
bullet("<b>Service Layer:</b> Business logic engines (Rule Engine, Botanical Resolver, Verification)")
bullet("<b>Data Layer:</b> PostgreSQL with SQLAlchemy ORM, FAISS vector index")
bullet("<b>AI Layer:</b> BGE embeddings, hybrid RAG retrieval, LLM explanation generation")
h2("9.3 Client-Server Architecture")
p("The frontend communicates with the backend exclusively through REST APIs. All AI processing, database operations, and business logic reside on the backend. The frontend is a clean client layer with zero server-side secrets.")
h2("9.4 AI Integration Architecture")
p("The AI layer is decoupled from the decision layer. The LLM never classifies law — it only explains results grounded in retrieved passages. This prevents hallucinations and ensures every output is auditable.")
h2("9.5 Deployment Architecture")
p("Docker Compose orchestrates three services: PostgreSQL 15, FastAPI backend, and Next.js frontend. All services communicate over an internal Docker network. The system degrades gracefully to SQLite and keyword retrieval if PostgreSQL or FAISS are unavailable.")
elements.append(PageBreak())

# 10. Backend Workflow
h1("10. Backend Workflow")
h2("10.1 Request Lifecycle")
elements.append(sequence_diagram())
caption("Figure 10.1: API Request Sequence Diagram")
sp()

h2("10.2 API Communication")
p("All API communication follows REST conventions with JSON payloads. The backend exposes endpoints under /api/v1/ with Swagger documentation at /api/v1/docs.")
h2("10.3 Authentication Flow")
p("JWT-based authentication with access tokens (15-min expiry) and refresh tokens (7-day expiry). Passwords hashed with bcrypt. DPDP consent logged for every authenticated session.")
h2("10.4 Database Queries")
p("SQLAlchemy ORM provides type-safe database operations. The system supports PostgreSQL (production) and SQLite (fallback). All queries use parameterized statements to prevent SQL injection.")
h2("10.5 Error Handling")
p("Structured error responses with HTTP status codes, error codes, and human-readable messages. All errors are logged with request ID for traceability.")
elements.append(PageBreak())

# 11. Frontend Workflow
h1("11. Frontend Workflow")
h2("11.1 Page Routing")
bullet("/ — Landing page")
bullet("/login — Login page")
bullet("/signup — Registration page")
bullet("/dashboard — Main dashboard")
bullet("/passport — Innovation Passport builder")
bullet("/analysis — Patent analysis view")
bullet("/copilot — AI Copilot chat")
bullet("/roadmap — Regulatory roadmap")
bullet("/export — Dossier export")
h2("11.2 State Management")
p("React Context API for global state (auth, language, theme). Local component state for form data. React Query for server state caching and synchronization.")
h2("11.3 API Calls")
p("Centralized API client in lib/api.ts with automatic token injection, error handling, and retry logic. All requests include JWT bearer token in Authorization header.")
h2("11.4 Loading States")
p("Skeleton screens for page loads, spinners for button actions, and streaming responses for AI Copilot. Optimistic updates for better perceived performance.")
h2("11.5 Error States")
p("Inline form validation errors, toast notifications for API errors, and dedicated error pages for 404/500. Graceful degradation when backend is unavailable.")
elements.append(PageBreak())

# 12. Database Design
h1("12. Database Design")
h2("12.1 ER Diagram")
elements.append(er_diagram())
caption("Figure 12.1: Entity-Relationship Diagram")
sp()

h2("12.2 Tables")
h3("users")
bullet("id (UUID, PK)")
bullet("email (VARCHAR, UNIQUE)")
bullet("password_hash (VARCHAR)")
bullet("role (ENUM: innovator, researcher, admin)")
bullet("created_at (TIMESTAMP)")
h3("passports")
bullet("id (UUID, PK)")
bullet("user_id (UUID, FK → users.id)")
bullet("case_title (VARCHAR)")
bullet("product_form (VARCHAR)")
bullet("dosage_form (VARCHAR)")
bullet("intended_use (TEXT)")
bullet("version (INTEGER)")
h3("ingredients")
bullet("id (UUID, PK)")
bullet("passport_id (UUID, FK → passports.id)")
bullet("common_name (VARCHAR)")
bullet("botanical_name (VARCHAR)")
bullet("api_monograph_id (VARCHAR)")
bullet("plant_part (VARCHAR)")
bullet("quantity_percentage (FLOAT)")
h3("findings")
bullet("id (UUID, PK)")
bullet("passport_id (UUID, FK → passports.id)")
bullet("jurisdiction (VARCHAR)")
bullet("pathway_category (VARCHAR)")
bullet("status (ENUM: satisfied, not_satisfied, insufficient)")
bullet("confidence (ENUM: high, medium, low, abstain)")
h3("citations")
bullet("id (UUID, PK)")
bullet("finding_id (UUID, FK → findings.id)")
bullet("act_title (VARCHAR)")
bullet("section_reference (VARCHAR)")
bullet("authority (VARCHAR)")
bullet("exact_passage (TEXT)")
h3("rules")
bullet("id (UUID, PK)")
bullet("jurisdiction (VARCHAR)")
bullet("rule_pack (YAML)")
bullet("version (INTEGER)")
bullet("effective_date (DATE)")
elements.append(PageBreak())

# 13. API Flow
h1("13. API Flow")
h2("13.1 API Lifecycle")
p("Every API endpoint follows a consistent lifecycle: Request → Validation → Authentication → Processing → Database → Response")
h2("13.2 Endpoints")
api_data = [
    [Paragraph('<b>Endpoint</b>', table_header_style), Paragraph('<b>Method</b>', table_header_style), Paragraph('<b>Purpose</b>', table_header_style)],
    [Paragraph('/api/v1/auth/signup', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Create account', table_cell_style)],
    [Paragraph('/api/v1/auth/login', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Login, returns JWT', table_cell_style)],
    [Paragraph('/api/v1/auth/profile', table_cell_style), Paragraph('GET', table_cell_style), Paragraph('Current user profile', table_cell_style)],
    [Paragraph('/api/v1/passport/create', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Create Innovation Passport', table_cell_style)],
    [Paragraph('/api/v1/passport/{id}/update', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Update passport', table_cell_style)],
    [Paragraph('/api/v1/formulation/parse', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Parse multilingual formulation', table_cell_style)],
    [Paragraph('/api/v1/botanical/canonicalize', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Map to API botanical name', table_cell_style)],
    [Paragraph('/api/v1/chat/query', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('AI Copilot (RAG answer + sources)', table_cell_style)],
    [Paragraph('/api/v1/fto/check', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Freedom-to-Operate analysis', table_cell_style)],
    [Paragraph('/api/v1/label/analyze', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Claim Firewall / label analysis', table_cell_style)],
    [Paragraph('/api/v1/analysis/readiness/{id}', table_cell_style), Paragraph('GET', table_cell_style), Paragraph('Patent readiness scores', table_cell_style)],
    [Paragraph('/api/v1/roadmap/{id}', table_cell_style), Paragraph('GET', table_cell_style), Paragraph('Regulatory roadmap', table_cell_style)],
    [Paragraph('/api/v1/export/dossier', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Generate exportable dossier', table_cell_style)],
    [Paragraph('/api/v1/upload/disclosure-check', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Upload & scan documents', table_cell_style)],
    [Paragraph('/api/v1/assessment/evaluate', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Regulatory assessment', table_cell_style)],
    [Paragraph('/api/v1/what-if/simulate', table_cell_style), Paragraph('POST', table_cell_style), Paragraph('Claim mutation simulation', table_cell_style)],
    [Paragraph('/api/v1/evidence/{id}', table_cell_style), Paragraph('GET', table_cell_style), Paragraph('Evidence gaps summary', table_cell_style)],
]
elements.append(make_table(api_data, [2.2*inch, 0.6*inch, 2.7*inch]))
caption("Table 13.1: Complete API Reference")
elements.append(PageBreak())

# 14. Authentication Flow
h1("14. Authentication Flow")
elements.append(auth_flow_diagram())
caption("Figure 14.1: Authentication Flow")
sp()

h2("14.1 Registration")
bullet("User fills signup form (name, email, password)")
bullet("System validates input and checks for existing email")
bullet("Password hashed with bcrypt")
bullet("User record created in database")
bullet("OTP sent to email for verification")
h2("14.2 OTP Verification")
bullet("User enters 6-digit OTP")
bullet("System verifies OTP against stored hash")
bullet("Account marked as verified")
bullet("User redirected to login")
h2("14.3 Login")
bullet("User enters email and password")
bullet("System verifies credentials")
bullet("JWT access token (15 min) + refresh token (7 days) generated")
bullet("Tokens returned to client")
h2("14.4 Token Refresh")
bullet("When access token expires, client sends refresh token")
bullet("System validates refresh token")
bullet("New access token issued")
h2("14.5 Logout")
bullet("Client discards tokens")
bullet("Server blacklists refresh token")
bullet("Session terminated")
elements.append(PageBreak())

# 15. Admin Flow
h1("15. Admin Flow")
h2("15.1 Admin Capabilities")
bullet("<b>Login:</b> Admin logs in with elevated credentials")
bullet("<b>Manage Users:</b> View, suspend, or delete user accounts")
bullet("<b>Review Reports:</b> Access all generated dossiers and analyses")
bullet("<b>Approve Requests:</b> Approve or reject expert handoff requests")
bullet("<b>View Analytics:</b> System-wide usage metrics and compliance analytics")
bullet("<b>Manage Rules:</b> Update versioned rule packs")
bullet("<b>Monitor System:</b> Health checks, error logs, performance metrics")
h2("15.2 Admin Dashboard")
p("The admin dashboard provides a multi-tenant view with cohort analytics, reviewer assignment queues, and aggregate compliance metrics across all cases.")
elements.append(PageBreak())

# 16. AI Workflow
h1("16. AI Workflow")
h2("16.1 Data Collection")
bullet("Statutory gazettes (Drugs & Cosmetics Act, FSSAI, Patents Act)")
bullet("API Monographs for Ayurvedic botanicals")
bullet("Traditional Knowledge Digital Library (TKDL) prior art")
bullet("PubMed research papers")
bullet("WHO and AYUSH guidelines")
h2("16.2 Preprocessing")
bullet("Document chunking (800 tokens, 150 overlap)")
bullet("Metadata extraction (source, section, date)")
bullet("Text normalization and cleaning")
bullet("Language detection for multilingual content")
h2("16.3 Embedding")
bullet("BAAI/bge-base-en-v1.5 via Sentence Transformers")
bullet("Dense vector representations")
bullet("FAISS flat index for fast similarity search")
h2("16.4 Model Inference")
bullet("Query embedding generation")
bullet("Top-5 chunk retrieval")
bullet("LLM generation with strict passage grounding")
bullet("Citation attachment to every statement")
h2("16.5 Confidence Score")
bullet("6-signal weighted composite (retrieval, citation, entailment, authority, diversity, rule)")
bullet("4-band calibration (High, Medium, Low, Abstain)")
bullet("UCR gate (<5% threshold)")
h2("16.6 Output Generation")
bullet("Structured findings matrix")
bullet("Clickable statutory citations")
bullet("Multilingual explanation")
bullet("QR-coded dossier export")
h2("16.7 Feedback Loop")
bullet("User feedback on answer quality")
bullet("Active learning register")
bullet("Reviewer disagreement tracking")
bullet("Continuous model improvement")
elements.append(PageBreak())

# 17. Exception Flow
h1("17. Exception Flow")
elements.append(decision_tree_diagram())
caption("Figure 17.1: Exception Handling Decision Tree")
sp()

h2("17.1 Invalid Input")
bullet("Pydantic validation catches malformed requests")
bullet("422 Unprocessable Entity returned")
bullet("Field-specific error messages provided")
bullet("User prompted to correct input")
h2("17.2 Server Error")
bullet("Unhandled exceptions caught by middleware")
bullet("500 Internal Server Error returned")
bullet("Error logged with stack trace")
bullet("User sees generic error message")
h2("17.3 API Timeout")
bullet("Request timeout after 45 seconds")
bullet("504 Gateway Timeout returned")
bullet("Client retries with exponential backoff")
bullet("Circuit breaker pattern for repeated failures")
h2("17.4 Database Failure")
bullet("PostgreSQL unavailable → SQLite fallback")
bullet("Connection pool exhaustion → Queue requests")
bullet("Transaction rollback on error")
bullet("Data integrity maintained via ACID")
h2("17.5 Network Failure")
bullet("Frontend detects offline status")
bullet("Requests queued in IndexedDB")
bullet("Sync when connection restored")
bullet("Conflict resolution via timestamps")
h2("17.6 Unauthorized Access")
bullet("Missing/invalid JWT → 401 Unauthorized")
bullet("Insufficient permissions → 403 Forbidden")
bullet("Rate limit exceeded → 429 Too Many Requests")
bullet("All attempts logged for security audit")
elements.append(PageBreak())

# 18. Security Architecture
h1("18. Security Architecture")
h2("18.1 Encryption")
bullet("TLS 1.3 for all communications")
bullet("bcrypt for password hashing")
bullet("AES-256 for data at rest")
h2("18.2 JWT")
bullet("Short-lived access tokens (15 min)")
bullet("Refresh token rotation")
bullet("Token blacklisting on logout")
h2("18.3 HTTPS")
bullet("Enforced HTTPS in production")
bullet("HSTS headers")
bullet("Secure cookie flags")
h2("18.4 Role-Based Access")
bullet("Innovator, Researcher, Admin roles")
bullet("Permission-based endpoint access")
bullet("Row-level security in database")
h2("18.5 Input Validation")
bullet("Pydantic v2 strict validation")
bullet("Regex sanitization for uploads")
bullet("Parameterized SQL queries")
h2("18.6 SQL Injection Protection")
bullet("SQLAlchemy ORM (no raw SQL)")
bullet("Parameterized statements only")
bullet("Input sanitization layer")
h2("18.7 XSS Protection")
bullet("React auto-escaping")
bullet("Content Security Policy headers")
bullet("Sanitized HTML rendering")
h2("18.8 Rate Limiting")
bullet("Per-user rate limits")
bullet("IP-based throttling")
bullet("Redis-backed distributed limiting")
elements.append(PageBreak())

# 19. Deployment Pipeline (CI/CD)
h1("19. Deployment Pipeline (CI/CD)")
elements.append(cicd_diagram())
caption("Figure 19.1: CI/CD Pipeline")
sp()

h2("19.1 Pipeline Stages")
bullet("<b>Developer:</b> Code pushed to feature branch")
bullet("<b>GitHub:</b> Pull request created, code review")
bullet("<b>Build:</b> Docker images built, dependencies installed")
bullet("<b>Testing:</b> Pytest unit tests, integration tests, linting")
bullet("<b>Deploy:</b> Docker Compose orchestration, rolling update")
bullet("<b>Cloud:</b> AWS ap-south-1 (Mumbai), data residency compliance")
bullet("<b>Monitor:</b> Health checks, log aggregation, alerting")
h2("19.2 Deployment Targets")
bullet("<b>Frontend:</b> Vercel / AWS S3 + CloudFront")
bullet("<b>Backend:</b> AWS ECS / Docker Compose")
bullet("<b>Database:</b> AWS RDS PostgreSQL")
bullet("<b>AI:</b> GPU-enabled instances for embedding generation")
elements.append(PageBreak())

# 20. Monitoring Pipeline
h1("20. Monitoring Pipeline")
elements.append(monitoring_diagram())
caption("Figure 20.1: Monitoring Pipeline")
sp()

h2("20.1 Logs")
bullet("Structured JSON logging")
bullet("Request/response logging with correlation IDs")
bullet("Error and exception logging")
bullet("Security event logging")
h2("20.2 Analytics")
bullet("User engagement metrics")
bullet("Feature usage tracking")
bullet("Performance metrics (latency, throughput)")
bullet("Error rate tracking")
h2("20.3 Error Tracking")
bullet("Real-time error alerts")
bullet("Stack trace capture")
bullet("Error grouping and deduplication")
bullet("Resolution tracking")
h2("20.4 Performance Monitoring")
bullet("p50, p95, p99 latency tracking")
bullet("Database query performance")
bullet("API endpoint response times")
bullet("Resource utilization (CPU, memory)")
h2("20.5 User Feedback")
bullet("In-app feedback forms")
bullet("Answer quality ratings")
bullet("Feature request tracking")
bullet("Bug report submission")
elements.append(PageBreak())

# 21. Technology Stack Diagram
h1("21. Technology Stack Diagram")
elements.append(tech_stack_diagram())
caption("Figure 21.1: Layered Technology Stack")
sp()

h2("21.1 Stack Summary")
stack_data = [
    [Paragraph('<b>Layer</b>', table_header_style), Paragraph('<b>Technology</b>', table_header_style), Paragraph('<b>Purpose</b>', table_header_style)],
    [Paragraph('Frontend', table_cell_style), Paragraph('Next.js 14, React 18, TypeScript', table_cell_style), Paragraph('UI, routing, state management', table_cell_style)],
    [Paragraph('Styling', table_cell_style), Paragraph('Tailwind CSS, Glassmorphism', table_cell_style), Paragraph('Responsive design, themes', table_cell_style)],
    [Paragraph('Backend', table_cell_style), Paragraph('FastAPI, Pydantic v2', table_cell_style), Paragraph('API, validation, async I/O', table_cell_style)],
    [Paragraph('Database', table_cell_style), Paragraph('PostgreSQL, SQLAlchemy', table_cell_style), Paragraph('Data persistence, ORM', table_cell_style)],
    [Paragraph('AI/ML', table_cell_style), Paragraph('BGE Embeddings, FAISS, RAG', table_cell_style), Paragraph('Retrieval, generation', table_cell_style)],
    [Paragraph('Auth', table_cell_style), Paragraph('JWT, bcrypt', table_cell_style), Paragraph('Authentication, security', table_cell_style)],
    [Paragraph('Infra', table_cell_style), Paragraph('Docker, AWS ap-south-1', table_cell_style), Paragraph('Deployment, hosting', table_cell_style)],
]
elements.append(make_table(stack_data, [1.0*inch, 2.5*inch, 2.0*inch]))
caption("Table 21.1: Technology Stack Summary")
elements.append(PageBreak())

# 22. Future Scope
h1("22. Future Scope")
elements.append(future_scope_table())
caption("Table 22.1: Future Enhancements Roadmap")
sp()

h2("22.1 Scalability")
bullet("Migrate to microservices architecture")
bullet("Kubernetes orchestration for auto-scaling")
bullet("Global CDN for static assets")
bullet("Multi-region deployment")
h2("22.2 AI Improvements")
bullet("Fine-tuned Ayurveda-specific LLM")
bullet("Graph RAG with Neo4j knowledge graph")
bullet("Agentic RAG with specialist agents")
bullet("Improved multilingual embeddings")
h2("22.3 Mobile App")
bullet("React Native cross-platform app")
bullet("Offline-first with IndexedDB sync")
bullet("Push notifications for regulatory updates")
bullet("Camera-based document scanning")
h2("22.4 Analytics")
bullet("Advanced cohort analytics")
bullet("Predictive compliance scoring")
bullet("Market opportunity assessment")
bullet("Competitive landscape analysis")
h2("22.5 Enterprise Features")
bullet("SSO/SAML integration")
bullet("Custom rule pack authoring")
bullet("API access for third-party integrations")
bullet("White-label deployment options")
elements.append(PageBreak())

# Closing
elements.append(Spacer(1, 40))
elements.append(Paragraph("— End of Document —", ParagraphStyle('EndDoc', parent=body_style, alignment=TA_CENTER, textColor=HexColor('#94A3B8'))))
elements.append(Spacer(1, 20))
elements.append(Paragraph("IP-SAKTI Sahayak | Ayurveda IP & Regulatory Decision Engine", ParagraphStyle('Footer', parent=body_style, alignment=TA_CENTER, textColor=SLATE, fontSize=8)))

doc = SimpleDocTemplate(OUTPUT_FILE, pagesize=A4,
                        leftMargin=MARGIN, rightMargin=MARGIN,
                        topMargin=MARGIN, bottomMargin=MARGIN)
doc.build(elements)
print(f"PDF created: {OUTPUT_FILE}")
