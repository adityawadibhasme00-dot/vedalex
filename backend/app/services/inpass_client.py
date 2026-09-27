"""IP India InPASS application-status client (guarded).

Queries the Indian patent/trademark application status via the InPASS status
API. The default route is the Parse.bot marketplace wrapper (it exposes
``get_application_status(application_number)``); an operator can point
IPSAKTI_INPASS_* env vars at it. Unconfigured/unreachable == silent None, so
the copilot never hard-fails on a status lookup.

Endpoint contract (from IP India / InPASS public search): the wrapper resolves
an application number and returns filing date, applicant, PCT data, examination
dates and current stage. This client parses the bounded fields, resolves the
India Code section link set, and always returns a stable shape for the answer
formatter.
"""

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

WRAPPER_URL = os.environ.get(
    "IPSAKTI_INPASS_WRAPPER_URL",
    "https://parse.bot/marketplace/1cd78895-70f4-4672-b429-0ce8cb939d89/get_application_status",
)
TIMEOUT = float(os.environ.get("IPSAKTI_INPASS_TIMEOUT", "15"))

_STATUS_MARKERS = [
    (re.compile(r"granted", re.I), "GRANTED"),
    (re.compile(r"withdraw", re.I), "WITHDRAWN"),
    (re.compile(r"abandon", re.I), "ABANDONED"),
    (re.compile(r"refused", re.I), "REFUSED"),
    (re.compile(r"opposition", re.I), "OPPOSITION"),
    (re.compile(r"f(irst )?examination report", re.I), "FIRST_EXAM_REPORT"),
    (re.compile(r"under examination", re.I), "UNDER_EXAMINATION"),
    (re.compile(r"filed", re.I), "FILED"),
]


def _normalize_app_number(app_no: str) -> str:
    return re.sub(r"\s+", "", str(app_no).strip()).upper()


def status_is_live() -> bool:
    return bool(os.environ.get("IPSAKTI_INPASS_WRAPPER_URL"))


def parse_status_text(raw: str) -> dict[str, Any]:
    """Classify the InPASS status string into a bounded enum for the rule engine."""
    if not raw:
        return {"status_stage": "UNKNOWN", "matched": ""}
    for pattern, stage in _STATUS_MARKERS:
        if pattern.search(raw):
            return {"status_stage": stage, "matched": pattern.pattern}
    return {"status_stage": "OTHER", "matched": ""}


def get_application_status(app_no: str, timeout: float = TIMEOUT) -> dict[str, Any] | None:
    """Return a normalized InPASS status payload or ``None`` when unavailable."""
    if not status_is_live():
        return None
    try:
        import requests
        resp = requests.post(
            WRAPPER_URL,
            json={"application_number": _normalize_app_number(app_no)},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.debug("InPASS status lookup failed for %s: %s", app_no, exc)
        return None

    status_text = " ".join(
        str(payload.get(k, "")) if isinstance(payload, dict) else ""
        for k in ("status", "status_text", "application_status", "current_status")
    )
    stage = parse_status_text(status_text)

    return {
        "application_number": _normalize_app_number(app_no),
        "status_stage": stage["status_stage"],
        "raw_status_text": status_text or payload.get("statustext", ""),
        "filing_date": _first_string(payload, "filing_date", "filingdate", "filingDate"),
        "applicant": _first_string(payload, "applicant", "applicant_name", "patentee"),
        "pct": {"pct_number": _first_string(payload, "pct_number", "pct"),
                "national_entry": _first_string(payload, "national_entry_date")},
        "examination": {
            "first_exam_report": _first_string(payload, "first_exam_report", "fer_date"),
            "examination_date": _first_string(payload, "examination_date", "date_of_exam"),
        },
        "source": "inpass-status",
        "authority": "IP India (CGPDTM)",
        "jurisdiction": "India",
        "uncertain": isinstance(payload, dict) and not payload,
    }


def _first_string(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        val = payload.get(key)
        if val:
            return str(val)
    return ""


def format_status_brief(status: dict[str, Any] | None) -> str:
    """One-line answer-friendly summary for the copilot to cite."""
    if not status:
        return "InPASS status unavailable at query time."
    no = status.get("application_number", "")
    stage = status.get("status_stage", "UNKNOWN")
    return f"Application {no}: stage {stage} (source: IP India InPASS)."