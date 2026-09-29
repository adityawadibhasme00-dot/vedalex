"""
Dossier document builders — IP-SAKTI Sahayak.

The Dossier screen offers three genuinely different artefacts, so they are
built by three different renderers instead of one HTML blob re-labelled:

  pdf        → full Innovation Passport dossier (reportlab, print-ready,
               passport QR embedded, statutory citations per finding)
  docx       → the same dossier as an editable Word file for counsel /
               patent-agent markup (python-docx)
  checklist  → a filing & evidence checklist (reportlab) — one tick-box per
               outstanding action, grouped by jurisdiction, with the missing
               facts and the statutory reference for each item
  html       → legacy browser-viewable dossier (kept for API back-compat)

Every renderer receives the passport plus the deterministic rule-engine
findings, so the PDF, the DOCX and the checklist never disagree about the
regulatory position — only about the presentation.
"""

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from app.models.passport import InnovationPassport
from app.models.regulatory import RegulatoryFinding

SUPPORTED_FORMATS: tuple[str, ...] = ("pdf", "docx", "checklist", "html")

BRAND_GREEN = "#059669"
BRAND_DARK = "#065f46"
INK = "#1f2937"
MUTED = "#6b7280"
RISK_COLORS = {"HIGH": "#dc2626", "MODERATE": "#d97706", "LOW": "#059669"}

STATUS_LABELS = {
    "condition_satisfied": "READY",
    "condition_not_satisfied": "ACTION REQUIRED",
    "insufficient_information": "EVIDENCE NEEDED",
}


def risk_level(finding: RegulatoryFinding) -> str:
    status = str(getattr(finding.status, "value", finding.status))
    if status == "insufficient_information":
        return "HIGH"
    if status == "condition_not_satisfied":
        return "MODERATE"
    return "LOW"


def _status_of(finding: RegulatoryFinding) -> str:
    return str(getattr(finding.status, "value", finding.status))


def _txt(value: Any, fallback: str = "N/A") -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _passport_rows(passport: InnovationPassport) -> list[tuple[str, str]]:
    return [
        ("Case Title", _txt(passport.case_title)),
        ("Product Form", _txt(passport.product_form)),
        ("Dosage Form", _txt(passport.dosage_form)),
        ("Intended Use", _txt(passport.intended_use)),
        ("Business Role", _txt(passport.business_role)),
        ("Version", str(passport.version)),
        ("Target Markets", ", ".join(passport.target_markets or []) or "N/A"),
        ("Manufacturing Location", _txt(passport.manufacturing_location)),
        ("Biological Resource Origin", _txt(passport.biological_resource_origin)),
        ("Existing IP Status", _txt(passport.existing_ip_status)),
    ]


def _qr_png_bytes(qr_b64: str) -> bytes | None:
    if not qr_b64:
        return None
    try:
        return base64.b64decode(qr_b64)
    except Exception:  # noqa: BLE001 — a missing QR must never break export
        return None


def _citations_line(finding: RegulatoryFinding) -> str:
    refs = [
        f"{c.act_title} {c.section_reference} ({c.authority})"
        for c in (finding.supporting_citations or [])
        if getattr(c, "act_title", None)
    ]
    return "; ".join(refs)


# ============================================================================
# PDF · full dossier
# ============================================================================

def render_dossier_pdf(passport: InnovationPassport,
                       findings: list[RegulatoryFinding],
                       qr_b64: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"IP-SAKTI Dossier · {passport.case_title}",
        author="IP-SAKTI Sahayak",
    )
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("dH1", parent=base["Title"], fontSize=20, leading=24,
                        textColor=colors.HexColor(BRAND_DARK), spaceAfter=2)
    sub = ParagraphStyle("dSub", parent=base["Normal"], fontSize=9, leading=13,
                         alignment=TA_CENTER, textColor=colors.HexColor(MUTED))
    h2 = ParagraphStyle("dH2", parent=base["Heading2"], fontSize=12, leading=15,
                        textColor=colors.HexColor(BRAND_GREEN), spaceBefore=10,
                        spaceAfter=4)
    body = ParagraphStyle("dBody", parent=base["Normal"], fontSize=9.5, leading=13,
                          textColor=colors.HexColor(INK))
    small = ParagraphStyle("dSmall", parent=body, fontSize=8, leading=10.5,
                           textColor=colors.HexColor(MUTED))

    story: list[Any] = [
        Paragraph("IP-SAKTI Sahayak", h1),
        Paragraph("Innovation Passport Dossier", sub),
        Spacer(1, 6 * mm),
    ]

    qr = _qr_png_bytes(qr_b64)
    if qr:
        img_buf = BytesIO(qr)
        story.append(Image(img_buf, width=32 * mm, height=32 * mm))
        story.append(Paragraph(
            f"Scan to verify passport authenticity · Passport ID: {escape(passport.id)}",
            sub))
        story.append(Spacer(1, 4 * mm))

    def section(title: str) -> None:
        story.append(Paragraph(title, h2))

    def kv_table(rows: list[tuple[str, str]]) -> Table:
        data = [[Paragraph(f"<b>{escape(k)}</b>", body), Paragraph(escape(v), body)]
                for k, v in rows]
        tbl = Table(data, colWidths=[55 * mm, 115 * mm], hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecfdf5")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    section("1 · Passport Summary")
    story.append(kv_table(_passport_rows(passport)))

    section("2 · Ingredients")
    ing_rows = [[Paragraph(f"<b>{h}</b>", body) for h in
                 ("Raw Name", "Botanical Name", "API Monograph", "Plant Part", "Source")]]
    for ing in passport.ingredients or []:
        ing_rows.append([Paragraph(escape(_txt(getattr(ing, 'raw_name', ''))), body),
                         Paragraph(escape(_txt(getattr(ing, 'botanical_name', None))), body),
                         Paragraph(escape(_txt(getattr(ing, 'api_monograph_id', None))), body),
                         Paragraph(escape(_txt(getattr(ing, 'plant_part', None))), body),
                         Paragraph(escape(_txt(getattr(ing, 'source_country', None))), body)])
    if len(ing_rows) == 1:
        ing_rows.append([Paragraph("No ingredients recorded.", small)] + [""] * 4)
    ing_tbl = Table(ing_rows, colWidths=[38 * mm, 42 * mm, 34 * mm, 30 * mm, 26 * mm], repeatRows=1)
    ing_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ing_tbl)

    section("3 · Proposed Claims")
    claims = passport.proposed_claims or []
    if claims:
        for i, claim in enumerate(claims, 1):
            story.append(Paragraph(f"{i}. {escape(str(claim))}", body))
    else:
        story.append(Paragraph("No claims recorded.", small))

    section("4 · Claimed Innovation")
    story.append(Paragraph(escape(_txt(passport.claimed_innovation, "Not recorded.")), body))

    section("5 · Preparation Process")
    story.append(Paragraph(escape(_txt(passport.process_description, "Not recorded.")), body))

    section("6 · Regulatory Assessment")
    head = ["Jurisdiction", "Pathway", "Risk", "Details"]
    rows = [[Paragraph(f"<b>{h}</b>", body) for h in head]]
    for f in findings:
        level = risk_level(f)
        rows.append([
            Paragraph(escape(f.jurisdiction), body),
            Paragraph(escape(_txt(f.pathway_category)), body),
            Paragraph(f"<font color='{RISK_COLORS[level]}'><b>{level}</b></font>", body),
            Paragraph(escape(_txt(f.explanation_text, _status_of(f))), body),
        ])
    reg = Table(rows, colWidths=[26 * mm, 48 * mm, 20 * mm, 76 * mm], repeatRows=1)
    reg.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(reg)

    cited = [f for f in findings if _citations_line(f)]
    if cited:
        section("7 · Statutory Basis")
        for f in cited:
            story.append(Paragraph(
                f"<b>{escape(f.jurisdiction)}</b> — {escape(_citations_line(f))}", small))

    section("8 · Evidence Status")
    story.append(kv_table([
        ("Total Ingredients", str(len(passport.ingredients or []))),
        ("Claims Proposed", str(len(passport.proposed_claims or []))),
        ("Markets Targeted", str(len(passport.target_markets or []))),
        ("Unresolved Clarifications", str(len(passport.unresolved_clarifications or []))),
        ("Open Actions", str(sum(len(f.next_action_steps or []) for f in findings))),
    ]))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "Generated by IP-SAKTI Sahayak · AI-Powered Regulatory Decision Engine. "
        "Informational purposes only — consult a qualified patent agent and "
        "regulatory specialist before filing. DPDP Act 2023 compliant · "
        "Data residency: ap-south-1 (Mumbai, India).", small))

    def _page(canvas, _doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(18 * mm, 10 * mm,
                          f"IP-SAKTI Dossier · {passport.case_title} · Passport {passport.id}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
        canvas.setStrokeColor(colors.HexColor(BRAND_GREEN))
        canvas.setLineWidth(1.2)
        canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        canvas.restoreState()

    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()


# ============================================================================
# DOCX · editable dossier
# ============================================================================

def render_dossier_docx(passport: InnovationPassport,
                        findings: list[RegulatoryFinding],
                        qr_b64: str = "") -> bytes:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    document = docx.Document()
    for style_name, size, color in (
        ("Normal", 10, INK),
        ("Title", 22, BRAND_DARK),
        ("Heading 1", 14, BRAND_GREEN),
        ("Heading 2", 12, BRAND_DARK),
    ):
        style = document.styles[style_name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        if style_name != "Normal":
            style.font.color.rgb = RGBColor.from_string(color.lstrip("#"))

    document.add_heading("IP-SAKTI Sahayak", 0)
    subtitle = document.add_paragraph("Innovation Passport Dossier — editable for counsel review")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.size = Pt(9)
    subtitle.runs[0].font.color.rgb = RGBColor.from_string(MUTED.lstrip("#"))

    qr = _qr_png_bytes(qr_b64)
    if qr:
        document.add_picture(BytesIO(qr), width=Inches(1.3))
        document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta = document.add_paragraph(f"Passport ID: {passport.id}")
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.runs[0].font.size = Pt(9)

    document.add_heading("1 · Passport Summary", level=1)
    table = document.add_table(rows=0, cols=2)
    table.style = "Light Grid Accent 1"
    for key, value in _passport_rows(passport):
        cells = table.add_row().cells
        cells[0].text = key
        cells[1].text = value
        for run in cells[0].paragraphs[0].runs:
            run.bold = True

    document.add_heading("2 · Ingredients", level=1)
    ing_table = document.add_table(rows=1, cols=5)
    ing_table.style = "Light Grid Accent 1"
    for cell, head in zip(ing_table.rows[0].cells,
                          ("Raw Name", "Botanical Name", "API Monograph", "Plant Part", "Source")):
        cell.text = head
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for ing in passport.ingredients or []:
        cells = ing_table.add_row().cells
        for cell, value in zip(cells, (
            _txt(getattr(ing, "raw_name", "")),
            _txt(getattr(ing, "botanical_name", None)),
            _txt(getattr(ing, "api_monograph_id", None)),
            _txt(getattr(ing, "plant_part", None)),
            _txt(getattr(ing, "source_country", None)),
        )):
            cell.text = value
    if not passport.ingredients:
        document.add_paragraph("No ingredients recorded.")

    document.add_heading("3 · Proposed Claims", level=1)
    claims = passport.proposed_claims or []
    if claims:
        for claim in claims:
            document.add_paragraph(str(claim), style="List Number")
    else:
        document.add_paragraph("No claims recorded.")

    document.add_heading("4 · Claimed Innovation", level=1)
    document.add_paragraph(_txt(passport.claimed_innovation, "Not recorded."))
    document.add_heading("5 · Preparation Process", level=1)
    document.add_paragraph(_txt(passport.process_description, "Not recorded."))

    document.add_heading("6 · Regulatory Assessment", level=1)
    reg = document.add_table(rows=1, cols=4)
    reg.style = "Light Grid Accent 1"
    for cell, head in zip(reg.rows[0].cells,
                          ("Jurisdiction", "Pathway", "Risk", "Details / Next Actions")):
        cell.text = head
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for f in findings:
        level = risk_level(f)
        details = _txt(f.explanation_text, _status_of(f))
        steps = f.next_action_steps or []
        if steps:
            details += "\nNext: " + "; ".join(str(s) for s in steps[:4])
        cells = reg.add_row().cells
        for cell, value in zip(cells, (f.jurisdiction, _txt(f.pathway_category), level, details)):
            cell.text = value
    if not findings:
        document.add_paragraph("No regulatory findings for the targeted markets.")

    cited = [f for f in findings if _citations_line(f)]
    if cited:
        document.add_heading("7 · Statutory Basis", level=1)
        for f in cited:
            document.add_paragraph(f"{f.jurisdiction} — {_citations_line(f)}",
                                   style="List Bullet")

    document.add_heading("8 · Evidence Status", level=1)
    status = document.add_table(rows=0, cols=2)
    status.style = "Light Grid Accent 1"
    for key, value in (
        ("Total Ingredients", str(len(passport.ingredients or []))),
        ("Claims Proposed", str(len(claims))),
        ("Markets Targeted", str(len(passport.target_markets or []))),
        ("Open Actions", str(sum(len(f.next_action_steps or []) for f in findings))),
    ):
        cells = status.add_row().cells
        cells[0].text = key
        cells[1].text = value
        for run in cells[0].paragraphs[0].runs:
            run.bold = True

    document.add_paragraph(
        "Generated by IP-SAKTI Sahayak. Informational purposes only — consult a "
        "qualified patent agent and regulatory specialist before filing."
    ).runs[0].font.size = Pt(8)

    buf = BytesIO()
    document.save(buf)
    return buf.getvalue()


# ============================================================================
# Checklist · filing & evidence readiness (tick-boxes, per jurisdiction)
# ============================================================================

def build_checklist_sections(passport: InnovationPassport,
                             findings: list[RegulatoryFinding]) -> list[dict[str, Any]]:
    """Group the filing work into sections of tick-box items.

    Passport-completeness gaps come first, then one section per target
    jurisdiction (never mixed — a finding's jurisdiction decides its section).
    Each section carries the statutory basis once, instead of repeating the
    full citation on every row.
    """
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def section(title: str, basis: str = "") -> dict[str, Any]:
        node = {"title": title, "basis": basis, "items": []}
        sections.append(node)
        return node

    def add(target: dict[str, Any], requirement: str, status: str, detail: str = "") -> None:
        target["items"].append({"requirement": requirement, "status": status,
                                "detail": detail})

    # -- A. Passport completeness -------------------------------------------
    completeness = section("A · Passport completeness")
    ingredients = passport.ingredients or []
    add(completeness,
        "Case title, product form and dosage form recorded",
        "READY" if passport.case_title and passport.product_form else "EVIDENCE NEEDED",
        f"{_txt(passport.product_form)} · {_txt(passport.dosage_form)}")
    add(completeness,
        "Intended use / therapeutic claim stated",
        "READY" if passport.intended_use else "EVIDENCE NEEDED",
        _txt(passport.intended_use, "No intended use recorded"))
    add(completeness,
        "Proposed claims enumerated for the application",
        "READY" if passport.proposed_claims else "EVIDENCE NEEDED",
        f"{len(passport.proposed_claims or [])} claim(s)")
    add(completeness,
        "Preparation process described",
        "READY" if passport.process_description else "EVIDENCE NEEDED",
        _txt(passport.process_description, "No process recorded"))
    add(completeness,
        "Every ingredient carries a botanical name",
        "READY" if ingredients and all(getattr(i, "botanical_name", None) for i in ingredients)
        else "ACTION REQUIRED",
        f"{sum(1 for i in ingredients if getattr(i, 'botanical_name', None))}"
        f"/{len(ingredients)} mapped")
    add(completeness,
        "API monograph reference for every ingredient (Section 3(p) screening)",
        "READY" if ingredients and all(getattr(i, "api_monograph_id", None) for i in ingredients)
        else "ACTION REQUIRED",
        f"{sum(1 for i in ingredients if getattr(i, 'api_monograph_id', None))}"
        f"/{len(ingredients)} referenced")
    add(completeness,
        "Source country and origin status declared (Biological Diversity Act / ABS)",
        "READY" if ingredients and all(getattr(i, "source_country", None) for i in ingredients)
        else "EVIDENCE NEEDED",
        ", ".join(sorted({str(getattr(i, "source_country", "N/A")) for i in ingredients})) or "N/A")
    for clarification in passport.unresolved_clarifications or []:
        add(completeness, f"Resolve clarification: {clarification}", "ACTION REQUIRED")

    # -- B. Per-jurisdiction filing + evidence actions ----------------------
    for f in findings:
        title = f"B · {f.jurisdiction} — {_txt(f.pathway_category, 'Unclassified pathway')}"
        existing = next((s for s in sections if s["title"] == title), None)
        basis = _citations_line(f)
        if existing is None:
            current = section(title, basis)
        else:
            current = existing
            if basis and basis not in current["basis"]:
                current["basis"] = f"{current['basis']}; {basis}" if current["basis"] else basis

        base_status = STATUS_LABELS.get(_status_of(f), _status_of(f))
        steps = list(f.next_action_steps or []) or [
            f"Confirm pathway status for {f.jurisdiction}"]
        for step in steps:
            add(current, str(step), base_status)
        for missing in f.missing_facts or []:
            add(current, f"Supply missing fact: {missing}", "EVIDENCE NEEDED")
        add(current, "Statutory basis confirmed against the current act text",
            "READY" if basis else "EVIDENCE NEEDED",
            "" if basis else "No citation attached to this finding")
        if getattr(f, "requires_human_review", False):
            add(current, "Human expert review required before filing", "ACTION REQUIRED",
                "Deterministic engine flagged this finding")

    return [s for s in sections if s["items"]]


def render_checklist_pdf(passport: InnovationPassport,
                         findings: list[RegulatoryFinding],
                         qr_b64: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    sections = build_checklist_sections(passport, findings)
    total = sum(len(s["items"]) for s in sections)
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"IP-SAKTI Filing Checklist · {passport.case_title}",
        author="IP-SAKTI Sahayak",
    )
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("cH1", parent=base["Title"], fontSize=18, leading=22,
                        textColor=colors.HexColor(BRAND_DARK))
    h2 = ParagraphStyle("cH2", parent=base["Heading2"], fontSize=11.5, leading=14,
                        textColor=colors.HexColor(BRAND_GREEN), spaceBefore=9,
                        spaceAfter=1)
    basis_style = ParagraphStyle("cBasis", parent=base["Normal"], fontSize=7.5,
                                 leading=9.5, textColor=colors.HexColor(MUTED),
                                 spaceAfter=3)
    body = ParagraphStyle("cBody", parent=base["Normal"], fontSize=9, leading=12,
                          textColor=colors.HexColor(INK))
    small = ParagraphStyle("cSmall", parent=body, fontSize=7.5, leading=9.5,
                           textColor=colors.HexColor(MUTED))

    story: list[Any] = [
        Paragraph("Filing &amp; Evidence Checklist", h1),
        Paragraph(
            f"{escape(passport.case_title)} · Passport {escape(passport.id)} · "
            f"Generated {datetime.now().strftime('%d %B %Y')} · "
            f"{total} item(s) to action", small),
        Spacer(1, 3 * mm),
    ]

    for section in sections:
        story.append(Paragraph(escape(section["title"]), h2))
        if section["basis"]:
            story.append(Paragraph(f"<i>Statutory basis:</i> {escape(section['basis'])}",
                                   basis_style))
        data = []
        for item in section["items"]:
            level = RISK_COLORS["HIGH"] if item["status"] == "EVIDENCE NEEDED" else (
                RISK_COLORS["MODERATE"] if item["status"] == "ACTION REQUIRED"
                else RISK_COLORS["LOW"])
            data.append([
                "",
                Paragraph(f"<b>{escape(item['requirement'])}</b>"
                          + (f"<br/><font size='7.5' color='{MUTED}'>{escape(item['detail'])}</font>"
                             if item["detail"] else ""), body),
                Paragraph(f"<font color='{level}'><b>{escape(item['status'])}</b></font>", small),
            ])
        tbl = Table(data, colWidths=[9 * mm, 136 * mm, 30 * mm], repeatRows=0)
        tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (0, -1), 0.7, colors.HexColor("#6b7280")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#e5e7eb")),
        ]))
        story.append(tbl)

    ready = sum(1 for s in sections for i in s["items"] if i["status"] == "READY")
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        f"<b>Readiness:</b> {ready}/{total} item(s) already satisfied · "
        f"{total - ready} outstanding. Tick each box as evidence is filed. "
        f"Generated by IP-SAKTI Sahayak — informational only.", small))

    def _page(canvas, _doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(16 * mm, 9 * mm, f"IP-SAKTI Filing Checklist · {passport.case_title}")
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()


# ============================================================================
# HTML · legacy browser-viewable dossier
# ============================================================================

def _finding_row(finding: RegulatoryFinding) -> str:
    level = risk_level(finding)
    css_class = {"HIGH": "risk", "MODERATE": "warning", "LOW": "safe"}[level]
    return (
        f"<tr><td>{escape(finding.jurisdiction)}</td>"
        f"<td>{escape(_txt(finding.pathway_category))}</td>"
        f'<td class="{css_class}">{level}</td>'
        f"<td>{escape(_txt(finding.explanation_text, _status_of(finding)))}</td></tr>"
    )


def render_dossier_html(passport: InnovationPassport,
                        findings: list[RegulatoryFinding],
                        qr_b64: str = "") -> str:
    """Browser-viewable dossier. All user-controlled values are XML-escaped so
    an exported file can never carry stored XSS back to the reader."""
    e = escape
    qr_block = (
        f'<img src="data:image/png;base64,{qr_b64}" alt="Passport QR Code" width="150" />'
        if qr_b64 else ""
    )
    ingredients = "".join(
        "<tr>"
        f"<td>{e(str(getattr(ing, 'raw_name', '') or 'N/A'))}</td>"
        f"<td>{e(_txt(getattr(ing, 'botanical_name', None)))}</td>"
        f"<td>{e(_txt(getattr(ing, 'api_monograph_id', None)))}</td>"
        f"<td>{e(_txt(getattr(ing, 'plant_part', None)))}</td>"
        "</tr>"
        for ing in passport.ingredients or []
    ) or "<tr><td colspan='4'>No ingredients recorded.</td></tr>"

    claims = "".join(f"<li>{e(str(c))}</li>" for c in passport.proposed_claims or []) \
        or "<li>No claims recorded.</li>"

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>IP-SAKTI Innovation Passport Dossier</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        .header {{ text-align: center; border-bottom: 3px solid #059669; padding-bottom: 20px; margin-bottom: 30px; }}
        .logo {{ font-size: 28px; font-weight: bold; color: #059669; }}
        h1 {{ color: #065f46; margin: 10px 0; }}
        h2 {{ color: #047857; border-bottom: 1px solid #d1d5db; padding-bottom: 5px; }}
        .qr {{ text-align: center; margin: 20px 0; }}
        .section {{ margin: 20px 0; padding: 15px; background: #f9fafb; border-radius: 8px; border-left: 4px solid #059669; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }}
        th {{ background: #ecfdf5; font-weight: bold; }}
        .safe {{ color: #059669; font-weight: bold; }}
        .warning {{ color: #d97706; font-weight: bold; }}
        .risk {{ color: #dc2626; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 40px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">IP-SAKTI Sahayak</div>
        <h1>Innovation Passport Dossier</h1>
        <p>Generated: {datetime.now().strftime('%d %B %Y, %H:%M UTC')}</p>
        <p>Passport ID: {e(passport.id)}</p>
    </div>

    <div class="qr">
        {qr_block}
        <p>Scan to verify passport authenticity</p>
    </div>

    <div class="section">
        <h2>Basic Information</h2>
        <table>
            <tr><th>Case Title</th><td>{e(_txt(passport.case_title))}</td></tr>
            <tr><th>Product Form</th><td>{e(_txt(passport.product_form))}</td></tr>
            <tr><th>Dosage Form</th><td>{e(_txt(passport.dosage_form))}</td></tr>
            <tr><th>Intended Use</th><td>{e(_txt(passport.intended_use))}</td></tr>
            <tr><th>Version</th><td>{e(str(passport.version))}</td></tr>
            <tr><th>Target Markets</th><td>{e(', '.join(passport.target_markets or []))}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Ingredients</h2>
        <table>
            <tr><th>Raw Name</th><th>Botanical Name</th><th>API Monograph</th><th>Plant Part</th></tr>
            {ingredients}
        </table>
    </div>

    <div class="section">
        <h2>Proposed Claims</h2>
        <ul>
            {claims}
        </ul>
    </div>

    <div class="section">
        <h2>Innovation Description</h2>
        <p>{e(_txt(passport.claimed_innovation))}</p>
    </div>

    <div class="section">
        <h2>Preparation Process</h2>
        <p>{e(_txt(passport.process_description))}</p>
    </div>

    <div class="section">
        <h2>Regulatory Assessment</h2>
        <table>
            <tr><th>Jurisdiction</th><th>Pathway</th><th>Risk Level</th><th>Details</th></tr>
            {''.join(_finding_row(f) for f in findings)}
        </table>
    </div>

    <div class="section">
        <h2>Evidence Status</h2>
        <p>Total Ingredients: {len(passport.ingredients or [])}</p>
        <p>Claims Proposed: {len(passport.proposed_claims or [])}</p>
        <p>Markets Targeted: {len(passport.target_markets or [])}</p>
    </div>

    <div class="footer">
        <p>This document was generated by IP-SAKTI Sahayak - AI-Powered Regulatory Decision Engine</p>
        <p>For informational purposes only. Consult qualified patent agents and regulatory specialists.</p>
        <p>DPDP Act 2023 Compliant | Data Residency: ap-south-1 (Mumbai, India)</p>
    </div>
</body>
</html>"""


# ============================================================================
# Orchestration
# ============================================================================

_EXTENSIONS = {"pdf": ".pdf", "docx": ".docx", "checklist": ".pdf", "html": ".html"}


def build_dossier(passport: InnovationPassport,
                  findings: list[RegulatoryFinding],
                  fmt: str,
                  qr_b64: str = "") -> tuple[str, bytes]:
    """Render one dossier artefact.

    Returns ``(filename, raw_bytes)`` for the requested format.
    """
    fmt = (fmt or "pdf").strip().lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported dossier format: {fmt}")

    if fmt == "pdf":
        payload = render_dossier_pdf(passport, findings, qr_b64)
    elif fmt == "docx":
        payload = render_dossier_docx(passport, findings, qr_b64)
    elif fmt == "checklist":
        payload = render_checklist_pdf(passport, findings, qr_b64)
    else:
        payload = render_dossier_html(passport, findings, qr_b64).encode("utf-8")

    stem = "Checklist" if fmt == "checklist" else "Dossier"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"IPSAKTI_{stem}_{passport.id[:8]}_{stamp}{_EXTENSIONS[fmt]}"
    return filename, payload
