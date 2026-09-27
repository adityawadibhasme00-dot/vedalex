import re
from typing import Any

ADVERSARIAL_INJECTION_PATTERNS = [
    r"(?i)\b(?:ignore|forget|disregard|override)\s+(?:all\s+)?(?:previous|prior|system)\s+instructions\b",
    r"(?i)\b(?:you\s+are\s+now|act\s+as|roleplay\s+as|system\s+prompt)\b",
    r"(?i)\b(?:mark|declare|certify|state)\s+this\s+(?:as\s+)?(?:patentable|compliant|approved|safe|novel)\b",
    r"(?i)\b(?:bypass|skip|disable)\s+(?:all\s+)?(?:checks|evaluations|filters|rules|safeties)\b",
    r"(?i)\b(?:treat\s+as\s+confidential\s+and\s+auto-approve)\b",
    r"(?i)\b(?:do\s+not\s+cite|suppress\s+citations)\b"
]

class DocumentSanitizer:
    """
    Sandboxes raw extracted OCR/PDF/label text to prevent prompt-injection attacks
    (Section 7.1.2). Strips imperatival instructions and produces typed factual schemas only.
    """
    _threat_log: list[dict[str, Any]] = []

    @classmethod
    def sanitize(cls, raw_text: str, source_filename: str = "document_upload") -> tuple[str, list[str]]:
        threats_found: list[str] = []
        cleaned_text = raw_text

        for pattern in ADVERSARIAL_INJECTION_PATTERNS:
            matches = re.findall(pattern, cleaned_text)
            if matches:
                threats_found.extend(matches)
                cleaned_text = re.sub(pattern, "[STRIPPED_POTENTIAL_INJECTION]", cleaned_text)

        if threats_found:
            cls._threat_log.append({
                "source": source_filename,
                "threats": threats_found,
                "status": "neutralized"
            })

        return cleaned_text, threats_found

    @classmethod
    def get_security_threat_log(cls) -> list[dict[str, Any]]:
        return cls._threat_log
