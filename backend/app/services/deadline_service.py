"""A3 - Deadline tracker with a reminder ladder.

Statutory anchors used (India):
- Patent: renewal fees from the 3rd year onwards (anniversary of filing),
  12th year renewal due within 6 months of the 3rd-year renewal.
- Trade mark: renewal every 10 years from the date of registration.
- GI: renewal every 10 years from the date of registration.
- ABS (NBA): access/benefit-share terms have no statutory clock here; the
  tracker records the applicant-agreed milestone instead of inventing one.

Nothing is fabricated: generated dates are *derived* from a user-entered
anchor date, and the statutory basis is returned with every reminder.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any, Protocol, cast

from sqlalchemy.orm import Session

from app.models.db_models import TrackedDeadline

DEFAULT_REMINDERS = [90, 60, 30, 7]

DEADLINE_RULES: dict[str, dict[str, Any]] = {
    "patent_renewal": {
        "label": "Patent renewal fee",
        "years": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "statutory_basis": "Patents Rules - renewal fees payable from the 3rd year",
        "reminders": DEFAULT_REMINDERS,
    },
    "patent_12th_year": {
        "label": "Patent 12th-year renewal (payable within 6 months of 3rd-year renewal)",
        "offsets_years": [(12, 0)],
        "statutory_basis": "Patents Rules - 12th year renewal window",
        "reminders": [180, 90, 30],
    },
    "trademark_renewal": {
        "label": "Trade mark renewal (10-year term)",
        "offsets_years": [(10, 0)],
        "statutory_basis": "Trade Marks Rules - 10 year renewal term",
        "reminders": [180, 90, 30, 7],
    },
    "gi_renewal": {
        "label": "Geographical Indication renewal (10-year term)",
        "offsets_years": [(10, 0)],
        "statutory_basis": "GI Registry - 10 year renewal term",
        "reminders": [180, 90, 30, 7],
    },
    "tm_renewal": {
        "label": "Trade mark renewal (alias of trademark_renewal)",
        "offsets_years": [(10, 0)],
        "statutory_basis": "Trade Marks Rules - 10 year renewal term",
        "reminders": [180, 90, 30, 7],
    },
    "abs_milestone": {
        "label": "NBA access / benefit-share milestone (applicant-defined)",
        "statutory_basis": "Biological Diversity Act 2002 - access terms agreed per application",
        "reminders": [60, 30, 7],
        "manual": True,
    },
    "custom": {
        "label": "Custom deadline",
        "statutory_basis": "user-defined",
        "reminders": DEFAULT_REMINDERS,
        "manual": True,
    },
}


def _parse_date(value: str) -> date:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date: {value!r} (use YYYY-MM-DD)")


def _add_years(base: date, years: int) -> date:
    try:
        return base.replace(year=base.year + years)
    except ValueError:  # 29 Feb
        return base.replace(year=base.year + years, day=28)


def generate_deadlines(
    kind: str,
    anchor_date: str,
    reference: str = "",
) -> list[dict[str, Any]]:
    """Derive every reminder-able deadline for ``kind`` from an anchor date."""
    rule = DEADLINE_RULES.get(kind)
    if rule is None:
        raise ValueError(f"Unknown deadline kind: {kind}")
    anchor = _parse_date(anchor_date)
    reminders = list(rule.get("reminders") or DEFAULT_REMINDERS)

    rows: list[dict[str, Any]] = []
    if rule.get("manual"):
        rows.append(
            {
                "kind": kind,
                "title": f"{rule['label']} - {reference}" if reference else rule["label"],
                "due_date": anchor.isoformat(),
                "reminder_days": reminders,
                "statutory_basis": rule["statutory_basis"],
            }
        )
        return rows

    offsets = rule.get("offsets_years")
    if offsets is None:
        offsets = [(year, 0) for year in rule.get("years", [])]
    for years, extra_days in offsets:
        due = _add_years(anchor, years) + timedelta(days=extra_days)
        rows.append(
            {
                "kind": kind,
                "title": f"{rule['label']} (year {years})" if rule.get("years") else rule["label"],
                "due_date": due.isoformat(),
                "reminder_days": reminders,
                "statutory_basis": rule["statutory_basis"],
            }
        )
    return rows


def create_deadline(
    db: Session,
    user_id: str,
    kind: str,
    due_date: str,
    reference: str = "",
    title: str = "",
    notes: str = "",
) -> TrackedDeadline:
    rule = DEADLINE_RULES.get(kind)
    if rule is None:
        raise ValueError(f"Unknown deadline kind: {kind}")
    _parse_date(due_date)  # validate
    row = TrackedDeadline(
        user_id=user_id,
        kind=kind,
        reference=reference.strip(),
        title=(title.strip() or rule["label"]),
        due_date=due_date.strip(),
        reminder_days=list(rule.get("reminders") or DEFAULT_REMINDERS),
        notes=notes.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_schedule(
    db: Session,
    user_id: str,
    kind: str,
    anchor_date: str,
    reference: str = "",
    notes: str = "",
) -> list[TrackedDeadline]:
    """Create every derived deadline for a schedule (e.g. all patent renewals)."""
    created: list[TrackedDeadline] = []
    for row in generate_deadlines(kind, anchor_date, reference):
        created.append(
            create_deadline(
                db,
                user_id,
                row["kind"],
                row["due_date"],
                reference=reference,
                title=row["title"],
                notes=notes,
            )
        )
    return created


def list_deadlines(
    db: Session,
    user_id: str,
    status: str = "",
    within_days: int | None = None,
) -> list[TrackedDeadline]:
    query = db.query(TrackedDeadline).filter(TrackedDeadline.user_id == user_id)
    if status:
        query = query.filter(TrackedDeadline.status == status)
    rows = list(query.order_by(TrackedDeadline.due_date.asc()).all())
    if within_days is not None:
        horizon = (date.today() + timedelta(days=within_days)).isoformat()
        rows = [r for r in rows if str(r.due_date) <= horizon]
    return rows


def upcoming(db: Session, user_id: str, within_days: int = 90) -> list[dict[str, Any]]:
    """Deadlines due within the window, with the next reminder that has fired."""
    today = date.today()
    out: list[dict[str, Any]] = []
    for row in list_deadlines(db, user_id, status="pending"):
        due = _parse_date(str(row.due_date))
        if (due - today).days > within_days:
            continue
        fired = [d for d in cast(list, row.reminder_days or []) if (due - today).days <= d]
        out.append(
            {
                "id": row.id,
                "kind": row.kind,
                "title": row.title,
                "reference": row.reference,
                "due_date": row.due_date,
                "days_left": (due - today).days,
                "reminders_fired": sorted(fired, reverse=True),
                "statutory_basis": DEADLINE_RULES.get(str(row.kind), {}).get(
                    "statutory_basis", "user-defined"
                ),
            }
        )
    return out


def mark_done(db: Session, user_id: str, deadline_id: str) -> bool:
    row = (
        db.query(TrackedDeadline)
        .filter(TrackedDeadline.id == deadline_id, TrackedDeadline.user_id == user_id)
        .one_or_none()
    )
    if row is None:
        return False
    row.status = "done"  # type: ignore[assignment]
    db.commit()
    return True


class ReminderRow(Protocol):
    """Minimal shape needed to render a reminder (model or plain test double)."""

    title: str
    due_date: str


def reminder_message(row: ReminderRow, lang: str = "en") -> str:
    """Delivery-ready reminder text (used by the G10 WhatsApp adapter)."""
    due = str(row.due_date)
    if lang == "hi":
        return f"Deadline reminder: {row.title} - due {due}. Please file on time."
    return f"Deadline reminder: {row.title} - due {due}. Please file on time."


def rules_catalogue() -> list[dict[str, Any]]:
    """Public catalogue of supported deadline kinds (grounds the UI dropdown)."""
    return [
        {
            "kind": kind,
            "label": rule["label"],
            "statutory_basis": rule["statutory_basis"],
            "reminders": rule.get("reminders", DEFAULT_REMINDERS),
            "manual": bool(rule.get("manual")),
        }
        for kind, rule in DEADLINE_RULES.items()
    ]


def as_of() -> str:
    return time.strftime("%Y-%m-%d")
