"""B4 — hash-chained, append-only audit trail (DPDP accountability).

Every security-relevant event is appended as an entry whose ``entry_hash``
covers ``prev_hash + ts + event_type + actor_hash + payload``. Verification
walks the chain and recomputes each link, so edited or deleted rows are
detected immediately. The actor is stored only as a salted hash and payloads
must contain hashed identifiers — never raw personal data.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.db_models import AuditLogEntry, ChatHistory

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64
_ACTOR_SALT = "ipsakti-audit-actor-v1"


def actor_hash(actor_id: str | None) -> str:
    """Salted SHA-256 of the acting user id (the raw id is never stored)."""
    raw = f"{_ACTOR_SALT}:{actor_id or 'anonymous'}"
    return hashlib.sha256(raw.encode()).hexdigest()


def compute_entry_hash(
    prev_hash: str,
    event_type: str,
    actor: str,
    ts_iso: str,
    payload_json: str,
) -> str:
    material = "|".join((prev_hash, ts_iso, event_type, actor, payload_json))
    return hashlib.sha256(material.encode()).hexdigest()


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def record_event(
    db: Session,
    event_type: str,
    payload: dict[str, Any],
    actor_id: str | None = None,
) -> AuditLogEntry:
    """Append one tamper-evident entry; payload must hold hashes/metadata only."""
    last = (
        db.query(AuditLogEntry)
        .order_by(AuditLogEntry.id.desc())
        .first()
    )
    prev_hash = str(last.entry_hash) if last else GENESIS_HASH
    ts_iso = datetime.now(UTC).isoformat(timespec="seconds")
    actor = actor_hash(actor_id)
    payload_json = _canonical(payload)
    entry = AuditLogEntry(
        ts=ts_iso,
        event_type=str(event_type)[:64],
        actor_hash=actor,
        payload=payload_json,
        prev_hash=prev_hash,
        entry_hash=compute_entry_hash(
            prev_hash, event_type, actor, ts_iso, payload_json
        ),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_chain(db: Session) -> dict[str, Any]:
    """Recompute the whole chain; reports the first broken link if any."""
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.id.asc()).all()
    prev = GENESIS_HASH
    for entry in entries:
        expected = compute_entry_hash(
            prev,
            str(entry.event_type),
            str(entry.actor_hash),
            str(entry.ts),
            str(entry.payload),
        )
        if str(entry.prev_hash) != prev or str(entry.entry_hash) != expected:
            return {
                "valid": False,
                "checked": len(entries),
                "first_broken_id": entry.id,
            }
        prev = str(entry.entry_hash)
    return {"valid": True, "checked": len(entries), "first_broken_id": None}


def chain_head(db: Session) -> str:
    """Latest entry hash (or the genesis hash for an empty chain)."""
    last = db.query(AuditLogEntry).order_by(AuditLogEntry.id.desc()).first()
    return str(last.entry_hash) if last else GENESIS_HASH


def purge_expired_chat(db: Session, retention_days: int = 90) -> int:
    """DPDP retention: delete chat records past their retention deadline."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=retention_days)
    removed = 0
    for row in db.query(ChatHistory).all():
        if row.retention_until is not None:
            deadline = row.retention_until
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            expired = deadline <= now
        elif row.created_at is not None:
            created = row.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            expired = created < cutoff
        else:
            expired = False
        if expired:
            db.delete(row)
            removed += 1
    if removed:
        db.commit()
    return removed


@event.listens_for(Session, "before_flush")
def _reject_audit_mutation(
    session: Session, flush_context: Any, instances: Any
) -> None:
    """Audit rows are append-only: UPDATE/DELETE raise before hitting disk."""
    for obj in session.dirty:
        if isinstance(obj, AuditLogEntry) and session.is_modified(obj):
            raise ValueError("audit log entries are append-only (immutable)")
    for obj in session.deleted:
        if isinstance(obj, AuditLogEntry):
            raise ValueError("audit log entries are append-only (immutable)")
