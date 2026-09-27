"""A2 - Patent Watch: saved formulation profiles monitored for new prior art.

Turns the product from a one-shot Q&A into a recurring service: a weekly cycle
screens newly published patent records against every active watch profile and
raises MATCH / PARTIAL alerts.

Design rules (same anti-hallucination contract as the rest of IP-SAKTI):
- Deterministic ingredient-overlap scoring is the **floor**: alerts are always
  reproducible offline and testable without an LLM.
- An optional LLM comparator (prompt: ``app/prompts/patent_watch_prompt.txt``)
  may *enrich* advice text, never invent a patent number.
- Every hit stores the source URL that produced it for citation.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, cast

from sqlalchemy.orm import Session

from app.agents.base import AgentBase
from app.models.db_models import WatchHit, WatchProfile

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "and", "or", "of", "the", "for", "with", "powder", "extract", "oil",
    "seed", "root", "leaf", "juice", "paste", "formulation", "composition",
    "method", "process", "system", "device", "use", "used", "preparation",
}

MATCH_THRESHOLD = 0.34
PARTIAL_THRESHOLD = 0.15


def _tokens(values: list[str] | None) -> set[str]:
    out: set[str] = set()
    for value in values or []:
        for token in _TOKEN_RE.findall(str(value).lower()):
            if len(token) > 2 and token not in _STOPWORDS:
                out.add(token)
    return out


def normalize_ingredient(name: str) -> str:
    return " ".join(str(name or "").strip().lower().split())


def score_overlap(
    profile_ingredients: list[str] | None,
    profile_indication: str,
    patent_text: str,
) -> tuple[str, float, list[str]]:
    """Deterministic MATCH/PARTIAL/NO_MATCH decision for one patent record."""
    prof_tokens = _tokens(profile_ingredients)
    ind_tokens = _tokens([profile_indication])
    text = str(patent_text or "").lower()
    text_tokens = _tokens([text])

    if not prof_tokens:
        return "no_match", 0.0, []

    shared = sorted(prof_tokens & text_tokens)
    if not shared:
        return "no_match", 0.0, []

    score = len(shared) / len(prof_tokens)
    indication_hit = bool(ind_tokens & text_tokens)
    if indication_hit:
        score = min(1.0, score + 0.2)

    if score >= MATCH_THRESHOLD and indication_hit:
        kind = "match"
    elif score >= PARTIAL_THRESHOLD:
        kind = "partial"
    else:
        kind = "no_match"
    return kind, round(score, 3), shared


def _advice_for(kind: str, shared: list[str]) -> str:
    overlap = ", ".join(shared)
    if kind == "match":
        return (
            f"Prior-art overlap on {overlap} with the same indication. "
            "Escalate to a human IP facilitator for a freedom-to-operate review."
        )
    return (
        f"Ingredient overlap on {overlap} but a different use. "
        "Track it; consider a narrower claim scope."
    )


def create_profile(
    db: Session,
    user_id: str,
    title: str,
    ingredients: list[str],
    indication: str = "",
    classical_ref: str = "",
    passport_id: str | None = None,
) -> WatchProfile:
    cleaned = [normalize_ingredient(i) for i in ingredients if str(i).strip()]
    profile = WatchProfile(
        user_id=user_id,
        title=title.strip(),
        ingredients=cleaned,
        indication=indication.strip(),
        classical_ref=classical_ref.strip(),
        passport_id=passport_id,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def list_profiles(db: Session, user_id: str, status: str = "active") -> list[WatchProfile]:
    query = db.query(WatchProfile).filter(WatchProfile.user_id == user_id)
    if status:
        query = query.filter(WatchProfile.status == status)
    return list(query.all())


def delete_profile(db: Session, user_id: str, profile_id: str) -> bool:
    profile = (
        db.query(WatchProfile)
        .filter(WatchProfile.id == profile_id, WatchProfile.user_id == user_id)
        .one_or_none()
    )
    if profile is None:
        return False
    db.delete(profile)
    db.commit()
    return True


def load_prompt() -> str:
    from app.agents.base import load_prompt as _load

    try:
        return _load("patent_watch_prompt.txt")
    except (OSError, ValueError):
        return ""


class _WatchComparator(AgentBase):
    """LLM comparator used only to enrich advice text (never identifiers)."""

    name = "patent-watch-comparator"
    prompt_file = "patent_watch_prompt.txt"


def enrich_with_llm(profile: WatchProfile, patents: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Optional LLM pass that returns advice text only; never a patent number.

    Returns ``None`` whenever the provider is unavailable or the payload cannot
    be parsed, so the deterministic floor always stands on its own.
    """
    if not patents:
        return None
    try:
        payload = {
            "profile": {
                "title": profile.title,
                "ingredients": profile.ingredients,
                "indication": profile.indication,
                "classical_ref": profile.classical_ref,
            },
            "patents": [
                {k: p.get(k, "") for k in ("patent_no", "title", "abstract")}
                for p in patents
            ],
        }
        result = _WatchComparator().llm_json(
            json.dumps(payload, ensure_ascii=False), fallback={}
        )
    except Exception as exc:  # pragma: no cover - provider dependent
        logger.debug("watch LLM enrichment skipped: %s", exc)
        return None
    if not result or not isinstance(result.get("alerts"), list):
        return None
    known = {str(p.get("patent_no") or p.get("number") or "").strip() for p in patents}
    kept = [
        a
        for a in result["alerts"]
        if isinstance(a, dict) and str(a.get("patent_no", "")).strip() in known
    ]
    return {"alerts": kept, "summary_hi": result.get("summary_hi", ""), "summary_en": result.get("summary_en", "")}


def screen_patents(
    db: Session,
    profile: WatchProfile,
    patents: list[dict[str, Any]],
) -> list[WatchHit]:
    """Screen one profile against patent records; persists new hits only."""
    seen: set[str] = {
        str(row.patent_no)
        for row in db.query(WatchHit).filter(WatchHit.profile_id == profile.id).all()
    }
    hits: list[WatchHit] = []
    for record in patents or []:
        patent_no = str(record.get("patent_no") or record.get("number") or "").strip()
        if not patent_no or patent_no in seen:
            continue
        text = " ".join(
            str(record.get(key) or "")
            for key in ("title", "abstract", "claims_summary", "description")
        )
        kind, _score, shared = score_overlap(
            cast(list[str], profile.ingredients), cast(str, profile.indication), text
        )
        if kind == "no_match":
            continue
        hit = WatchHit(
            profile_id=profile.id,
            patent_no=patent_no,
            title=str(record.get("title") or "")[:400],
            match_kind=kind,
            overlap=", ".join(shared)[:400],
            advice=_advice_for(kind, shared)[:600],
            urgency="HIGH" if kind == "match" else "MEDIUM",
            source_url=str(record.get("source_url") or "")[:500],
        )
        db.add(hit)
        seen.add(patent_no)
        hits.append(hit)
    if hits:
        db.commit()
    return hits


NO_MATCH_HI = "Is hafte aapki formulation se koi naya patent publish nahi hua."


def build_digest(db: Session, user_id: str) -> dict[str, Any]:
    """Weekly digest for one user: alerts grouped per profile, Hindi + English."""
    profiles = list_profiles(db, user_id)
    sections: list[dict[str, Any]] = []
    total = 0
    for profile in profiles:
        hits = (
            db.query(WatchHit)
            .filter(WatchHit.profile_id == profile.id)
            .order_by(WatchHit.detected_at.desc())
            .all()
        )
        alerts = [
            {
                "patent_no": h.patent_no,
                "title": h.title,
                "match": h.match_kind,
                "overlap": h.overlap,
                "advice": h.advice,
                "urgency": h.urgency,
                "source_url": h.source_url,
            }
            for h in hits[:10]
        ]
        total += len(alerts)
        sections.append(
            {
                "profile_id": profile.id,
                "title": profile.title,
                "ingredients": profile.ingredients,
                "alert_count": len(alerts),
                "alerts": alerts,
            }
        )
    return {
        "user_id": user_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "profiles": len(profiles),
        "total_alerts": total,
        "sections": sections,
        "summary_hi": NO_MATCH_HI if total == 0 else f"Aapke {total} formulation(s) par {total} naye patent alert mile hain.",
        "summary_en": (
            "No new patent matching your formulation was published this week."
            if total == 0
            else f"{total} new patent alert(s) matched your watched formulation(s)."
        ),
    }


def run_watch_cycle(
    db: Session,
    patents: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Screen every active profile (or one user's) against ``patents``.

    ``patents=None`` means "no new publications in this cycle" - the cycle then
    only stamps ``last_checked_at``. Inject the week's records from the patent
    ingestion path (or the caller) to actually raise alerts.
    """
    query = db.query(WatchProfile).filter(WatchProfile.status == "active")
    if user_id:
        query = query.filter(WatchProfile.user_id == user_id)
    profiles = list(query.all())

    screened = 0
    hits_created = 0
    for profile in profiles:
        screened += 1
        if patents:
            hits_created += len(screen_patents(db, profile, patents))
        else:
            enrich = enrich_with_llm(profile, [])
            if enrich is not None:
                logger.debug("llm digest computed for profile %s", profile.id)
        profile.last_checked_at = time.strftime("%Y-%m-%dT%H:%M:%S")  # type: ignore[assignment]
    if profiles:
        db.commit()

    summary = {
        "ok": True,
        "profiles_screened": screened,
        "patents_considered": len(patents or []),
        "hits_created": hits_created,
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        from app.services.audit_chain import record_event

        record_event(
            db,
            "watch.cycle",
            {
                "profiles_screened": screened,
                "patents_considered": summary["patents_considered"],
                "hits_created": hits_created,
            },
        )
        db.commit()
    except Exception as exc:  # pragma: no cover - audit must not break the cycle
        logger.warning("watch cycle audit skipped: %s", exc)
    return summary


def digest_as_json(digest: dict[str, Any]) -> str:
    return json.dumps(digest, ensure_ascii=False, indent=2)
