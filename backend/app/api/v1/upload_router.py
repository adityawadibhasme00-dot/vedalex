import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
from app.core.sandboxing import DocumentSanitizer

router = APIRouter(prefix="/upload", tags=["File Upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/disclosure-check")
async def upload_disclosure_check(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

    file_id = str(uuid.uuid4())[:8]
    safe_filename = f"{file_id}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_filename)
    with open(filepath, "wb") as f:
        f.write(content)

    extracted_text = ""
    if ext == ".txt":
        extracted_text = content.decode("utf-8", errors="ignore")
    elif ext == ".pdf":
        try:
            import fitz
            pdf_doc = fitz.open(stream=content, filetype="pdf")
            for page in pdf_doc:
                extracted_text += page.get_text()
        except Exception:
            extracted_text = "[PDF content - install PyMuPDF for extraction]"
    elif ext == ".docx":
        try:
            from docx import Document
            doc = Document(filepath)
            extracted_text = "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            extracted_text = "[DOCX content - install python-docx for extraction]"
    else:
        extracted_text = "[Image file uploaded - OCR available with EasyOCR]"

    cleaned_text, threats = DocumentSanitizer.sanitize(extracted_text, file.filename)

    return {
        "status": "success",
        "file_id": file_id,
        "filename": file.filename,
        "file_size": len(content),
        "file_type": ext,
        "extracted_text": cleaned_text[:5000],
        "threats_detected": threats,
        "is_safe": len(threats) == 0
    }
