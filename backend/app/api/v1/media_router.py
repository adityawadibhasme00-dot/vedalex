import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.rag.kb import kb_root

router = APIRouter(prefix="/copilot", tags=["Copilot Media"])

@router.get("/media/{path:path}")
async def serve_media(path: str):
    base = os.path.join(kb_root(), "images")
    full = os.path.abspath(os.path.join(base, path))
    if not full.startswith(os.path.abspath(base)) or not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(full)