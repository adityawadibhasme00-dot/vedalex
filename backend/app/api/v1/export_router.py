import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from app.services.passport_engine import PassportEngine
from app.services.rule_engine import DeterministicRuleEngine

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
from io import BytesIO
import base64

router = APIRouter(prefix="/export", tags=["Dossier Export"])

class ExportRequest(BaseModel):
    passport_id: str
    format: Optional[str] = "pdf"

class ExportResponse(BaseModel):
    status: str
    download_url: str
    filename: str
    generated_at: str

def _finding_row(f):
    risk_level = 'HIGH' if f.status == 'insufficient_information' else 'MODERATE' if f.status == 'condition_not_satisfied' else 'LOW'
    css_class = 'risk' if risk_level == 'HIGH' else 'warning' if risk_level == 'MODERATE' else 'safe'
    return f'<tr><td>{f.jurisdiction}</td><td>{f.pathway_category}</td><td class="{css_class}">{risk_level}</td><td>{f.explanation_text or f.status}</td></tr>'

@router.post("/dossier", response_model=ExportResponse)
async def export_dossier(req: ExportRequest):
    passport = PassportEngine.get_passport(req.passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")

    findings = DeterministicRuleEngine.evaluate_passport(
        passport, target_markets=passport.target_markets or ["India"]
    )

    qr_b64 = ""
    if QRCODE_AVAILABLE:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"IP-SAKTI-PASSPORT:{passport.id}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        qr_img.save(buf)
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

    export_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "exports")
    os.makedirs(export_dir, exist_ok=True)

    filename = f"IPSAKTI_Dossier_{passport.id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(export_dir, filename)

    html_content = f"""<!DOCTYPE html>
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
        <p>Passport ID: {passport.id}</p>
    </div>

    <div class="qr">
        <img src="data:image/png;base64,{qr_b64}" alt="Passport QR Code" width="150" />
        <p>Scan to verify passport authenticity</p>
    </div>

    <div class="section">
        <h2>Basic Information</h2>
        <table>
            <tr><th>Case Title</th><td>{passport.case_title}</td></tr>
            <tr><th>Product Form</th><td>{passport.product_form or 'N/A'}</td></tr>
            <tr><th>Dosage Form</th><td>{passport.dosage_form or 'N/A'}</td></tr>
            <tr><th>Intended Use</th><td>{passport.intended_use or 'N/A'}</td></tr>
            <tr><th>Version</th><td>{passport.version}</td></tr>
            <tr><th>Target Markets</th><td>{', '.join(passport.target_markets or [])}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Ingredients</h2>
        <table>
            <tr><th>Raw Name</th><th>Botanical Name</th><th>API Monograph</th><th>Plant Part</th></tr>
            {"".join(f'<tr><td>{ing.raw_name}</td><td>{ing.botanical_name or "N/A"}</td><td>{ing.api_monograph_id or "N/A"}</td><td>{ing.plant_part or "N/A"}</td></tr>' for ing in passport.ingredients)}
        </table>
    </div>

    <div class="section">
        <h2>Proposed Claims</h2>
        <ul>
            {"".join(f'<li>{claim}</li>' for claim in passport.proposed_claims)}
        </ul>
    </div>

    <div class="section">
        <h2>Innovation Description</h2>
        <p>{passport.claimed_innovation or 'N/A'}</p>
    </div>

    <div class="section">
        <h2>Preparation Process</h2>
        <p>{passport.process_description or 'N/A'}</p>
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
        <p>Total Ingredients: {len(passport.ingredients)}</p>
        <p>Claims Proposed: {len(passport.proposed_claims)}</p>
        <p>Markets Targeted: {len(passport.target_markets or [])}</p>
    </div>

    <div class="footer">
        <p>This document was generated by IP-SAKTI Sahayak - AI-Powered Regulatory Decision Engine</p>
        <p>For informational purposes only. Consult qualified patent agents and regulatory specialists.</p>
        <p>DPDP Act 2023 Compliant | Data Residency: ap-south-1 (Mumbai, India)</p>
    </div>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return ExportResponse(
        status="success",
        download_url=f"/api/v1/export/download/{filename}",
        filename=filename,
        generated_at=datetime.now().isoformat()
    )

@router.get("/download/{filename}")
async def download_dossier(filename: str):
    export_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "exports")
    filepath = os.path.join(export_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="text/html", filename=filename)
