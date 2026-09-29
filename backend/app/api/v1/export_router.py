import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.dossier_builder import SUPPORTED_FORMATS, build_dossier
from app.services.passport_engine import PassportEngine
from app.services.rule_engine import DeterministicRuleEngine

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
import base64
from io import BytesIO

router = APIRouter(prefix="/export", tags=["Dossier Export"])

class ExportRequest(BaseModel):
    passport_id: str
    format: str | None = "pdf"

class ExportResponse(BaseModel):
    status: str
    download_url: str
    filename: str
    generated_at: str
    format: str

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
}

def _qr_base64(passport_id: str) -> str:
    if not QRCODE_AVAILABLE:
        return ""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"IP-SAKTI-PASSPORT:{passport_id}")
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf)
    return base64.b64encode(buf.getvalue()).decode()

@router.post("/dossier", response_model=ExportResponse)
def export_dossier(req: ExportRequest):
    passport = PassportEngine.get_passport(req.passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")

    fmt = (req.format or "pdf").strip().lower()
    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{req.format}'. Supported: "
                   f"{', '.join(SUPPORTED_FORMATS)}",
        )

    findings = DeterministicRuleEngine.evaluate_passport(
        passport, target_markets=passport.target_markets or ["India"]
    )

    try:
        filename, payload = build_dossier(passport, findings, fmt, _qr_base64(passport.id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    export_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "exports")
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, filename)
    with open(filepath, "wb") as f:
        f.write(payload)

    return ExportResponse(
        status="success",
        download_url=f"/api/v1/export/download/{filename}",
        filename=filename,
        generated_at=datetime.now().isoformat(),
        format=fmt,
    )

@router.get("/download/{filename}")
def download_dossier(filename: str):
    export_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "exports")
    filepath = os.path.join(export_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    extension = os.path.splitext(filename)[1].lower()
    return FileResponse(
        filepath,
        media_type=MEDIA_TYPES.get(extension, "application/octet-stream"),
        filename=filename,
    )
