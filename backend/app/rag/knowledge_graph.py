"""
Lightweight knowledge graph over the IP-SAKTI corpus.

Builds entity nodes and typed edges from:
  - canonical seed lexicons (botanical_synonyms, api_monographs, acts_and_gazettes)
  - live corpus documents in Qdrant (which documents mention which ingredient /
    regulation / authority)

Node types : ingredient, botanical, monograph, regulation, authority, jurisdiction
Edge types : botanical_identity, has_monograph, regulatory_status, issued_by,
              has_jurisdiction, mentioned_in, resolved_in_authority

Powers White-Space Navigator indicators and quick entity lookups. The graph is
cached to ``backend/data/knowledge_graph.json`` (TTL default 6h).
"""

import json
import logging
import os
import time
from typing import Any

from app.rag import official_web_retriever

logger = logging.getLogger(__name__)

GRAPH_CACHE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_graph.json")
CACHE_TTL_SEC = float(os.environ.get("IPSAKTI_GRAPH_TTL", "21600"))

_NODE_PREFIX = {
    "ingredient": "ING",
    "botanical": "BOT",
    "monograph": "MONO",
    "regulation": "REG",
    "authority": "AUTH",
    "jurisdiction": "JUS",
}


def _node(ntype: str, name: str) -> str:
    return f"{_NODE_PREFIX.get(ntype, 'N')}:{name}"


def _load_lexicons() -> dict[str, Any]:
    base = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    data: dict[str, Any] = {}
    for name in ("botanical_synonyms", "api_monographs", "acts_and_gazettes"):
        path = os.path.join(base, f"{name}.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data[name] = json.load(fh)
        except Exception as exc:
            logger.warning("Lexicon %s unavailable: %s", name, exc)
            data[name] = {} if name == "botanical_synonyms" else []
    return data


def _build_entities(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return {node_id: node} plus alias -> node_id index."""
    nodes: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}

    def put(ntype: str, name: str, attrs: dict[str, Any] | None = None) -> str:
        key = _node(ntype, name)
        nodes.setdefault(key, {
            "id": key, "type": ntype, "name": name,
            **({"attrs": attrs} if attrs else {}),
        })
        return key

    for cid, entry in (data.get("botanical_synonyms") or {}).items():
        botanical = entry.get("botanical_name", "") or cid
        ing_key = put("ingredient", cid)
        put("botanical", botanical)
        names = [botanical, cid]
        for lang in ("sanskrit", "hindi", "marathi", "english", "tamil", "telugu"):
            for alias in entry.get(lang) or []:
                if isinstance(alias, str) and alias.strip():
                    names.append(alias.strip())
        for name in names:
            aliases[name.lower()] = ing_key
        nodes[ing_key]["aliases"] = names
        nodes[ing_key]["botanical"] = botanical

    for mono in data.get("api_monographs") or []:
        cid = mono.get("canonical_id", "")
        mid = mono.get("api_monograph_id", "")
        if not cid:
            continue
        ing_key = _node("ingredient", cid)
        if ing_key not in nodes:
            put("ingredient", cid)
        mono_key = put("monograph", mid or f"{cid}-monograph", {
            "botanical": mono.get("botanical_name", ""),
            "family": mono.get("family", ""),
            "daily_dosage_limit_g": mono.get("daily_dosage_limit_g"),
        })
        for market, status in (
            ("India/FSSAI", mono.get("fssai_aahara_status")),
            ("United States/FDA", mono.get("us_fda_ndi_status")),
            ("Canada/Health Canada", mono.get("canada_nhpid_status")),
        ):
            if status:
                put("authority", market.split("/")[1])
                nodes[mono_key].setdefault("statuses", []).append({"market": market, "status": status})

    for act in data.get("acts_and_gazettes") or []:
        title = act.get("act_title", "")
        if not title:
            continue
        auth = act.get("authority", "")
        jur = act.get("jurisdiction", "")
        reg_key = put("regulation", title, {
            "section": act.get("section_reference", ""),
            "effective_date": act.get("effective_date", ""),
            "keywords": act.get("keywords", []),
        })
        nodes[reg_key]["jurisdiction"] = jur
        put("jurisdiction", jur)
        if auth:
            put("authority", auth)
            nodes[reg_key]["authority"] = auth
        aliases[title.lower()] = reg_key

    for src in official_web_retriever.OFFICIAL_SOURCES:
        put("authority", src["authority"])
        put("jurisdiction", src["jurisdiction"])

    return {"nodes": nodes, "aliases": aliases}


def _build_edges(nodes: dict[str, dict[str, Any]], docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen = set()
    deferred: dict[str, dict[str, Any]] = {}

    def add(src_n: str, rel: str, dst_n: str) -> None:
        key = (src_n, rel, dst_n)
        if key in seen:
            return
        seen.add(key)
        edges.append({"from": src_n, "relation": rel, "to": dst_n})

    ing_by_botanical: dict[str, str] = {}
    for node in nodes.values():
        if node["type"] == "ingredient" and node.get("botanical"):
            ing_by_botanical[node["botanical"].lower()] = node["id"]

    for node in list(nodes.values()):
        if node["type"] == "monograph":
            botanical = (node.get("attrs") or {}).get("botanical", "").lower()
            ing_id = ing_by_botanical.get(botanical) or node["id"]
            if botanical in ing_by_botanical:
                add(ing_by_botanical[botanical], "has_monograph", node["id"])
            for status in node.get("statuses", []):
                compound = f"{status['market']} — {status['status']}"
                compound_key = _node("authority", compound)
                if compound_key not in nodes and compound_key not in deferred:
                    deferred[compound_key] = {
                        "id": compound_key, "type": "authority", "name": compound,
                    }
                add(ing_id, "regulatory_status", compound_key)

    for node in list(nodes.values()):
        if node["type"] == "regulation":
            if node.get("jurisdiction"):
                jur_id = _node("jurisdiction", node["jurisdiction"])
                if jur_id in nodes:
                    add(node["id"], "in_jurisdiction", jur_id)
            if node.get("authority"):
                auth_id = _node("authority", node["authority"])
                if auth_id in nodes:
                    add(auth_id, "issued_by", node["id"])

    for auth_node in list(nodes.values()):
        if auth_node["type"] != "authority":
            continue
        name = auth_node["name"]
        if "Health Canada" in name:
            add(auth_node["id"], "has_jurisdiction", _node("jurisdiction", "Canada"))
        elif "WHO" in name or "WIPO" in name:
            add(auth_node["id"], "has_jurisdiction", _node("jurisdiction", "International"))
        elif "FDA" in name:
            add(auth_node["id"], "has_jurisdiction", _node("jurisdiction", "United States"))

    nodes.update(deferred)

    # Corpus scan: which docs mention which ingredient / regulation.
    for doc in docs:
        content = (doc.get("content") or "").lower()
        source_name = doc.get("source", "")
        source_key = _node("source", source_name)
        if source_key not in nodes:
            nodes[source_key] = {"id": source_key, "type": "source", "name": source_name}
        for node in list(nodes.values()):
            if node["type"] not in ("ingredient", "regulation"):
                continue
            for alias in node.get("aliases", [node["name"]]):
                if len(alias) < 4:
                    continue
                if alias.lower() in content:
                    add(node["id"], "mentioned_in", source_key)
                    break
    return edges


def _corpus_docs() -> list[dict[str, Any]]:
    try:
        from app.rag.qdrant_store import QdrantVectorStore
        store = QdrantVectorStore()
        docs = store.get_all_documents(limit=5000)
        if docs:
            return docs
    except Exception as exc:
        logger.debug("Qdrant docs unavailable for graph: %s", exc)
    try:
        from app.rag.kb import collect_knowledge_documents
        return collect_knowledge_documents() or []
    except Exception as exc:
        logger.debug("KB docs unavailable for graph: %s", exc)
    return []


def build_graph(force: bool = False) -> dict[str, Any]:
    """Build (or load cached) graph: nodes and edges with stats."""
    if not force:
        cached = _load_cached_graph()
        if cached is not None:
            return cached

    data = _load_lexicons()
    built = _build_entities(data)
    nodes = built["nodes"]
    docs = _corpus_docs()
    edges = _build_edges(nodes, docs)

    by_type: dict[str, int] = {}
    for node in nodes.values():
        by_type[node["type"]] = by_type.get(node["type"], 0) + 1
    edge_types: dict[str, int] = {}
    for e in edges:
        edge_types[e["relation"]] = edge_types.get(e["relation"], 0) + 1

    graph = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "node_counts": by_type,
        "edge_counts": edge_types,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "ingredients": sorted(
            ({"name": n.get("name"), "aliases": n.get("aliases", []),
              "botanical": n.get("botanical", "")}
             for n in nodes.values() if n["type"] == "ingredient"),
            key=lambda x: x["name"],
        ),
        "authorities": sorted(
            (n.get("name") for n in nodes.values() if n["type"] == "authority"),
        ),
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    _save_cached_graph(graph)
    return graph


def _cache_path() -> str:
    return GRAPH_CACHE


def _load_cached_graph() -> dict[str, Any] | None:
    try:
        if not os.path.exists(_cache_path()):
            return None
        with open(_cache_path(), encoding="utf-8") as fh:
            graph = json.load(fh)
        built = graph.get("built_at", "")
        try:
            if built and (time.time() - time.mktime(time.strptime(built, "%Y-%m-%dT%H:%M:%S"))) <= CACHE_TTL_SEC:
                return graph
        except Exception:
            pass
    except Exception as exc:
        logger.debug("Graph cache load failed: %s", exc)
    return None


def _save_cached_graph(graph: dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_cache_path()), exist_ok=True)
        with open(_cache_path(), "w", encoding="utf-8") as fh:
            json.dump(graph, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Could not persist graph cache: %s", exc)


def get_graph_stats(force: bool = False) -> dict[str, Any]:
    graph = build_graph(force=force)
    return {
        "built_at": graph["built_at"],
        "total_nodes": graph["total_nodes"],
        "total_edges": graph["total_edges"],
        "node_counts": graph["node_counts"],
        "edge_counts": graph["edge_counts"],
        "cached": _load_cached_graph() is not None,
        "cache_ttl_sec": int(CACHE_TTL_SEC),
    }


def search_entities(term: str, limit: int = 10) -> dict[str, Any]:
    graph = build_graph(force=False)
    q = term.lower().strip()
    if not q:
        return {"query": term, "matches": []}
    matches = []
    seen_nodes = set()
    for node in graph["nodes"]:
        if node["id"] in seen_nodes:
            continue
        hay = " ".join([node["name"], *node.get("aliases", [])]).lower()
        if q in hay:
            seen_nodes.add(node["id"])
            edges = [
                {"relation": e["relation"], "to": e["to"]}
                for e in graph["edges"] if e["from"] == node["id"]
            ]
            matches.append({
                "id": node["id"], "type": node["type"], "name": node["name"],
                "aliases": node.get("aliases", [])[:6],
                "edges": edges[:8],
            })
            if len(matches) >= limit:
                break
    return {"query": term, "match_count": len(matches), "matches": matches}