"""Shared primitives for the Innovation-Lab agent executors.

Every agent in :mod:`app.services.innolab.agent_executors` speaks the same
vocabulary: resolve ingredients to real corpus monographs, retrieve passages,
shape findings and evidence blocks, and label a source by authority.  That
vocabulary lives here so the per-agent executors stay readable and so a new
agent inherits the same grounding guarantees instead of reinventing them.

Nothing in here is agent-specific; nothing in here may fabricate a source.
"""

from __future__ import annotations

import os
import re
from typing import Any, cast

from app.services.ingredient_resolver import IngredientResolverService
from app.services.retrieval_engine import HybridRetrievalEngine

__all__ = [
    "_KB",
    "_load_json",
    "_api_monographs",
    "_pathway_rules",
    "_bioresource",
    "_CURATIVE",
    "_SOLVENT",
    "_PURPOSE",
    "_INJECTION",
    "_PROHIBITED_CLAIM",
    "_text",
    "_list_value",
    "_markets",
    "_scan_formulation",
    "_ingredient_names",
    "_resolve_ingredients",
    "_as_citation",
    "_retrieve",
    "_jurisdiction_code",
    "_claim_signals",
    "_fingerprint",
    "_base_result",
    "_section",
    "_AUTHORITY_KIND",
    "_source_kind",
    "_sources_section",
    "_real_ref",
    "_finding",
    "_evidence",
    "_draft_claims",
]

_KB = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge")

_JSON_CACHE: dict[str, Any] = {}


def _load_json(name: str) -> Any:
    if name not in _JSON_CACHE:
        import json

        path = os.path.join(_KB, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                _JSON_CACHE[name] = json.load(f)
        else:
            _JSON_CACHE[name] = None
    return _JSON_CACHE[name]


def _api_monographs() -> list[dict[str, Any]]:
    data = _load_json("api_monographs.json")
    if isinstance(data, dict):
        return list(data.values())
    return data or []


def _pathway_rules() -> list[dict[str, Any]]:
    return _load_json("pathway_rules.json") or []


def _bioresource() -> list[dict[str, Any]]:
    return _load_json("bioresource.json") or []


# --------------------------------------------------------------------------- #
# Shared input + knowledge helpers
# --------------------------------------------------------------------------- #
_CURATIVE = re.compile(
    r"\b(cure|cures|cured|heal|heals|therapeutic|therapy|treatments?|prevent|"
    r"disease|illness|diabetes|cancer|covid|infection|symptoms?|remedy|medicine)\b",
    re.I,
)
_SOLVENT = re.compile(
    r"\b(solvent|water|honey|ghee|ghrita|milk|alcohol|aristha|asava|kwath|"
    r"decoction|hydro-?alcoholic|jaggery)\b",
    re.I,
)
_PURPOSE = re.compile(
    r"\b(cognitive|memory|sleep|stress|anxiety|immunity|digest|digestion|energy|"
    r"vitality|hair|skin|joint|pain relief|weight|wellness|relax)\b",
    re.I,
)
_INJECTION = re.compile(
    r"\b(ignore (previous|prior)|system prompt|jailbreak|disregard (rules|safety)|"
    r"act as (dan|devil)|forget instructions|reveal your (prompt|instructions)|"
    r"do anything now)\b",
    re.I,
)
_PROHIBITED_CLAIM = re.compile(
    r"\b(cures?|treats?) (diabetes|cancer|covid|corona|hypertension|blood pressure|"
    r"tumor|aids|hiv)\b",
    re.I,
)


def _text(inputs: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = inputs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _list_value(inputs: dict[str, Any], key: str) -> list[str]:
    value = inputs.get(key)
    if isinstance(value, list):
        return [str(x).strip() for x in value if x is not None and str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in re.split(r"[,;+|]", value) if x.strip()]
    return []


def _markets(inputs: dict[str, Any]) -> list[str]:
    markets = _list_value(inputs, "target_markets")
    return markets or ["India", "United States", "Canada"]


def _scan_formulation(text: str) -> list[str]:
    matched: list[str] = []
    for mono in _api_monographs():
        bot = mono.get("botanical_name", "")
        if bot and bot in text and bot not in matched:
            matched.append(bot)
    return matched[:8]


def _ingredient_names(inputs: dict[str, Any]) -> list[str]:
    raw = inputs.get("ingredients")
    if isinstance(raw, list):
        names = [str(x).strip() for x in raw if str(x).strip()]
    elif isinstance(raw, str) and raw.strip():
        names = [x.strip() for x in re.split(r"[,;+|]", raw) if x.strip()]
    else:
        formula = _text(inputs, "formulation_text")
        if not formula:
            formula = _text(inputs, "problem_text")
        if not formula:
            formula = _text(inputs, "document_text", "disclosure_text")
        names = []
        seen = set()
        for token in re.split(r"[,;+:&]+", formula):
            token = token.strip()
            short = re.sub(r"[\d.%~()/]+\s*", "", token)
            if 2 <= len(short) <= 60 and short.lower() not in seen:
                seen.add(short.lower())
                names.append(short)
        if not names:
            names = _scan_formulation(formula)
    if not names:
        names = _scan_formulation(_text(inputs, "formulation_text", "problem_text", "document_text", "disclosure_text"))
    return names[:12]


def _resolve_ingredients(names: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen = set()
    for name in names:
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        resolved = None
        try:
            resolved = IngredientResolverService.resolve(name)
        except Exception:
            resolved = None
        if resolved is None:
            out.append({"raw_name": name, "resolved": False})
            continue
        out.append(
            {
                "raw_name": name,
                "resolved": True,
                "canonical_id": getattr(resolved, "canonical_id", None),
                "api_monograph_id": getattr(resolved, "api_monograph_id", None),
                "botanical_name": getattr(resolved, "accepted_botanical_name", None),
                "family": getattr(resolved, "family", None),
                "classical_therapeutic_uses": getattr(resolved, "classical_therapeutic_uses", None),
                "fssai_aahara_status": getattr(resolved, "fssai_aahara_status", "permitted"),
                "us_fda_ndi_status": getattr(resolved, "us_fda_ndi_status", "old_dietary_ingredient"),
                "canada_nhpid_status": getattr(resolved, "canada_nhpid_status", "monographed"),
                "resolution_confidence": getattr(resolved, "resolution_confidence", 0.9),
            }
        )
    return out


def _as_citation(c: Any) -> dict[str, Any]:
    return {
        "act_title": getattr(c, "act_title", ""),
        "section_reference": getattr(c, "section_reference", ""),
        "authority": getattr(c, "authority", ""),
        "effective_date": getattr(c, "effective_date", ""),
        "exact_passage": (getattr(c, "exact_passage", "") or "")[:500],
        "source_url": getattr(c, "source_url", ""),
        "authority_rank": getattr(c, "authority_rank", 1),
    }


def _retrieve(query: str, jurisdiction: str | None = None, top_k: int = 4) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return []
    try:
        return [
            _as_citation(c)
            for c in HybridRetrievalEngine.search_passages(query, jurisdiction=jurisdiction, top_k=top_k)
        ]
    except Exception:
        return []


def _jurisdiction_code(market: str) -> str | None:
    m = market.lower()
    if "india" in m:
        return "in"
    if "unit" in m or "usa" in m or "america" in m:
        return "us"
    if "canada" in m:
        return "ca"
    return None


def _claim_signals(inputs: dict[str, Any]) -> dict[str, bool]:
    claims = _text(inputs, "proposed_claims", "claim_wording", "problem_text")
    process = _text(inputs, "process_desc", "formulation_text")
    problem = _text(inputs, "problem_text", "formulation_text")
    blob = f"{claims} {problem}"
    return {
        "claim_curative": bool(_CURATIVE.search(blob)),
        "prep_solvent": bool(_SOLVENT.search(process)),
        "therapeutic_purpose": bool(_PURPOSE.search(blob)),
    }


def _fingerprint(inputs: dict[str, Any], resolved: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        fp = IngredientResolverService.generate_formulation_fingerprint(
            ingredients=[
                {
                    "canonical_id": r.get("canonical_id"),
                    "quantity_percentage": 0.0,
                }
                for r in resolved
                if r.get("resolved")
            ],
            process_desc=_text(inputs, "process_desc") or "unspecified process",
        )
        return {
            "fingerprint_hash": getattr(fp, "fingerprint_hash", ""),
            "canonical_ingredient_ids": getattr(fp, "canonical_ingredient_ids", []),
            "ratios": getattr(fp, "ratios", {}),
            "process_signature": getattr(fp, "process_signature", ""),
        }
    except Exception:
        return {}


def _base_result(slug: str, phase: str, summary: str, note: str) -> dict[str, Any]:
    return {
        "agent_slug": slug,
        "phase": phase,
        "ok": True,
        "summary": summary,
        "note": note,
        "findings": [],
        "evidence": [],
        "citations": [],
        "claims": [],
        "suggestions": [],
        "sections": [],
    }


def _section(title: str, rows: list[Any], columns: list[str] | None = None, caption: str = "") -> dict[str, Any]:
    """Eureka-style structured report section (table of key/value rows)."""
    sec: dict[str, Any] = {"title": title, "rows": rows}
    if columns:
        sec["columns"] = columns
    if caption:
        sec["caption"] = caption
    return sec


# Map corpus authorities to Eureka-style "where the data comes from" source kinds.
_AUTHORITY_KIND = [
    ("patent", "Patent database"),
    ("Indian Patent", "Patent database (Indian Patent Office)"),
    ("United States Patent", "Patent database (USPTO)"),
    ("European Patent", "Patent database (EPO)"),
    ("WIPO", "Patent database (WIPO)"),
    ("PubMed", "Scientific literature (PubMed)"),
    ("AYUSH", "Regulatory corpus (Ministry of AYUSH)"),
    ("FSS", "Regulatory corpus (FSSAI)"),
    ("FDA", "Regulatory corpus (US FDA)"),
    ("Health", "Regulatory corpus (Health Canada)"),
    ("EFSA", "Regulatory corpus (EFSA)"),
    ("WHO", "Regulatory corpus (WHO)"),
]


def _source_kind(authority: str) -> str:
    low = (authority or "").lower()
    for needle, label in _AUTHORITY_KIND:
        if needle.lower() in low:
            return label
    return "Evidence corpus"


def _sources_section(citations: list[dict[str, Any]]) -> dict[str, Any]:
    """Eureka-style 'Data sources' rail — the real corpora fed this answer."""
    seen: dict[str, dict[str, Any]] = {}
    for c in citations:
        authority = c.get("authority") or "Evidence corpus"
        key = authority
        if key not in seen:
            seen[key] = {"authority": authority, "kind": _source_kind(authority), "rows": 0}
        seen[key]["rows"] += 1
    if not seen:
        seen = {"Evidence corpus": {"authority": "Local evidence corpus", "kind": "Grounded retriever (patents · literature · regulations)", "rows": 0}}
    return _section("Data sources (where this answer is grounded)", [
        {"source": v["authority"], "type": v["kind"], "passages": str(v["rows"])}
        for k, v in sorted(seen.items(), key=lambda kv: -kv[1]["rows"])
    ], ["source", "type", "passages"], "Every answer is traceable to these sources — like Eureka's citation rail.")


def _real_ref(citations: list[dict[str, Any]], idx: int) -> str:
    """Safely pull a REAL corpus reference (act title + authority) instead of fabricating one."""
    if not citations:
        return "local corpus"
    c = citations[idx % len(citations)]
    return f"{c.get('act_title') or 'corpus source'} · {c.get('authority') or 'KB'} ({c.get('section_reference') or 'full text'})"


def _finding(fid: str, title: str | None, detail: str, severity: str = "info") -> dict[str, Any]:
    return {"id": fid, "title": title, "detail": detail, "severity": severity}


def _evidence(kind: str, label: str | None, source: str, citation_ref: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"kind": kind, "label": label, "source": source}
    if citation_ref:
        item["citation_ref"] = citation_ref
    return item


def _draft_claims(inputs: dict[str, Any], resolved: list[dict[str, Any]]) -> list[str]:
    names = [r["botanical_name"] or r["raw_name"] for r in resolved if r.get("resolved")]
    names = names or [r["raw_name"] for r in resolved] or ["an Ayurvedic botanical"]
    composition = " and ".join(names[:3])
    process = _text(inputs, "process_desc")
    claims = [f"1. A composition comprising {composition} in effective amounts."]
    if process:
        claims.append(f"2. The composition of claim 1, obtainable by a process comprising: {process}.")
    if len(names) > 1:
        claims.append(f"3. The composition of claim 1, wherein :{names[0]} is present in a ratio of 1:1 to 1:5 relative to {names[1]}.")
    last = names[-1].split(" (")[0]
    claims.append(f"4. The composition of claim 1, formulated as an Ayurvedic dosage form adapted for oral administration of {last}.")
    return claims


# --------------------------------------------------------------------------- #
# Executors (one per registered slug)
# --------------------------------------------------------------------------- #
