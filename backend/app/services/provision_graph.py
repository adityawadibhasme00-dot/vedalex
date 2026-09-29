"""Provision cross-reference graph.

Why this exists
---------------
Vector retrieval returns the section whose *text* matches the question. An
exception frequently lives in a different section that does not match the
question text at all — NBA approval under the Biological Diversity Act sits
nowhere near the words "Section 3(p)", and 21 U.S.C. 355 is nowhere near
"structure/function claim". Without an explicit edge those provisions are
unreachable, and the copilot answers as though no exception exists. That is a
confidently wrong answer, not a cautious one.

This resolver turns a retrieved provision into the set of provisions that
qualify it, so the exception reaches the answer and gets cited.

What it will not do
-------------------
An edge says *where to look*, never *what the answer is*. No conclusion is
derived here; the caller still has to cite the instrument text. Edges are
curated metadata and are only ever as trustworthy as the ``basis`` recorded
alongside them in ``provision_graph.json``.

Temporal resolution
-------------------
``effective_as_of`` answers "which version applied on date X", so a superseded
provision is not cited as current law. An ``effective_to`` of ``None`` means
"no known end date", never "permanent".

Degradation
-----------
Every entry point returns an empty result instead of raising when the graph
file is missing, unparseable, or when a provision is not in it. A missing
graph must reduce the system to today's behaviour (no cross-references), not
break answering.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

GRAPH_FILE = os.path.join(
    os.path.dirname(__file__), "..", "knowledge", "provision_graph.json"
)

# Typed edges. Order matters: it is the order exceptions are surfaced in, so
# the provision that most changes the answer comes first.
EDGE_TYPES = ("exception", "definition", "amendment", "cross_reference")

# How far to follow a chain. Depth 1 is the normal case (a provision's own
# exceptions); the cap exists so a malformed graph cannot spin.
MAX_EXPANSION_DEPTH = 2

STATUS_ACTIVE = "active"
STATUS_SUPERSEDED = "superseded"
STATUS_REPEALED = "repealed"
STATUS_NOT_IN_FORCE = "not_in_force"

# Statuses that mean the provision must not be presented as current law.
_NON_CURRENT_STATUSES = frozenset({STATUS_SUPERSEDED, STATUS_REPEALED, STATUS_NOT_IN_FORCE})

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _empty_graph() -> dict[str, Any]:
    return {
        "provisions": {}, "out_edges": {}, "in_edges": {},
        "by_record": {}, "load_error": None,
    }


def _parse_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    # Tolerate the "2005-04-04 (amended 2005)" and "1945-12-21" shapes that
    # already appear in the corpus rather than rejecting them.
    head = value.strip()[:10]
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None


def _build_graph() -> dict[str, Any]:
    graph = _empty_graph()
    try:
        with open(GRAPH_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        logger.info("Provision graph not present at %s; cross-references disabled", GRAPH_FILE)
        return graph
    except (OSError, json.JSONDecodeError) as exc:
        # A corrupt graph must not break answering; log loudly and carry on
        # with no cross-references.
        graph["load_error"] = str(exc)
        logger.error("Provision graph unreadable at %s: %s", GRAPH_FILE, exc)
        return graph

    provisions = raw.get("provisions")
    if not isinstance(provisions, list):
        logger.error("Provision graph has no 'provisions' list; cross-references disabled")
        return graph

    for prov in provisions:
        if not isinstance(prov, dict):
            continue
        pid = prov.get("provision_id")
        if not pid:
            continue
        graph["provisions"][pid] = prov

    for edge in raw.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        src, dst, etype = edge.get("from"), edge.get("to"), edge.get("type")
        if not src or not dst or not etype:
            continue
        if src not in graph["provisions"] or dst not in graph["provisions"]:
            # An edge to a provision we do not hold would let the system
            # reference something it cannot cite.
            logger.warning(
                "Dropping provision edge %s -> %s (%s): endpoint not in graph",
                src, dst, etype,
            )
            continue
        record = {
            "type": etype,
            "to": dst,
            "basis": edge.get("basis", ""),
            "citation_locator": edge.get("citation_locator", ""),
            "verification_status": edge.get("verification_status", ""),
        }
        graph["out_edges"].setdefault(src, []).append(record)
        graph["in_edges"].setdefault(dst, []).append(
            {"type": etype, "from": src, "citation_locator": record["citation_locator"]}
        )

    # Stable order so the answer is deterministic and exceptions lead.
    for pid, records in graph["out_edges"].items():
        records.sort(key=lambda r: (EDGE_TYPES.index(r["type"]) if r["type"] in EDGE_TYPES else 99, r["to"]))

    # Reverse index: a corpus record may be the *parent* of several provisions
    # (one Act record can back 21 U.S.C. 321(g)(1)(B) and 21 U.S.C. 355), so a
    # record id can map to more than one provision. Both directions matter: an
    # exact provision_id match is authoritative, corpus_record is the fallback.
    by_record: dict[str, list[str]] = {}
    for pid, prov in graph["provisions"].items():
        record_id = prov.get("corpus_record")
        if isinstance(record_id, str) and record_id and record_id != pid:
            by_record.setdefault(record_id, []).append(pid)
    for record_id in by_record:
        by_record[record_id].sort()
    graph["by_record"] = by_record

    logger.info(
        "Provision graph loaded: %d provisions, %d edges",
        len(graph["provisions"]), sum(len(v) for v in graph["out_edges"].values()),
    )
    return graph


def get_graph() -> dict[str, Any]:
    """Load (and memoise) the graph. Thread-safe."""
    global _cache
    if _cache is None:
        with _lock:
            if _cache is None:
                _cache = _build_graph()
    return _cache


def reset_cache() -> None:
    """Drop the memoised graph. Used by tests and after re-ingestion."""
    global _cache
    with _lock:
        _cache = None


def available() -> bool:
    return bool(get_graph()["provisions"])


def get_provision(provision_id: str) -> dict[str, Any] | None:
    if not provision_id:
        return None
    return get_graph()["provisions"].get(provision_id)


def provisions_for_record(record_id: str) -> list[str]:
    """Provision IDs covered by a corpus record, most specific match first.

    An exact ``provision_id`` match wins. Otherwise the record is treated as a
    parent corpus record and every provision that cites it is returned, which
    is how a single Act record that backs several sections still joins to the
    graph. Returns ``[]`` rather than guessing when there is no match.
    """
    if not record_id:
        return []
    graph = get_graph()
    if record_id in graph["provisions"]:
        return [record_id]
    return list(graph["by_record"].get(record_id, []))


def out_edges(provision_id: str, edge_types: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Edges leaving a provision, optionally filtered by type."""
    if not provision_id:
        return []
    records = get_graph()["out_edges"].get(provision_id, [])
    if edge_types:
        wanted = set(edge_types)
        records = [r for r in records if r["type"] in wanted]
    return list(records)


def in_edges(provision_id: str, edge_types: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Edges arriving at a provision (which provisions it qualifies)."""
    if not provision_id:
        return []
    records = get_graph()["in_edges"].get(provision_id, [])
    if edge_types:
        wanted = set(edge_types)
        records = [r for r in records if r["type"] in wanted]
    return list(records)


def is_current(provision_id: str, as_of: date | None = None) -> bool:
    """Is this provision current law on ``as_of``?

    Both the status flag and the applicability window must hold. A provision
    marked superseded is not current even if its window has not closed, and a
    window that has closed is not current even if the status was never updated.
    """
    prov = get_provision(provision_id)
    if prov is None:
        return False
    if prov.get("status") in _NON_CURRENT_STATUSES:
        return False
    day = as_of or date.today()
    start = _parse_date(prov.get("effective_from"))
    if start and day < start:
        return False
    end = _parse_date(prov.get("effective_to"))
    if end and day > end:
        return False
    return True


def expand(
    provision_ids: list[str] | list[tuple[str, str]] | None,
    edge_types: tuple[str, ...] | None = None,
    as_of: date | None = None,
    max_depth: int = MAX_EXPANSION_DEPTH,
) -> dict[str, Any]:
    """Expand provisions into the set that qualifies them.

    Accepts either bare provision IDs or ``(provision_id, citation_locator)``
    pairs from retrieved sources.

    Returns a dict with:
      ``matched``  - requested provisions that exist in the graph
      ``linked``   - provisions reached through edges, each with ``via``,
                    ``depth``, ``edge_type`` and its ``basis``
      ``stale``    - matched/linked provisions that are NOT current law
      ``traversal``- a human-readable explanation for the decision trace

    Never raises. Unknown provisions are simply not matched, so a graph that
    predates a new corpus leaves existing answers untouched.
    """
    result: dict[str, Any] = {
        "matched": [], "linked": [], "stale": [], "traversal": [],
    }
    if not provision_ids:
        return result

    graph = get_graph()
    if not graph["provisions"]:
        return result

    # Normalise (id, locator) pairs; dedupe by provision id, keeping the
    # locator of the first sighting so the citation stays anchored.
    requested: dict[str, str] = {}
    for item in provision_ids:
        if isinstance(item, (tuple, list)):
            pid, locator = (item + ("",))[:2] if len(item) < 2 else (item[0], item[1])
        else:
            pid, locator = item, ""
        if pid and pid in graph["provisions"] and pid not in requested:
            requested[pid] = locator or ""

    result["matched"] = [
        {"provision_id": pid, "citation_locator": loc, "provision": graph["provisions"][pid]}
        for pid, loc in requested.items()
    ]

    seen: set[str] = set(requested)
    frontier: list[tuple[str, str, int, str]] = [
        (pid, EDGE_TYPES[0], 0, "retrieved") for pid in requested
    ]
    depth = 0
    while frontier and depth < max_depth:
        depth += 1
        nxt: list[tuple[str, str, int, str]] = []
        for pid, _via, _d, _origin in frontier:
            for edge in out_edges(pid, edge_types):
                target = edge["to"]
                # Cycle guard: a provision already visited is not re-expanded.
                if target in seen:
                    continue
                seen.add(target)
                linked = graph["provisions"][target]
                result["linked"].append({
                    "provision_id": target,
                    "via": pid,
                    "depth": depth,
                    "edge_type": edge["type"],
                    "basis": edge["basis"],
                    "citation_locator": edge["citation_locator"],
                    "provision": linked,
                })
                nxt.append((target, edge["type"], depth, pid))
        frontier = nxt

    for entry in result["matched"] + result["linked"]:
        if not is_current(entry["provision_id"], as_of):
            result["stale"].append({
                "provision_id": entry["provision_id"],
                "status": entry["provision"].get("status"),
                "effective_from": entry["provision"].get("effective_from"),
                "effective_to": entry["provision"].get("effective_to"),
            })

    if result["matched"]:
        result["traversal"].append(
            "Resolved {} retrieved provision(s) in the cross-reference graph.".format(
                len(result["matched"])
            )
        )
    for entry in result["linked"]:
        result["traversal"].append(
            "{} --{}--> {} ({})".format(
                entry["via"], entry["edge_type"], entry["provision_id"],
                entry["provision"].get("label", ""),
            )
        )
    if result["stale"]:
        result["traversal"].append(
            "WARNING: {} provision(s) are not current law and must not be "
            "presented as current: {}".format(
                len(result["stale"]),
                ", ".join(s["provision_id"] for s in result["stale"]),
            )
        )
    return result


def expand_for_sources(
    sources: list[dict[str, Any]],
    edge_types: tuple[str, ...] | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Expand the provisions behind a list of retrieved source payloads.

    Sources are matched on ``provision_id``, which may be a single ID or a list
    (one Act record can back several provisions). A source with no provision
    identity is skipped rather than guessed at, so this stays correct while
    parts of the corpus still lack the field.
    """
    pairs: list[tuple[str, str]] = []
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        raw = src.get("provision_id")
        if not raw:
            continue
        ids = raw if isinstance(raw, (list, tuple)) else [raw]
        locator = str(src.get("citation_locator") or src.get("source_url") or "")
        for pid in ids:
            if isinstance(pid, str) and pid:
                pairs.append((pid, locator))
    return expand(pairs, edge_types=edge_types, as_of=as_of)


def provision_to_source(
    provision_id: str, edge: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Render a provision node as a citable source payload.

    These are *cross-reference pointers*, not retrieved passages, so they are
    marked ``graph_derived`` and must never be counted as independent official
    votes (that would manufacture High Confidence out of a lookup). The
    relationship that led here is preserved so the answer can say "subject to"
    rather than presenting the provision as a fresh citation.
    """
    prov = get_provision(provision_id)
    if prov is None:
        return None
    edge = edge or {}
    # A raw out-edge record uses "type"; an entry from expand()["linked"] uses
    # "edge_type". Accept both so callers can pass whichever they hold.
    edge_type = edge.get("edge_type") or edge.get("type") or ""
    locator = prov.get("citation_locator", "") or ""
    title = prov.get("label") or prov.get("title") or provision_id
    if locator and locator not in title:
        title = f"{locator} — {title}"
    return {
        "title": title,
        "content": prov.get("summary") or prov.get("title") or title,
        "source": prov.get("authority") or prov.get("act") or "Statute",
        "source_id": provision_id,
        "doc_id": f"provision_graph:{provision_id}",
        "provision_id": provision_id,
        "jurisdiction": prov.get("jurisdiction", "") or "",
        "authority": prov.get("authority", "") or "",
        "authority_level": int(prov.get("authority_level", 1) or 1),
        "category": prov.get("category", "statutory"),
        "document_type": prov.get("document_type", "statute"),
        "citation_locator": locator,
        "source_url": prov.get("source_url", "") or "",
        "effective_from": prov.get("effective_from", "") or "",
        "effective_to": prov.get("effective_to", "") or "",
        "status": prov.get("status", "") or "",
        "verification_status": prov.get("verification_status", "") or "",
        "graph_derived": True,
        "graph_edge_type": edge_type,
        "graph_via": edge.get("via", "") or "",
        "graph_basis": edge.get("basis", "") or "",
    }

