"""A6 - Form I / Form II prefilling with read-back verification.

A patent application form is a legal document. This service therefore never
*authors* content: it only **copies values that already exist** in the
Innovation Passport or the user record, and every field carries provenance.

Field statuses:
- ``filled``        - copied from a real source, verified by read-back.
- ``needs_input``   - the form needs data we do not have (inventor address,
                      applicant legal name). Left blank on purpose.
- ``needs_review``  - derived (e.g. an abstract assembled from two fields) and
                      must be confirmed by a human before filing.

``read_back()`` re-reads a draft and re-derives each filled value from its
source, so any hallucinated field fails the check. Nothing is signed or filed.
"""

from __future__ import annotations

import time
from typing import Any

from app.services.passport_engine import PassportEngine

FILLED = "filled"
NEEDS_INPUT = "needs_input"
NEEDS_REVIEW = "needs_review"

FORM_NOTE = (
    "Field mapping follows the published IP India patent forms. Verify the current "
    "form version on ipindia.gov.in before filing."
)

DISCLAIMER = (
    "DRAFT - prefilled for human completion. IP-SAKTI does not file documents and "
    "this is not legal advice. A qualified patent agent must review every field."
)

# Field spec per form: (field key, label, source key, status)
FORM_FIELDS: dict[str, list[tuple[str, str, str, str]]] = {
    "form1": [
        ("applicant_name", "Name of applicant", "applicant_name", NEEDS_INPUT),
        ("applicant_address", "Address of applicant", "applicant_address", NEEDS_INPUT),
        ("applicant_nationality", "Nationality of applicant", "applicant_nationality", NEEDS_INPUT),
        ("title_of_invention", "Title of invention", "case_title", FILLED),
        ("brief_description", "Brief description of the invention", "claimed_innovation", FILLED),
        ("summary_of_invention", "Summary of the invention", "intended_use", NEEDS_REVIEW),
        ("classifications", "Classification (IPC/CPC)", "classifications", NEEDS_INPUT),
        ("number_of_claims", "Number of claims", "proposed_claims", FILLED),
        ("invention_details", "Details of the invention", "process_description", FILLED),
    ],
    "form2": [
        ("applicant_name", "Name of applicant", "applicant_name", NEEDS_INPUT),
        ("title_of_invention", "Title of invention", "case_title", FILLED),
        ("number_of_claims", "Number of claims", "proposed_claims", FILLED),
    ],
}

CLAIM_FIELDS: dict[str, list[str]] = {
    "form2": [
        "claim_1",
        "claim_2",
        "claim_3",
        "claim_4",
        "claim_5",
        "claim_6",
        "claim_7",
        "claim_8",
        "claim_9",
        "claim_10",
    ],
}


class PrefillError(RuntimeError):
    """Raised when a form cannot be prefilled at all."""


def supported_forms() -> list[dict[str, Any]]:
    return [
        {
            "form": "form1",
            "title": "Form I - Application for grant of patent",
            "fields": [f[0] for f in FORM_FIELDS["form1"]],
            "note": FORM_NOTE,
        },
        {
            "form": "form2",
            "title": "Form II - Statement of claims",
            "fields": [f[0] for f in FORM_FIELDS["form2"]]
            + [c for c in CLAIM_FIELDS["form2"] if c not in {f[0] for f in FORM_FIELDS["form2"]}],
            "note": FORM_NOTE,
        },
    ]


def _source_values(passport: Any, applicant: dict[str, Any] | None) -> dict[str, Any]:
    claims = list(getattr(passport, "proposed_claims", []) or [])
    values: dict[str, Any] = {
        "case_title": getattr(passport, "case_title", ""),
        "claimed_innovation": getattr(passport, "claimed_innovation", "") or "",
        "intended_use": getattr(passport, "intended_use", "") or "",
        "process_description": getattr(passport, "process_description", "") or "",
        "proposed_claims": claims,
        "applicant_name": (applicant or {}).get("name", ""),
        "applicant_address": (applicant or {}).get("address", ""),
        "applicant_nationality": (applicant or {}).get("nationality", ""),
        "classifications": (applicant or {}).get("classifications", ""),
    }
    if values["claimed_innovation"] and values["intended_use"]:
        values["summary_of_invention"] = (
            f"{values['claimed_innovation']} Intended use: {values['intended_use']}"
        )
    return values


def _field_status(value: Any, declared: str) -> str:
    """A field with a real source value is filled; the declared ``needs_input``
    status only survives when the source genuinely has nothing."""
    if value in (None, "", [], {}):
        return NEEDS_INPUT
    if declared == NEEDS_REVIEW:
        return NEEDS_REVIEW
    return FILLED


def prefill_form(
    passport_id: str,
    form: str = "form1",
    applicant: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prefill ``form`` from the passport; unknown forms raise."""
    spec = FORM_FIELDS.get(form)
    if spec is None:
        raise PrefillError(f"unsupported form: {form}")

    passport = PassportEngine.get_passport(passport_id)
    if passport is None:
        raise PrefillError(f"passport not found: {passport_id}")

    values = _source_values(passport, applicant)
    fields: dict[str, dict[str, Any]] = {}
    for key, label, source_key, declared in spec:
        value = values.get(source_key)
        if key == "number_of_claims":
            value = len(values.get("proposed_claims") or [])
        status = _field_status(value, declared)
        fields[key] = {
            "label": label,
            "value": value if status != NEEDS_INPUT else None,
            "source": f"passport.{source_key}" if source_key != "applicant_name" else "applicant.record",
            "status": status,
        }

    if form == "form2":
        claims = values.get("proposed_claims") or []
        for index, key in enumerate(CLAIM_FIELDS["form2"]):
            if index < len(claims):
                fields[key] = {
                    "label": f"Claim {index + 1}",
                    "value": claims[index],
                    "source": "passport.proposed_claims",
                    "status": FILLED,
                }
            else:
                fields[key] = {
                    "label": f"Claim {index + 1}",
                    "value": None,
                    "source": "passport.proposed_claims",
                    "status": NEEDS_INPUT,
                }

    missing = [k for k, f in fields.items() if f["status"] == NEEDS_INPUT]
    review = [k for k, f in fields.items() if f["status"] == NEEDS_REVIEW]

    from app.services.dossier_service import content_hash

    draft = {
        "form": form,
        "form_title": next(t["title"] for t in supported_forms() if t["form"] == form),
        "status": "DRAFT",
        "disclaimer": DISCLAIMER,
        "form_note": FORM_NOTE,
        "passport_id": passport_id,
        "case_title": getattr(passport, "case_title", ""),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "fields": fields,
        "missing_fields": missing,
        "review_fields": review,
        "sign_off": {
            "required": True,
            "signed_by": None,
            "signed_at": None,
            "note": "Must be completed by a qualified patent agent before filing.",
        },
    }
    draft["content_hash"] = content_hash(render_form_text(draft))
    return draft


def render_form_text(draft: dict[str, Any]) -> str:
    lines = [f"{draft['form_title']}", f"Status: {draft['status']} - {draft['disclaimer']}", ""]
    for key, field in draft["fields"].items():
        mark = {"filled": "[x]", "needs_review": "[?]", "needs_input": "[ ]"}[field["status"]]
        value = field["value"] if field["value"] not in (None, "") else "________"
        lines.append(f"{mark} {field['label']} ({key}): {value}  <- {field['source']}")
    return "\n".join(lines)


def read_back(draft: dict[str, Any]) -> dict[str, Any]:
    """Verify every filled field against its source; flag anything untraceable."""
    passport = PassportEngine.get_passport(str(draft.get("passport_id") or ""))
    values = _source_values(passport, None) if passport is not None else {}

    checked: list[dict[str, Any]] = []
    untraceable: list[str] = []
    for key, field in draft.get("fields", {}).items():
        value = field.get("value")
        if field.get("status") == NEEDS_INPUT:
            checked.append({"field": key, "status": NEEDS_INPUT, "verified": True, "note": "blank by design"})
            continue
        source = str(field.get("source", ""))
        origin: Any = values.get(source.split(".", 1)[-1]) if source.startswith("passport.") else None
        if source.startswith("passport.proposed_claims") and key.startswith("claim_"):
            index = int(key.split("_")[1]) - 1
            claims = values.get("proposed_claims") or []
            origin = claims[index] if 0 <= index < len(claims) else None
        if key == "number_of_claims":
            origin = len(values.get("proposed_claims") or [])
        verified = origin is not None and str(origin) == str(value)
        if not verified:
            untraceable.append(key)
        checked.append(
            {
                "field": key,
                "status": field.get("status"),
                "source": source,
                "value": value,
                "source_value": None if origin is None else str(origin)[:200],
                "verified": verified,
            }
        )

    filled = [c for c in checked if c["status"] in (FILLED, NEEDS_REVIEW)]
    return {
        "form": draft.get("form"),
        "passport_id": draft.get("passport_id"),
        "checked": len(checked),
        "filled_checked": len(filled),
        "untraceable_fields": untraceable,
        "traceable": not untraceable,
        "ready_for_human_review": not untraceable,
        "results": checked,
    }


def save_prefill_record(
    db: Any,
    passport_id: str,
    user_id: str | None,
    draft: dict[str, Any],
) -> Any:
    from app.models.db_models import GeneratedDocumentDB

    row = GeneratedDocumentDB(
        passport_id=passport_id,
        user_id=user_id,
        kind="form",
        form_code=str(draft["form"]),
        doc_format="json",
        status="DRAFT",
        content_hash=str(draft["content_hash"]),
        citation_count=0,
        missing_field_count=len(draft.get("missing_fields") or []),
        summary={
            "form_title": draft["form_title"],
            "case_title": draft.get("case_title", ""),
            "generated_at": draft["generated_at"],
            "review_fields": draft.get("review_fields", []),
            "traceable": read_back(draft)["traceable"],
        },
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
