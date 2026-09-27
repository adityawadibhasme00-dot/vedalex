"""
Dynamic Bio-Resource Knowledge Graph builder (IP-SAKTI).

Composes a node/edge graph for ANY selected innovation — single herb or
polyherbal formulation — strictly from the curated IP-SAKTI knowledge base:

  * identity + API monograph for every resolved canonical ingredient
  * provenance / ABS / TK / IP posture from curated bio-resource seed data
  * regulations / authorities / jurisdictions linked through the corpus
    knowledge graph (lexicons + Qdrant mentions)
  * retrieved corpus documents (patents / traditional_knowledge /
    regulations / safety / quality_standards) surfaced as evidence nodes
    with real citations

There is nothing hardcoded to Ashwagandha or Brahmi. If a requested herb has
no indexed evidence, the graph still returns its identity node plus an explicit
"no verified information" guard instead of inventing connections.
"""

import logging
import re
from typing import Any

from app.models.intelligence import (
    InnovationGraphIngredient,
    InnovationKnowledgeGraphResponse,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    SelectedInnovationInfo,
)
from app.services.bio_resource_engine import BioResourceEngine
from app.services.ingredient_resolver import IngredientResolverService
from app.services.passport_engine import PassportEngine

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Generated dynamically from the curated IP-SAKTI knowledge base "
    "(regulations · patents · biodiversity · traditional_knowledge · "
    "quality_standards · safety). No content outside the indexed corpus is used."
)

# Column order used for deterministic layout.
_CATEGORY_COLUMNS = [
    "ingredient",
    "monograph",
    "tkdl",
    "regulation",
    "authority",
    "patent",
    "paper",
    "safety",
    "supplier",
]


def _slug(label: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return raw[:48] or "node"


def _uniquify(base: str, taken: set) -> str:
    candidate = base
    n = 2
    while candidate in taken:
        candidate = f"{base}-{n}"
        n += 1
    taken.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def _layout(nodes: list[KnowledgeGraphNode]) -> list[KnowledgeGraphNode]:
    """Deterministic grid layout: one column per category, rows stacked."""
    col_index = {cat: i for i, cat in enumerate(_CATEGORY_COLUMNS)}
    rows: dict[str, int] = {}
    for node in nodes:
        cat = node.category if node.category in col_index else "ingredient"
        row = rows.get(cat, 0)
        rows[cat] = row + 1
        node.x = 70 + col_index[cat] * 200
        node.y = 90 + (row % 5) * 88
    return nodes


# ---------------------------------------------------------------------------
# Corpus retrieval (pure RAG — indexed documents only)
# ---------------------------------------------------------------------------

def _collection_mapping() -> dict[str, str]:
    return {
        "regulations": "regulation",
        "patents": "patent",
        "biodiversity": "supplier",
        "traditional_knowledge": "tkdl",
        "quality_standards": "monograph",
        "safety": "safety",
    }


def _edge_label(category: str) -> str:
    return {
        "regulation": "Regulatory",
        "patent": "Prior Art",
        "tkdl": "Classical Prior Art",
        "safety": "Safety / Research",
        "monograph": "Quality Standard",
        "supplier": "ABS / Provenance",
    }.get(category, "Evidence")


def _retrieve_corpus_evidence(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve evidence for one ingredient across the six indexed collections."""
    try:
        from app.rag.retrieval_pipeline import HybridRetriever
        result = HybridRetriever.retrieve(query, top_k=min(limit, 8))
        return result.get("sources", []) or []
    except Exception as exc:
        logger.warning("Corpus retrieval failed for %r: %s", query, exc)
        return []


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _add_bioresource_layer(
    canonical_id: str,
    nodes: list[KnowledgeGraphNode],
    edges: list[KnowledgeGraphEdge],
    taken: set,
    ingredient_id: str,
) -> None:
    """Add provenance / conservation / ABS / TK nodes from curated seed data."""
    try:
        BioResourceEngine.load_data()
        if not BioResourceEngine._bioresource.get(canonical_id):
            return
    except Exception:
        return

    try:
        plant = BioResourceEngine._plant(canonical_id)
    except Exception as exc:
        logger.warning("bio-resource layer skipped for %s: %s", canonical_id, exc)
        return

    # Supplier / provenance nodes for every registry-backed origin.
    for geo in plant.geography:
        if geo.status in ("verified", "supplier_confirmed"):
            sid = _uniquify(_slug(f"sup-{geo.state}"), taken)
            nodes.append(KnowledgeGraphNode(
                id=sid,
                label=f"{geo.state} · {plant.botanical_name.split('(')[0].strip()}",
                category="supplier",
                details=f"{geo.note} (status: {geo.status.replace('_', ' ')})",
                sourceAuthority=geo.source,
            ))
            edges.append(KnowledgeGraphEdge(**{"from": ingredient_id}, to=sid, label="Provenance", color="#14b8a6"))

    # Conservation / trade posture as a supplier-side note node.
    if plant.conservation_status:
        cid = _uniquify(_slug(f"cons-{canonical_id}"), taken)
        nodes.append(KnowledgeGraphNode(
            id=cid,
            label="Conservation & Trade Posture",
            category="supplier",
            details=f"{plant.conservation_status} · {plant.trade_demand_class}",
            sourceAuthority="NMPB trade guidance",
        ))
        edges.append(KnowledgeGraphEdge(**{"from": ingredient_id}, to=cid, label="Market Posture", color="#14b8a6"))


def _add_corpus_nodes(
    raw_name: str,
    ingredient_id: str,
    nodes: list[KnowledgeGraphNode],
    edges: list[KnowledgeGraphEdge],
    taken: set,
    collections_used: set,
) -> None:
    """Surface real indexed documents mentioning this ingredient as evidence."""
    cmap = _collection_mapping()
    sources = _retrieve_corpus_evidence(raw_name)
    for src in sources[:6]:
        collection = src.get("collection") or ""
        category = cmap.get(collection) or _collection_mapping().get(str(src.get("category", "")).lower()) or "source"
        label = str(src.get("title") or src.get("act_title") or src.get("source") or "Indexed source")[:64]
        nid = _uniquify(_slug(label), taken)
        authority = str(src.get("authority") or src.get("jurisdiction") or "Indexed corpus")
        details = " ".join(str(src.get("content", "")).split())[:180]
        nodes.append(KnowledgeGraphNode(
            id=nid,
            label=label,
            category=category,
            details=details or authority,
            sourceAuthority=authority,
            collection=collection,
            sourceUrl=str(src.get("source_url") or ""),
        ))
        edges.append(KnowledgeGraphEdge(
            **{"from": ingredient_id}, to=nid,
            label=_edge_label(category), color=_color_for(category),
        ))
        if collection:
            collections_used.add(collection)


def _color_for(category: str) -> str:
    return {
        "ingredient": "#16a34a",
        "monograph": "#7c3aed",
        "regulation": "#d97706",
        "authority": "#2563eb",
        "jurisdiction": "#2563eb",
        "tkdl": "#f59e0b",
        "patent": "#0284c7",
        "paper": "#10b981",
        "safety": "#ef4444",
        "supplier": "#14b8a6",
        "source": "#64748b",
    }.get(category, "#10b981")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_innovation_graph(
    ingredient_names: list[str],
    innovation_title: str | None = None,
    passport_id: str | None = None,
) -> InnovationKnowledgeGraphResponse:
    """Build a dynamic knowledge graph for the selected innovation.

    The graph is generated per-innovation from the curated knowledge base —
    never from a fixed Ashwagandha/Brahmi template.
    """
    names = [n for n in (ingredient_names or []) if n and str(n).strip()]
    passport = None
    if passport_id:
        try:
            passport = PassportEngine.get_passport(passport_id)
        except Exception:
            passport = None
    if passport is not None:
        names = [ing.raw_name for ing in passport.ingredients if ing.raw_name] or names
        innovation_title = innovation_title or passport.case_title or innovation_title

    if not names:
        return InnovationKnowledgeGraphResponse(
            selected_innovation=SelectedInnovationInfo(title=innovation_title or "Selected Innovation", kind="Single Herb"),
            nodes=[],
            edges=[],
            evidence_found=False,
            evidence_note="No resolved botanical ingredients were provided to build the graph.",
            disclaimer=DISCLAIMER,
        )

    kind = "Polyherbal Formulation" if len(names) > 1 else "Single Herb"
    title = innovation_title or ("Formulation" if len(names) > 1 else next(iter(names)))

    nodes: list[KnowledgeGraphNode] = []
    edges: list[KnowledgeGraphEdge] = []
    taken: set = set()
    collections_used: set = set()
    ingredient_meta: list[InnovationGraphIngredient] = []
    nugget: list[str] = []

    IngredientResolverService.load_data()
    entity_graph = None
    try:
        from app.rag.knowledge_graph import build_graph as build_entity_graph
        entity_graph = build_entity_graph(force=False)
    except Exception:
        entity_graph = None

    for name in names:
        stripped = str(name).strip()
        resolved = None
        try:
            resolved = IngredientResolverService.resolve(stripped)
        except Exception:
            resolved = None

        canonical_id = resolved.canonical_id if resolved else ""
        botanical = resolved.accepted_botanical_name if resolved else ""
        monograph_id = resolved.api_monograph_id if resolved else ""

        label = f"{botanical} ({stripped})" if botanical and botanical != stripped else stripped
        iid = _uniquify(_slug(f"ing-{stripped}"), taken)
        details_parts = [f"Canonical: {canonical_id}" if canonical_id else "Not in curated API monograph set."]
        if resolved:
            family = getattr(resolved, "family", "")
            if family:
                details_parts.append(f"Family: {family}")
            parts = getattr(resolved, "standard_plant_parts", None) or []
            if parts:
                details_parts.append("Parts: " + ", ".join(parts))
            uses = getattr(resolved, "classical_therapeutic_uses", None) or []
            if uses and any(uses):
                details_parts.append("Classical uses: " + "; ".join(uses[:2]))
        nodes.append(KnowledgeGraphNode(
            id=iid,
            label=label,
            category="ingredient",
            details=". ".join(details_parts),
            sourceAuthority="Ayurvedic Pharmacopoeia of India" if resolved else "Curated IP-SAKTI knowledge base",
        ))
        ingredient_meta.append(InnovationGraphIngredient(
            raw_name=stripped,
            canonical_id=canonical_id,
            botanical_name=botanical,
            api_monograph_id=monograph_id,
            monographed=bool(resolved),
        ))

        # Identity -> botanical alias when the resolver knows the Latin name.
        if botanical and canonical_id:
            bid = _uniquify(_slug(f"bot-{canonical_id}"), taken)
            nodes.append(KnowledgeGraphNode(
                id=bid,
                label=botanical,
                category="botanical",
                details=f"Botanical identity of {stripped}; monographed as {monograph_id or 'unmonographed'}.",
                sourceAuthority="Ayurvedic Pharmacopoeia of India",
            ))
            edges.append(KnowledgeGraphEdge(**{"from": iid}, to=bid, label="Identity", color="#16a34a"))

        # Monograph node from curated API monograph records.
        if resolved and monograph_id:
            mid = _uniquify(_slug(f"mono-{canonical_id}"), taken)
            mono_ref = monograph_id[4:] if monograph_id.upper().startswith("API") else monograph_id
            mono_details = f"API Monograph {monograph_id}."
            try:
                with open(__import__("os").path.join(
                    __import__("os").path.dirname(__file__), "..", "knowledge", "api_monographs.json"
                ), encoding="utf-8") as fh:
                    import json as _json
                    for entry in _json.load(fh):
                        if entry.get("canonical_id") == canonical_id:
                            statuses = []
                            for label_key, mkt in (
                                ("fssai_aahara_status", "India/FSSAI"),
                                ("us_fda_ndi_status", "United States/FDA"),
                                ("canada_nhpid_status", "Canada/Health Canada"),
                            ):
                                val = entry.get(label_key)
                                if val:
                                    statuses.append(f"{mkt}: {val}")
                            if statuses:
                                mono_details += " Statuses — " + "; ".join(statuses)
                            break
            except Exception:
                pass
            nodes.append(KnowledgeGraphNode(
                id=mid,
                label=f"API Monograph {mono_ref}",
                category="monograph",
                details=mono_details,
                sourceAuthority="Ayurvedic Pharmacopoeia of India",
                collection="quality_standards",
            ))
            edges.append(KnowledgeGraphEdge(**{"from": iid}, to=mid, label="Has Monograph", color="#7c3aed"))
            collections_used.add("quality_standards")

        # Provenance / ABS / TK posture from curated bio-resource seed data.
        if canonical_id:
            _add_bioresource_layer(canonical_id, nodes, edges, taken, iid)

        # Statutory / authority context from the corpus entity graph.
        if entity_graph and canonical_id:
            _add_entity_context(entity_graph, canonical_id, botanical, iid, nodes, edges, taken, collections_used)

        # Live indexed corpus documents naming this ingredient.
        _add_corpus_nodes(stripped, iid, nodes, edges, taken, collections_used)

    nodes = _layout(nodes)

    evidence_found = len(nodes) > len(ingredient_meta)
    if not evidence_found:
        nugget.append(
            "No verified information found in the current IP-SAKTI knowledge base "
            "for the requested ingredient(s). Please refine the query or consult an IP facilitator."
        )

    return InnovationKnowledgeGraphResponse(
        selected_innovation=SelectedInnovationInfo(
            title=title,
            kind=kind,
            ingredients=ingredient_meta,
        ),
        nodes=nodes,
        edges=edges,
        collections_used=sorted(collections_used),
        evidence_found=evidence_found,
        evidence_note="\n".join(nugget),
        disclaimer=DISCLAIMER,
    )


def _add_entity_context(
    entity_graph: dict[str, Any],
    canonical_id: str,
    botanical: str,
    ingredient_id: str,
    nodes: list[KnowledgeGraphNode],
    edges: list[KnowledgeGraphEdge],
    taken: set,
    collections_used: set,
) -> None:
    """Pull regulation / authority / jurisdiction nodes linked to this
    ingredient in the corpus knowledge graph (lexicons + Qdrant mentions)."""
    ing_id = f"ING:{canonical_id}"
    bot_lower = botanical.lower()
    related: list[tuple[str, dict[str, Any]]] = []
    node_by_id = {n["id"]: n for n in entity_graph.get("nodes", [])}
    for edge in entity_graph.get("edges", []):
        src = edge.get("from", "")
        dst = edge.get("to", "")
        if src == ing_id or (bot_lower and src == f"ING:{canonical_id}"):
            if dst in node_by_id:
                related.append((edge.get("relation", "related"), node_by_id[dst]))
        elif dst == ing_id:
            if src in node_by_id:
                related.append((edge.get("relation", "related"), node_by_id[src]))

    seen_type_count: dict[str, int] = {}
    for _rel, node in related:
        ntype = node.get("type", "")
        if ntype in ("ingredient", "source"):
            continue
        if ntype not in ("regulation", "authority", "jurisdiction", "monograph"):
            continue
        if seen_type_count.get(ntype, 0) >= 3:
            continue
        seen_type_count[ntype] = seen_type_count.get(ntype, 0) + 1
        name = str(node.get("name", ""))
        nid = _uniquify(_slug(f"{ntype}-{name}"), taken)
        attrs = node.get("attrs") or {}
        detail = []
        if ntype == "regulation":
            detail.append(f"Section: {attrs.get('section', '')}")
            detail.append(f"Effective: {attrs.get('effective_date', '')}")
            node.get("jurisdiction") or ""
            authority = node.get("authority") or ""
        else:
            authority = name
        nodes.append(KnowledgeGraphNode(
            id=nid,
            label=name[:64],
            category="jurisdiction" if ntype == "jurisdiction" else ntype,
            details=" · ".join(d for d in detail if d),
            sourceAuthority=authority or name,
        ))
        edges.append(KnowledgeGraphEdge(
            **{"from": ingredient_id}, to=nid,
            label="Regulatory" if ntype == "regulation" else ("Issued By" if ntype == "authority" else "Jurisdiction"),
            color=_color_for(ntype),
        ))
        if ntype == "regulation":
            collections_used.add("regulations")