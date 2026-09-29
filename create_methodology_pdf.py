from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
import os

OUTPUT_DIR = r"C:\Users\adity\OneDrive\Pictures\Desktop\SIH Final\xyz"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "IP_SAKTI_Methodology.pdf")

os.makedirs(OUTPUT_DIR, exist_ok=True)

doc = SimpleDocTemplate(OUTPUT_FILE, pagesize=A4,
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

styles = getSampleStyleSheet()

title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                             fontSize=24, spaceAfter=30, alignment=TA_CENTER,
                             textColor=HexColor('#059669'), fontName='Helvetica-Bold')

h1_style = ParagraphStyle('CustomH1', parent=styles['Heading1'],
                          fontSize=18, spaceAfter=12, spaceBefore=20,
                          textColor=HexColor('#0F172A'), fontName='Helvetica-Bold')

h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'],
                          fontSize=14, spaceAfter=8, spaceBefore=12,
                          textColor=HexColor('#059669'), fontName='Helvetica-Bold')

h3_style = ParagraphStyle('CustomH3', parent=styles['Heading3'],
                          fontSize=12, spaceAfter=6, spaceBefore=8,
                          textColor=HexColor('#334155'), fontName='Helvetica-Bold')

body_style = ParagraphStyle('CustomBody', parent=styles['Normal'],
                            fontSize=10, spaceAfter=6, alignment=TA_JUSTIFY,
                            leading=14)

bullet_style = ParagraphStyle('CustomBullet', parent=styles['Normal'],
                              fontSize=10, spaceAfter=4, leftIndent=20,
                              bulletIndent=10, leading=13)

sub_bullet_style = ParagraphStyle('CustomSubBullet', parent=styles['Normal'],
                                  fontSize=9, spaceAfter=3, leftIndent=40,
                                  bulletIndent=30, leading=12,
                                  textColor=HexColor('#475569'))

elements = []

def add_heading(text, level=1):
    if level == 1:
        elements.append(Paragraph(text, h1_style))
    elif level == 2:
        elements.append(Paragraph(text, h2_style))
    elif level == 3:
        elements.append(Paragraph(text, h3_style))
    elements.append(Spacer(1, 6))

def add_paragraph(text):
    elements.append(Paragraph(text, body_style))

def add_bullet(text):
    elements.append(Paragraph(f"• {text}", bullet_style))

def add_sub_bullet(text):
    elements.append(Paragraph(f"  - {text}", sub_bullet_style))

def add_spacer(h=12):
    elements.append(Spacer(1, h))

def create_user_flow_diagram():
    d = Drawing(450, 600)

    box_w = 140
    box_h = 35
    x_start = 150
    y_start = 560
    gap = 50

    box_style = HexColor('#1E293B')
    text_color = white
    accent_color = HexColor('#10B981')

    nodes = [
        ("User Access\n(Login/Signup)", y_start),
        ("Dashboard\nOverview", y_start - gap),
        ("Innovation Passport\nIntake", y_start - 2*gap),
        ("Multilingual\nFormulation Input", y_start - 3*gap),
        ("Document Upload\n(PDF/DOCX/Images)", y_start - 4*gap),
        ("AI Copilot\n(RAG Query)", y_start - 5*gap),
        ("Patent Analysis\n& Readiness", y_start - 6*gap),
        ("Regulatory Roadmap\n& FTO Check", y_start - 7*gap),
        ("Claim Firewall\n& Label Analysis", y_start - 8*gap),
        ("Dossier Export\n& Report", y_start - 9*gap),
    ]

    for i, (label, y) in enumerate(nodes):
        rect = Rect(x_start - box_w/2, y - box_h/2, box_w, box_h,
                    fillColor=box_style, strokeColor=accent_color, strokeWidth=1.5)
        d.add(rect)
        s = String(x_start, y - 5, label, fontSize=8, fillColor=text_color,
                   textAnchor='middle', fontName='Helvetica-Bold')
        d.add(s)
        if i < len(nodes) - 1:
            line = Line(x_start, y - box_h/2, x_start, y - gap + box_h/2,
                       strokeColor=accent_color, strokeWidth=1.5)
            d.add(line)

    return d

def create_system_flow_diagram():
    d = Drawing(500, 700)

    accent = HexColor('#10B981')
    dark = HexColor('#1E293B')
    mid = HexColor('#334155')
    light = HexColor('#64748B')

    def draw_box(x, y, w, h, text, fill=dark, font_size=7):
        rect = Rect(x, y, w, h, fillColor=fill, strokeColor=accent, strokeWidth=1)
        d.add(rect)
        s = String(x + w/2, y + h/2 - 3, text, fontSize=font_size,
                   fillColor=white, textAnchor='middle', fontName='Helvetica-Bold')
        d.add(s)

    def draw_arrow(x1, y1, x2, y2):
        line = Line(x1, y1, x2, y2, strokeColor=accent, strokeWidth=1.2)
        d.add(line)

    draw_box(180, 660, 140, 30, "USER INPUT LAYER")
    draw_box(180, 620, 140, 30, "Multilingual UI (10 Languages)")
    draw_arrow(250, 660, 250, 650)

    draw_box(180, 570, 140, 30, "INPUT SANDBOXING")
    draw_box(180, 530, 140, 30, "Prompt-Injection Defense")
    draw_arrow(250, 620, 250, 600)
    draw_arrow(250, 570, 250, 560)

    draw_box(180, 480, 140, 30, "INNOVATION PASSPORT")
    draw_box(180, 440, 140, 30, "Fact Origin Tracker")
    draw_arrow(250, 530, 250, 510)
    draw_arrow(250, 480, 250, 470)

    draw_box(180, 390, 140, 30, "BOTANICAL RESOLVER")
    draw_box(180, 350, 140, 30, "Formulation Fingerprint")
    draw_arrow(250, 440, 250, 420)
    draw_arrow(250, 390, 250, 380)

    draw_box(180, 300, 140, 30, "RULE ENGINE (3-State)")
    draw_box(180, 260, 140, 30, "Jurisdiction Router")
    draw_arrow(250, 350, 250, 330)
    draw_arrow(250, 300, 250, 290)

    draw_box(180, 210, 140, 30, "HYBRID RAG RETRIEVAL")
    draw_box(180, 170, 140, 30, "BM25 + Dense + Rerank")
    draw_arrow(250, 260, 250, 240)
    draw_arrow(250, 210, 250, 200)

    draw_box(180, 120, 140, 30, "CITATION VALIDATOR")
    draw_box(180, 80, 140, 30, "UCR Gate (<5%)")
    draw_arrow(250, 170, 250, 150)
    draw_arrow(250, 120, 250, 110)

    draw_box(180, 30, 140, 30, "LLM EXPLANATION")
    draw_arrow(250, 80, 250, 60)

    draw_box(20, 300, 120, 30, "Knowledge Base", fill=mid)
    draw_box(20, 260, 120, 30, "Gazettes & Acts", fill=mid)
    draw_box(20, 220, 120, 30, "API Monographs", fill=mid)
    draw_box(20, 180, 120, 30, "TK Prior Art", fill=mid)
    draw_arrow(140, 315, 180, 225)
    draw_arrow(140, 275, 180, 225)
    draw_arrow(140, 235, 180, 225)
    draw_arrow(140, 195, 180, 225)

    draw_box(340, 300, 120, 30, "Verification Layer", fill=mid)
    draw_box(340, 260, 120, 30, "Claim Extractor", fill=mid)
    draw_box(340, 220, 120, 30, "Entailment Check", fill=mid)
    draw_box(340, 180, 120, 30, "Confidence Scorer", fill=mid)
    draw_arrow(320, 225, 340, 315)
    draw_arrow(320, 225, 340, 275)
    draw_arrow(320, 225, 340, 235)
    draw_arrow(320, 225, 340, 195)

    draw_box(340, 120, 120, 30, "Output Layer", fill=mid)
    draw_box(340, 80, 120, 30, "Findings Matrix", fill=mid)
    draw_box(340, 40, 120, 30, "Dossier Export", fill=mid)
    draw_arrow(400, 180, 400, 150)
    draw_arrow(400, 120, 400, 110)
    draw_arrow(400, 80, 400, 70)

    return d

elements.append(Paragraph("IP-SAKTI Sahayak", title_style))
elements.append(Paragraph("Project Methodology & System Architecture", title_style))
elements.append(Spacer(1, 20))

add_heading("1. Project Overview", 1)
add_paragraph(
    "IP-SAKTI Sahayak is a multilingual, RAG-based (source-cited) AI assistant for Intellectual "
    "Property and regulatory guidance in Ayurveda, across national and international regimes. "
    "The system guides Ayurveda researchers, startups, students, MSMEs, and patent professionals "
    "from Idea → Innovation Passport → Patent Analysis → Compliance → Commercialization."
)
add_spacer()

add_heading("2. Core System Invariant", 1)
add_paragraph(
    "The fundamental engineering philosophy is captured in the Core Invariant:"
)
add_paragraph(
    "<b>User Facts</b> → define → <b>Case</b> → evaluated by → <b>Deterministic Rules</b> → "
    "evidenced by → <b>Hybrid RAG Retrieval</b> → explained by → <b>Language Model</b>"
)
add_paragraph(
    "\"User facts define the case. Reviewed rules evaluate supported conditions. "
    "Retrieval supplies evidence. The language model explains the result — and never decides it.\""
)
add_spacer()

add_heading("3. Development Methodology (8-Phase Roadmap)", 1)

add_heading("Phase 1: Foundations & Architecture", 2)
add_paragraph("<b>Objective:</b> Establish foundational schemas, legal source inventory, and application structure.")
add_bullet("Pydantic models for InnovationPassport, Fact, Rule, Finding, EvidenceLink")
add_bullet("Ingestion of primary statutory gazettes (Drugs & Cosmetics Act 1940, FSSAI Ayurveda Aahara 2022, Patents Act 1970)")
add_bullet("API Monograph database for top Ayurvedic botanicals (Ashwagandha, Brahmi, Curcumin, Tulsi, Guggulu, Neem, Shatavari)")
add_bullet("Modular monolith folder layout for backend/ and frontend/")
add_spacer()

add_heading("Phase 2: India Text Workflow", 2)
add_paragraph("<b>Objective:</b> Complete end-to-end English workflow from intake to evidence-backed action plan for Indian regulatory pathways.")
add_bullet("Deterministic evaluation for India ASU Drug (Classical vs Proprietary) vs Ayurveda Aahara (Food)")
add_bullet("Ingredient legality check against FSSAI Ayurveda Aahara positive list")
add_bullet("Evidence-Gap action checklist with dependency-ordered tasks")
add_spacer()

add_heading("Phase 3: IP & Traditional Knowledge Screening & Citation Gate", 2)
add_paragraph("<b>Objective:</b> Implement patentability screening under Indian Patents Act Section 3(p) and citation validation.")
add_bullet("Formulation fingerprinting comparing canonical botanical ratios against prior art")
add_bullet("4-Band Confidence & Abstention framework (High, Medium, Low, Insufficient Evidence)")
add_bullet("Unsupported Claim Rate (UCR) gatekeeper ensuring every finding has a clickable statutory passage link")
add_spacer()

add_heading("Phase 4: Multilingual Interaction & Regional Language Search", 2)
add_paragraph("<b>Objective:</b> Native Indic language intake, normalization, and explanation generation with strict meaning preservation.")
add_bullet("Core validated workflows for English, Hindi, Marathi")
add_bullet("Multi-script botanical dictionary indexing vernacular plant names across Tamil, Telugu, Kannada, Bengali, Gujarati, Malayalam, Sanskrit")
add_bullet("Code-switching detection and botanical entity normalization")
add_bullet("Language-Parity release gate validation")
add_spacer()

add_heading("Phase 5: Cross-Jurisdiction Comparison (India, US, Canada)", 2)
add_paragraph("<b>Objective:</b> Multi-country side-by-side comparative analysis without translating foreign rules into local terms.")
add_bullet("US FDA DSHEA (21 CFR 101.93) classifier: Dietary Supplement vs Unapproved New Drug")
add_bullet("Health Canada NHPR evaluator: Product License (NPN) vs Site License")
add_bullet("Per-ingredient legality checks against US FDA NDI list and Health Canada NHPID monograph list")
add_bullet("Side-by-side comparison matrix with explicit coverage limitations")
add_spacer()

add_heading("Phase 6: Reactive What-If Simulator, Red-Team & Traceable Workspace", 2)
add_paragraph("<b>Objective:</b> Interactive decision-support tools empowering innovators before filing.")
add_bullet("What-If Simulator: Live mutation DAG cloner showing instant diffs when modifying claims or ingredients")
add_bullet("\"Challenge My Innovation\" Red-Team: Examiner-style objections identifying Section 3(p) TK vulnerabilities")
add_bullet("Traceable Decision Workspace (\"Why?\" View): Interactive graph linking Facts → Rules → Gazette Passages → Findings")
add_bullet("Voice intake simulation with transcript confirmation")
add_spacer()

add_heading("Phase 7: Evaluation Suite & Benchmark Verification", 2)
add_paragraph("<b>Objective:</b> Quantitative validation of system accuracy, groundedness, and security.")
add_bullet("Gold Standard case benchmark with 30+ validated multi-language cases")
add_bullet("Ablation comparison harness (LLM-only vs Basic RAG vs IP-SAKTI Full)")
add_bullet("Prompt-injection red-team testing suite for document uploads")
add_bullet("Full execution of the 10-step SIH Demonstration Script")
add_spacer()

add_heading("Phase 8: Expansion & Institutional Multi-Tenancy", 2)
add_paragraph("<b>Objective:</b> Advanced ecosystem integrations for incubators and regulatory agencies.")
add_bullet("Institutional Incubator Dashboard with multi-tenant case queues and cohort gap analytics")
add_bullet("Living Regulatory-Diff & Notification Service alerting users to statutory gazette amendments")
add_bullet("Expert Handoff bridge with DPDP Act-compliant consent and liability boundaries")
add_bullet("Offline-first draft intake with IndexedDB sync")
add_spacer()

add_heading("4. Technology Stack", 1)

tech_data = [
    ['Layer', 'Technology', 'Rationale'],
    ['Frontend', 'Next.js 14 / React 18 + TypeScript', 'Server/Client components, streaming, type safety'],
    ['Styling', 'Tailwind CSS + Glassmorphism', 'Responsive grids, dark/light theme, accessible'],
    ['Backend', 'FastAPI (Python 3.11) + Pydantic v2', 'Async I/O, strict JSON validation, AI ecosystem'],
    ['Database', 'PostgreSQL / SQLite fallback', 'Relational schemas for passports, rules, citations'],
    ['Retrieval', 'BM25 + Dense Embeddings + FAISS', 'Lexical + semantic match across languages'],
    ['Rule Engine', 'YAML Versioned Rule Packs', 'Auditable, deterministic, zero-hallucination'],
    ['Security', 'Regex Sanitizer + DPDP Logger', 'Prompt injection stripping, consent logging'],
]

tech_table = Table(tech_data, colWidths=[1.2*inch, 2.2*inch, 2.8*inch])
tech_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('TOPPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F8FAFC')),
    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 1), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
]))
elements.append(tech_table)
add_spacer()

add_heading("5. Performance SLOs", 1)

slo_data = [
    ['Metric', 'Target'],
    ['p95 Latency (Cached Public Corpus)', '< 12 seconds'],
    ['p95 Latency (Fresh 3-Country RAG)', '< 45 seconds'],
    ['p50 Assessment Latency', '< 4.5 seconds'],
    ['Max Token Ceiling (Extraction)', '1,200 tokens'],
    ['Max Token Ceiling (Retrieval Rank)', '2,500 tokens'],
    ['Max Token Ceiling (Explanation)', '1,800 tokens'],
    ['Target Cache-Hit Rate (Public RAG)', '>= 85%'],
    ['Private Formulation Caching', 'STRICTLY 0%'],
]

slo_table = Table(slo_data, colWidths=[3.5*inch, 2.5*inch])
slo_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 1), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
]))
elements.append(slo_table)
add_spacer()

add_heading("6. User Flow Hierarchical Diagram", 1)
add_paragraph(
    "The following diagram illustrates the hierarchical user flow from initial access through "
    "to final dossier export, showing the complete journey of a user interacting with the system."
)
add_spacer(6)

elements.append(create_user_flow_diagram())
add_spacer()

elements.append(PageBreak())

add_heading("7. System Flow Hierarchical Diagram (All Pipelines Combined)", 1)
add_paragraph(
    "The following diagram combines all pipelines and system flows into a single hierarchical "
    "view, showing how data moves from user input through sandboxing, passport creation, "
    "botanical resolution, rule evaluation, RAG retrieval, citation validation, and finally "
    "to LLM explanation generation and output."
)
add_spacer(6)

elements.append(create_system_flow_diagram())
add_spacer()

add_heading("8. Key Methodology Components", 1)

add_heading("8.1 Botanical Canonicalization & Formulation Fingerprinting", 2)
add_paragraph(
    "Converts raw multilingual user inputs into typed, canonical botanical records. "
    "A fingerprint F is defined as:"
)
add_paragraph(
    "F = { (I₁, R₁, P₁, S₁), (I₂, R₂, P₂, S₂), ..., (Iₙ, Rₙ, Pₙ, Sₙ) }"
)
add_paragraph("Where:")
add_bullet("Iₖ: Canonical Botanical API ID (e.g. API-VOL1-008)")
add_bullet("Rₖ: Quantitative ratio percentage (Σ Rₖ = 100%)")
add_bullet("Pₖ: Plant part utilized (Root, Whole Plant, Leaf, Bark)")
add_bullet("Sₖ: Extraction solvent / process (Aqueous, Hydroalcoholic, Choorna, Taila)")
add_spacer()

add_heading("8.2 Deterministic 3-State Rule Evaluation Engine", 2)
add_paragraph(
    "The rule engine processes versioned YAML rule trees. Each rule specifies premises/conditions, "
    "statutory authority references, and action precedence. The three output states are:"
)
add_bullet("<b>condition_satisfied</b> — All required facts present and predicate evaluates true")
add_bullet("<b>condition_not_satisfied</b> — Facts present but predicate evaluates false")
add_bullet("<b>insufficient_information</b> — Missing facts trigger clarification prompts")
add_spacer()

add_heading("8.3 Citation & Evidence Validator (UCR Gate)", 2)
add_paragraph(
    "The Unsupported Claim Rate (UCR) is defined as the ratio of unsupported statements to total "
    "atomic statements generated. Gate invariants:"
)
add_bullet("If UCR > 5%, explanation is automatically rejected and regenerated")
add_bullet("If primary statutory passage is missing, finding transitions to INSUFFICIENT_EVIDENCE")
add_bullet("Claim-level verification: each claim marked SUPPORTED, CONTRADICTED, or NOT_ENOUGH")
add_bullet("Evidence Confidence is weighted composite of 6 signals (retrieval coverage, citation validity, entailment ratio, source authority, source diversity, rule-engine validation)")
add_spacer()

add_heading("8.4 Adversarial Input Sandboxing", 2)
add_paragraph(
    "Uploaded certificates, PDFs, and scanned labels are processed through an isolated regex "
    "sanitization pipeline that strips prompt injection patterns including:"
)
add_bullet("\"ignore/forget/disregard/override previous instructions\"")
add_bullet("\"you are now / act as / roleplay as / system prompt\"")
add_bullet("\"mark/declare/certify this as patentable/compliant/approved/safe\"")
add_bullet("\"bypass/skip all checks/evaluations/filters/rules\"")
add_spacer()

add_heading("8.5 Hybrid RAG Retrieval Pipeline", 2)
add_bullet("<b>Load</b> documents from pharmacopoeia, ayurveda, regulations, patents, pubmed, who")
add_bullet("<b>Chunk</b> — 800 tokens with 150-token overlap, metadata stored")
add_bullet("<b>Embed</b> — BAAI/bge-base-en-v1.5 via Sentence Transformers")
add_bullet("<b>Index</b> — FAISS flat index")
add_bullet("<b>Retrieve</b> — top-5 relevant chunks per query")
add_bullet("<b>Generate</b> — LLM answers grounded only in retrieved context")
add_spacer()

add_heading("8.6 Multilingual Pipeline", 2)
add_bullet("Language Detection (Devanagari → hi/mr, Tamil → ta, etc.)")
add_bullet("Botanical Canonicalization → Curcuma longa, Azadirachta indica...")
add_bullet("RAG Retrieval against Ayurvedic Pharmacopoeia & classical texts")
add_bullet("LLM Answer + Cited Sources")
add_bullet("Supported: English, Hindi, Marathi, Tamil, Telugu, Kannada, Bengali, Gujarati, Malayalam, Sanskrit")
add_spacer()

add_heading("9. Regulatory Pathways", 1)

add_heading("9.1 India", 2)
add_bullet("<b>ASU Classical Drug</b>: Composition strictly conforms to First Schedule of Drugs & Cosmetics Act, 1940")
add_bullet("<b>ASU Proprietary Medicine</b>: Innovative combinations requiring Rule 158-B safety/efficacy documentation")
add_bullet("<b>Ayurveda Aahara (FSSAI 2022)</b>: Food items prepared per Ayurvedic texts; no disease treatment claims")
add_spacer()

add_heading("9.2 United States", 2)
add_bullet("<b>Dietary Supplement (21 CFR 101.93)</b>: Structure/function claims permitted; FDA disclaimer required")
add_bullet("<b>Unapproved New Drug</b>: Triggered by disease claims; requires IND and NDA approval")
add_spacer()

add_heading("9.3 Canada", 2)
add_bullet("<b>Natural Health Product (NPN)</b>: Requires Natural Product Number; Product License + Site License")
add_spacer()

add_heading("10. Evaluation Framework", 1)
add_bullet("30+ gold standard cases across English, Hindi, and Marathi")
add_bullet("Retrieval Recall@K & Precision@K")
add_bullet("Jurisdiction & Classification Accuracy (>98%)")
add_bullet("Unsupported Claim Rate (UCR) (<1.5%)")
add_bullet("Language-Parity Gap: |Accuracy_Hindi - Accuracy_English| ≤ 0.03")
add_bullet("Language-Parity Gap: |Accuracy_Marathi - Accuracy_English| ≤ 0.03")
add_spacer()

add_heading("11. Compliance & Security", 1)
add_bullet("<b>DPDP Act 2023</b> — consent logging via DPDPConsentLogger")
add_bullet("<b>AI citation grounding</b> — every answer shows retrieved sources + confidence")
add_bullet("<b>Grievance officer</b> — grievance@ipsakti.in")
add_bullet("<b>Data residency</b> — ap-south-1 (Mumbai, India)")
add_bullet("<b>Zero frontend key leaks</b> — all secrets reside in backend boundary")
add_spacer()

add_heading("12. Unified RAG Architectures", 1)

rag_data = [
    ['Architecture', 'Description'],
    ['hybrid', 'Qdrant dense + BM25 + statutory -> RRF -> BGE cross-encoder rerank (default)'],
    ['production', 'Result caching + per-user rate limit + query/cost logging'],
    ['graph', 'Local knowledge graph entity traversal fused with hybrid results'],
    ['agentic', 'Parallel Patent / Regulatory / ABS / TKDL specialist agents + intent routing'],
]

rag_table = Table(rag_data, colWidths=[1.2*inch, 4.8*inch])
rag_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('TOPPADDING', (0, 1), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
]))
elements.append(rag_table)
add_spacer()

elements.append(Spacer(1, 30))
elements.append(Paragraph("— End of Document —", ParagraphStyle('End', parent=body_style, alignment=TA_CENTER, textColor=HexColor('#94A3B8'))))

doc.build(elements)
print(f"PDF created: {OUTPUT_FILE}")
