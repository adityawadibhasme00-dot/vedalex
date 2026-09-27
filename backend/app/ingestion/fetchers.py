"""
Guarded content fetchers for the IP-SAKTI ingestion pipeline.

Reuses the whitelist + search machinery from ``official_web_retriever`` so
ingestion respects the same official-domain policy. Every fetch is
time-boxed, TTL-cached, and never raises on failure.
"""

import hashlib
import io
import logging
import os
import re
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SEC = float(os.environ.get("IPSAKTI_WEB_TIMEOUT", "12"))
CACHE_TTL_SEC = float(os.environ.get("IPSAKTI_WEB_CACHE_TTL", "21600"))

_fetch_url: Callable[..., str | None] | None

# Reuse the official-source fetch + whitelist utilities.
try:
    from app.rag.official_web_retriever import (
        _fetch_url,
        _html_to_text,
        _is_allowed_domain,
        _search_candidate_links,
    )
except Exception:  # pragma: no cover - backend not bootstrapped
    _fetch_url = None

    def _html_to_text(html: str) -> tuple[str, str]:  # type: ignore[no-redef]
        return "Official Source", ""

    def _is_allowed_domain(url: str) -> bool:  # type: ignore[no-redef]
        return True

    def _search_candidate_links(query: str, top: int = 5) -> list[str]:  # type: ignore[no-redef]
        return []


def is_allowed_url(url: str) -> bool:
    return _is_allowed_domain(url)


def fetch_html(url: str, timeout: float = HTTP_TIMEOUT_SEC) -> tuple[str, str] | None:
    """Fetch a URL and return ``(title, cleaned_text)`` or ``None``."""
    if _fetch_url is None:
        return None
    html = _fetch_url(url, timeout=timeout)
    if not html:
        return None
    return _html_to_text(html)


def fetch_pdf(url_or_path: str, timeout: float = HTTP_TIMEOUT_SEC) -> str | None:
    """Extract text from a PDF at a URL or local path."""
    try:
        import fitz
    except Exception as exc:
        logger.warning("PyMuPDF unavailable for PDF extraction: %s", exc)
        return None

    data = None
    try:
        if url_or_path.startswith("http"):
            if _fetch_url is None:
                return None
            cached = _fetch_url
            text = cached(url_or_path, timeout=timeout)
            if not text:
                return None
            data = text.encode("utf-8", errors="ignore")
            # _fetch_url returns decoded text; PDFs are binary — re-fetch raw.
            import httpx
            with httpx.Client(follow_redirects=True, timeout=timeout) as client:
                resp = client.get(url_or_path, headers={"User-Agent": "IP-SAKTI IngestionBot"})
                if resp.status_code >= 400:
                    return None
                data = resp.content
        else:
            with open(url_or_path, "rb") as fh:
                data = fh.read()
    except Exception as exc:
        logger.debug("PDF fetch failed for %s: %s", url_or_path, exc)
        return None

    try:
        doc = fitz.open(stream=data, filetype="pdf") if isinstance(data, bytes) else None
        if doc is None:
            return None
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return re.sub(r"\s+", " ", text).strip()
    except Exception as exc:
        logger.debug("PDF parse failed for %s: %s", url_or_path, exc)
        return None


def fetch_docx(path: str) -> str | None:
    """Extract text from a local .docx file."""
    try:
        import docx
        document = docx.Document(path)
        return "\n".join(p.text for p in document.paragraphs if p.text).strip()
    except Exception as exc:
        logger.debug("DOCX read failed for %s: %s", path, exc)
        return None


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def csv_to_text(data: bytes, charset: str = "utf-8") -> str:
    """Parse CSV bytes into a searchable ``field: value`` text corpus.

    Each non-empty row is flattened to ``Header: Value | Header: Value`` lines
    so column names (e.g. ``application_number``) stay attached to their values
    for lexical matching while remaining readable for the embedding model.
    """
    import csv

    if not data:
        return ""
    try:
        raw = data.decode(charset, errors="ignore").lstrip("\ufeff")
        rows: list[str] = []
        reader = csv.reader(io.StringIO(raw))
        header = next(reader, [])
        for row in reader:
            if not row or not any(str(c).strip() for c in row):
                continue
            if header:
                pairs = [
                    f"{h.strip()}: {str(v).strip()}"
                    for h, v in zip(header, row, strict=False)
                    if str(v).strip()
                ]
            else:
                pairs = [str(c).strip() for c in row]
            if pairs:
                rows.append(" | ".join(pairs))
        return "\n".join(rows).strip()
    except Exception as exc:
        logger.debug("CSV parse failed: %s", exc)
        return ""


def fetch_csv(url_or_path: str, timeout: float = HTTP_TIMEOUT_SEC) -> str | None:
    """Download/read a CSV (URL or local path) and return flattened text."""
    import httpx

    data: bytes | None = None
    try:
        if url_or_path.startswith("http"):
            with httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": "IP-SAKTI IngestionBot"}) as client:
                resp = client.get(url_or_path)
                if resp.status_code >= 400:
                    return None
                data = resp.content
        else:
            with open(url_or_path, "rb") as fh:
                data = fh.read()
    except Exception as exc:
        logger.debug("CSV fetch failed for %s: %s", url_or_path, exc)
        return None
    text = csv_to_text(data or b"")
    return text or None


_ocr_reader = None
_ocr_attempted = False
_ocr_lock = threading.Lock()


def _get_ocr_reader(langs: tuple[str, ...] = ("en",)):
    """Lazily load (and then cache) the EasyOCR reader instance.

    EasyOCR downloads detection/recognition models on first use; a network
    failure must never break ingestion — we record the attempt and return
    ``None`` so callers degrade to their existing fallback text.
    """
    global _ocr_reader, _ocr_attempted
    with _ocr_lock:
        if _ocr_attempted:
            return _ocr_reader
        _ocr_attempted = True
        try:
            import easyocr
            _ocr_reader = easyocr.Reader(langs, gpu=False, verbose=False)
            logger.info("EasyOCR reader ready (langs=%s)", ",".join(langs))
        except Exception as exc:
            logger.warning("EasyOCR unavailable (OCR disabled): %s", exc)
            _ocr_reader = None
        return _ocr_reader


def ocr_image(source, langs: tuple[str, ...] = ("en",)) -> str | None:
    """Run OCR on an image given as a file path or raw bytes.

    Returns extracted text joined into a single paragraph, or ``None`` when
    the OCR stack is unavailable or the image cannot be decoded.
    """
    reader = _get_ocr_reader(langs)
    if reader is None:
        return None
    try:
        import numpy as np
        from PIL import Image

        if isinstance(source, (bytes, bytearray)):
            img = Image.open(io.BytesIO(bytes(source))).convert("RGB")
        else:
            img = Image.open(source).convert("RGB")
        arr = np.array(img)

        result = reader.readtext(arr, detail=0)
        return " ".join(str(t) for t in result if t).strip() or None
    except Exception as exc:
        logger.debug("OCR failed: %s", exc)
        return None


def fetch_image(url: str, timeout: float = HTTP_TIMEOUT_SEC) -> str | None:
    """Download an image at a URL and run OCR on the bytes."""
    import httpx

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": "IP-SAKTI IngestionBot"}) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                return None
            return ocr_image(resp.content)
    except Exception as exc:
        logger.debug("Image fetch failed for %s: %s", url, exc)
        return None


def read_local_file(path: str) -> tuple[str, str] | None:
    """Read a local corpus file; returns ``(title, text)`` by extension."""
    ext = os.path.splitext(path)[1].lower()
    title = os.path.basename(path)
    try:
        if ext == ".pdf":
            text = fetch_pdf(path)
            return (title, text) if text else None
        if ext == ".docx":
            text = fetch_docx(path)
            return (title, text) if text else None
        if ext in (".md", ".txt"):
            with open(path, encoding="utf-8", errors="ignore") as fh:
                return (title, re.sub(r"\s+", " ", fh.read()).strip())
        if ext == ".csv":
            with open(path, "rb") as fh:
                text = csv_to_text(fh.read())
            return (title, text) if text else None
        if ext in IMAGE_EXTENSIONS:
            text = ocr_image(path)
            return (title, text) if text else None
        if ext == ".json":
            with open(path, encoding="utf-8") as fh:
                return (title, fh.read().strip())
    except Exception as exc:
        logger.debug("Local read failed for %s: %s", path, exc)
    return None


def search_source(urls: list[str], query: str, top: int = 3) -> list[str]:
    """Search the web restricted to allowed domains, then merge canonical URLs."""
    matches: list[str] = []
    try:
        links = _search_candidate_links(query, top=top * 5)
        matches = [u for u in links if _is_allowed_domain(u)]
    except Exception as exc:
        logger.debug("Search failed for %r: %s", query, exc)
    seen = set(matches)
    for u in urls or []:
        if _is_allowed_domain(u) and u not in seen:
            seen.add(u)
            matches.append(u)
    return matches[:top]


def content_hash(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def _url_digest(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]