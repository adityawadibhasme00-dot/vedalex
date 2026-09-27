import json
import sys
import time
import types
from typing import Any

import pytest

from app.rag import knowledge_graph as kg
from app.rag import official_web_retriever as owr

LEXICON = {
    "botanical_synonyms": {
        "ING-Ashwagandha": {
            "botanical_name": "Withania somnifera",
            "english": ["Winter Cherry", "Ashwagandha"],
            "hindi": ["Asagandh", "   "],
            "sanskrit": [],
        }
    },
    "api_monographs": [
        {
            "canonical_id": "ING-Ashwagandha",
            "api_monograph_id": "API-1",
            "botanical_name": "Withania somnifera",
            "family": "Solanaceae",
            "daily_dosage_limit_g": 3.0,
            "fssai_aahara_status": "restricted",
            "us_fda_ndi_status": "old_dietary_ingredient",
        },
        {"canonical_id": "", "api_monograph_id": "SKIP-ME"},
        {"canonical_id": "ING-Orphan", "api_monograph_id": ""},
    ],
    "acts_and_gazettes": [
        {
            "act_title": "Patents Act, 1970",
            "authority": "IPO",
            "jurisdiction": "India",
            "section_reference": "3(p)",
            "effective_date": "1970",
            "keywords": ["novelty"],
        },
        {"act_title": "", "authority": "Ghost", "jurisdiction": "India"},
    ],
}


@pytest.fixture
def graph_env(tmp_path, monkeypatch):
    cache = tmp_path / "knowledge_graph.json"
    monkeypatch.setattr(kg, "GRAPH_CACHE", str(cache))
    monkeypatch.setattr(kg, "_corpus_docs", lambda: [])
    return cache


def _qdrant_module(store_cls):
    module: Any = types.ModuleType("app.rag.qdrant_store")
    module.QdrantVectorStore = store_cls
    return module


def _kb_module(collector):
    module: Any = types.ModuleType("app.rag.kb")
    module.collect_knowledge_documents = collector
    return module


def _controlled_graph():
    nodes = [
        {
            "id": "ING:X",
            "type": "ingredient",
            "name": "X",
            "aliases": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta"],
        },
        {"id": "REG:Y", "type": "regulation", "name": "Alpha Act"},
        {"id": "AUTH:Z", "type": "authority", "name": "Nobody"},
    ]
    edges = [{"from": "ING:X", "relation": f"rel{i}", "to": "T"} for i in range(12)]
    return {"built_at": "2026-01-01T00:00:00", "nodes": nodes, "edges": edges}


def _edge_set(edges):
    return {(e["from"], e["relation"], e["to"]) for e in edges}


def test_node_id_prefixes():
    assert kg._node("ingredient", "ING-A") == "ING:ING-A"
    assert kg._node("botanical", "Withania") == "BOT:Withania"
    assert kg._node("monograph", "API-1") == "MONO:API-1"
    assert kg._node("regulation", "Patents Act") == "REG:Patents Act"
    assert kg._node("authority", "FSSAI") == "AUTH:FSSAI"
    assert kg._node("jurisdiction", "India") == "JUS:India"
    assert kg._node("source", "kb") == "N:kb"
    assert kg._node("unknown-kind", "thing") == "N:thing"


def test_load_lexicons_reads_shipped_files():
    data = kg._load_lexicons()
    assert set(data) == {"botanical_synonyms", "api_monographs", "acts_and_gazettes"}
    assert isinstance(data["botanical_synonyms"], dict)
    assert data["botanical_synonyms"]
    assert isinstance(data["api_monographs"], list)
    assert data["api_monographs"]
    assert isinstance(data["acts_and_gazettes"], list)
    assert data["acts_and_gazettes"]


def test_load_lexicons_defaults_when_files_unreadable(monkeypatch):
    real_open = open

    def failing_open(path, *args, **kwargs):
        name = str(path)
        if name.endswith("botanical_synonyms.json"):
            raise FileNotFoundError(name)
        if name.endswith("api_monographs.json"):
            raise OSError("unreadable")
        if name.endswith("acts_and_gazettes.json"):
            raise OSError("unreadable")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", failing_open)
    data = kg._load_lexicons()
    assert data["botanical_synonyms"] == {}
    assert data["api_monographs"] == []
    assert data["acts_and_gazettes"] == []


def test_build_entities_creates_ingredient_aliases():
    built = kg._build_entities(LEXICON)
    node = built["nodes"]["ING:ING-Ashwagandha"]
    assert node["type"] == "ingredient"
    assert node["name"] == "ING-Ashwagandha"
    assert node["botanical"] == "Withania somnifera"
    assert node["aliases"] == [
        "Withania somnifera",
        "ING-Ashwagandha",
        "Asagandh",
        "Winter Cherry",
        "Ashwagandha",
    ]
    assert built["nodes"]["BOT:Withania somnifera"]["type"] == "botanical"
    assert built["aliases"]["winter cherry"] == "ING:ING-Ashwagandha"
    assert built["aliases"]["ing-ashwagandha"] == "ING:ING-Ashwagandha"
    assert "   " not in built["aliases"]


def test_build_entities_monograph_statuses_and_skips():
    built = kg._build_entities(LEXICON)
    nodes = built["nodes"]
    mono = nodes["MONO:API-1"]
    assert mono["attrs"] == {
        "botanical": "Withania somnifera",
        "family": "Solanaceae",
        "daily_dosage_limit_g": 3.0,
    }
    assert mono["statuses"] == [
        {"market": "India/FSSAI", "status": "restricted"},
        {"market": "United States/FDA", "status": "old_dietary_ingredient"},
    ]
    assert nodes["AUTH:FSSAI"]["type"] == "authority"
    assert nodes["AUTH:FDA"]["type"] == "authority"
    assert "AUTH:Health Canada" not in nodes
    assert not any("SKIP-ME" in key for key in nodes)
    assert nodes["MONO:ING-Orphan-monograph"]["attrs"]["botanical"] == ""


def test_build_entities_regulation_and_official_sources():
    built = kg._build_entities(LEXICON)
    nodes = built["nodes"]
    reg = nodes["REG:Patents Act, 1970"]
    assert reg["type"] == "regulation"
    assert reg["attrs"]["section"] == "3(p)"
    assert reg["attrs"]["effective_date"] == "1970"
    assert reg["attrs"]["keywords"] == ["novelty"]
    assert reg["jurisdiction"] == "India"
    assert reg["authority"] == "IPO"
    assert nodes["JUS:India"]["type"] == "jurisdiction"
    assert nodes["AUTH:IPO"]["type"] == "authority"
    assert built["aliases"]["patents act, 1970"] == "REG:Patents Act, 1970"
    assert not any("Ghost" in key for key in nodes)
    assert nodes["AUTH:World Health Organization (WHO)"]["type"] == "authority"
    assert nodes["JUS:International"]["type"] == "jurisdiction"
    for source in owr.OFFICIAL_SOURCES:
        assert nodes[f"AUTH:{source['authority']}"]["type"] == "authority"
        assert nodes[f"JUS:{source['jurisdiction']}"]["type"] == "jurisdiction"


def test_build_edges_monograph_and_regulatory_status():
    built = kg._build_entities(LEXICON)
    edges = kg._build_edges(built["nodes"], [])
    rels = _edge_set(edges)
    assert ("ING:ING-Ashwagandha", "has_monograph", "MONO:API-1") in rels
    assert (
        "ING:ING-Ashwagandha",
        "regulatory_status",
        "AUTH:India/FSSAI — restricted",
    ) in rels
    assert (
        "ING:ING-Ashwagandha",
        "regulatory_status",
        "AUTH:United States/FDA — old_dietary_ingredient",
    ) in rels
    assert built["nodes"]["AUTH:India/FSSAI — restricted"]["type"] == "authority"


def test_build_edges_regulation_jurisdiction_and_issuer():
    built = kg._build_entities(LEXICON)
    edges = kg._build_edges(built["nodes"], [])
    rels = _edge_set(edges)
    assert ("REG:Patents Act, 1970", "in_jurisdiction", "JUS:India") in rels
    assert ("AUTH:IPO", "issued_by", "REG:Patents Act, 1970") in rels


def test_build_edges_authority_jurisdiction_links():
    built = kg._build_entities(LEXICON)
    rels = _edge_set(kg._build_edges(built["nodes"], []))
    assert (
        "AUTH:Health Canada, Government of Canada",
        "has_jurisdiction",
        "JUS:Canada",
    ) in rels
    assert (
        "AUTH:World Health Organization (WHO)",
        "has_jurisdiction",
        "JUS:International",
    ) in rels
    assert (
        "AUTH:US Food and Drug Administration (FDA)",
        "has_jurisdiction",
        "JUS:United States",
    ) in rels


def test_build_edges_corpus_mentions_deduplicated():
    built = kg._build_entities(LEXICON)
    docs = [
        {"content": "Winter Cherry is used in the formulation", "source": "kb"},
        {"content": "more about winter cherry", "source": "kb"},
        {"content": "unrelated text", "source": "other"},
    ]
    edges = kg._build_edges(built["nodes"], docs)
    mentions = [e for e in edges if e["relation"] == "mentioned_in"]
    assert mentions == [
        {"from": "ING:ING-Ashwagandha", "relation": "mentioned_in", "to": "N:kb"}
    ]
    assert built["nodes"]["N:kb"]["type"] == "source"
    assert built["nodes"]["N:kb"]["name"] == "kb"
    assert built["nodes"]["N:other"]["type"] == "source"


def test_build_edges_ignores_short_aliases():
    lex = {
        "botanical_synonyms": {
            "ING-Shorty": {
                "botanical_name": "Shortus minimus",
                "english": ["ab"],
            }
        },
        "api_monographs": [],
        "acts_and_gazettes": [],
    }
    built = kg._build_entities(lex)
    short_edges = kg._build_edges(built["nodes"], [{"content": "contains ab here", "source": "kb"}])
    assert [e for e in short_edges if e["relation"] == "mentioned_in"] == []
    long_edges = kg._build_edges(built["nodes"], [{"content": "the Shortus minimus plant grows", "source": "kb"}])
    assert (
        "ING:ING-Shorty",
        "mentioned_in",
        "N:kb",
    ) in _edge_set(long_edges)


def test_build_graph_returns_counts_and_lists(graph_env):
    graph = kg.build_graph(force=True)
    assert graph["total_nodes"] > 0
    assert graph["total_edges"] > 0
    assert sum(graph["node_counts"].values()) == graph["total_nodes"]
    assert sum(graph["edge_counts"].values()) == graph["total_edges"]
    assert set(graph["node_counts"]) <= {
        "ingredient",
        "botanical",
        "monograph",
        "regulation",
        "authority",
        "jurisdiction",
        "source",
    }
    assert graph["ingredients"]
    assert graph["ingredients"] == sorted(graph["ingredients"], key=lambda item: item["name"])
    for ingredient in graph["ingredients"]:
        assert set(ingredient) == {"name", "aliases", "botanical"}
    assert graph["authorities"] == sorted(graph["authorities"])
    assert all(isinstance(node["id"], str) and node["type"] for node in graph["nodes"])
    assert all(set(edge) == {"from", "relation", "to"} for edge in graph["edges"])
    assert graph["built_at"]


def test_build_graph_writes_and_reuses_cache(graph_env):
    first = kg.build_graph(force=True)
    assert graph_env.exists()
    on_disk = json.loads(graph_env.read_text(encoding="utf-8"))
    assert on_disk["total_nodes"] == first["total_nodes"]
    second = kg.build_graph(force=False)
    assert second["total_nodes"] == first["total_nodes"]
    assert second["built_at"] == first["built_at"]


def test_build_graph_force_rebuilds_stale_marker(graph_env):
    kg.build_graph(force=True)
    injected = json.loads(graph_env.read_text(encoding="utf-8"))
    injected["marker"] = "keep-me"
    graph_env.write_text(json.dumps(injected), encoding="utf-8")
    cached = kg.build_graph(force=False)
    assert cached.get("marker") == "keep-me"
    rebuilt = kg.build_graph(force=True)
    assert "marker" not in rebuilt
    assert rebuilt["total_nodes"] > 0


def test_build_graph_rejects_expired_cache(graph_env):
    stale = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - kg.CACHE_TTL_SEC - 60))
    graph_env.write_text(json.dumps({"built_at": stale, "marker": "stale"}), encoding="utf-8")
    graph = kg.build_graph(force=False)
    assert "marker" not in graph
    assert graph["total_nodes"] > 0


def test_build_graph_rejects_corrupt_cache(graph_env):
    graph_env.write_text("{ this is not json", encoding="utf-8")
    graph = kg.build_graph(force=False)
    assert graph["total_nodes"] > 0
    assert graph["edges"]


def test_build_graph_rejects_unparsable_timestamp(graph_env):
    graph_env.write_text(json.dumps({"built_at": "not-a-timestamp", "marker": "bad"}), encoding="utf-8")
    graph = kg.build_graph(force=False)
    assert "marker" not in graph
    assert graph["total_nodes"] > 0


def test_build_graph_survives_unwritable_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(kg, "GRAPH_CACHE", str(tmp_path))
    monkeypatch.setattr(kg, "_corpus_docs", lambda: [])
    graph = kg.build_graph(force=True)
    assert graph["total_nodes"] > 0
    assert tmp_path.is_dir()


def test_get_graph_stats_shape(graph_env):
    stats = kg.get_graph_stats(force=True)
    assert stats["total_nodes"] > 0
    assert sum(stats["node_counts"].values()) == stats["total_nodes"]
    assert sum(stats["edge_counts"].values()) == stats["total_edges"]
    assert stats["cache_ttl_sec"] == int(kg.CACHE_TTL_SEC)
    assert stats["cached"] is True
    assert stats["built_at"]


def test_search_entities_finds_real_ingredient(graph_env):
    out = kg.search_entities("ashwagandha")
    assert out["query"] == "ashwagandha"
    assert out["match_count"] == 1
    match = out["matches"][0]
    assert match["id"] == "ING:ING-ASHWAGANDHA"
    assert match["type"] == "ingredient"
    assert "ASHWAGANDHA" in match["name"]
    assert isinstance(match["edges"], list)
    assert len(match["edges"]) <= 8
    assert len(match["aliases"]) <= 6


def test_search_entities_blank_query(graph_env):
    assert kg.search_entities("   ") == {"query": "   ", "matches": []}


def test_search_entities_without_matches(graph_env):
    out = kg.search_entities("zzzz-no-such-entity")
    assert out["query"] == "zzzz-no-such-entity"
    assert out["match_count"] == 0
    assert out["matches"] == []


def test_search_entities_truncates_aliases_and_edges(monkeypatch):
    monkeypatch.setattr(kg, "build_graph", lambda force=False: _controlled_graph())
    out = kg.search_entities("alpha")
    assert out["match_count"] == 2
    first = out["matches"][0]
    assert first["id"] == "ING:X"
    assert len(first["aliases"]) == 6
    assert len(first["edges"]) == 8
    assert first["edges"][0] == {"relation": "rel0", "to": "T"}
    second = out["matches"][1]
    assert second["id"] == "REG:Y"
    assert second["aliases"] == []
    assert second["edges"] == []


def test_search_entities_honours_limit(monkeypatch):
    monkeypatch.setattr(kg, "build_graph", lambda force=False: _controlled_graph())
    out = kg.search_entities("alpha", limit=1)
    assert out["match_count"] == 1
    assert out["matches"][0]["id"] == "ING:X"


def test_search_entities_deduplicates_repeated_node_ids(monkeypatch):
    graph = _controlled_graph()
    graph["nodes"].append(dict(graph["nodes"][0]))
    monkeypatch.setattr(kg, "build_graph", lambda force=False: graph)
    out = kg.search_entities("alpha", limit=10)
    assert out["match_count"] == 2
    assert [match["id"] for match in out["matches"]] == ["ING:X", "REG:Y"]


def test_corpus_docs_prefers_qdrant_documents(monkeypatch):
    docs = [{"content": "served by qdrant"}]

    class _Store:
        def get_all_documents(self, limit=5000):
            return docs

    monkeypatch.setitem(sys.modules, "app.rag.qdrant_store", _qdrant_module(_Store))
    assert kg._corpus_docs() == docs


def test_corpus_docs_falls_back_to_knowledge_base(monkeypatch):
    docs = [{"content": "served by knowledge base"}]

    class _Store:
        def get_all_documents(self, limit=5000):
            return []

    monkeypatch.setitem(sys.modules, "app.rag.qdrant_store", _qdrant_module(_Store))
    monkeypatch.setitem(sys.modules, "app.rag.kb", _kb_module(lambda: docs))
    assert kg._corpus_docs() == docs


def test_corpus_docs_returns_empty_when_all_sources_fail(monkeypatch):
    class _Store:
        def __init__(self):
            raise RuntimeError("qdrant unavailable")

    def _broken_kb():
        raise RuntimeError("kb unavailable")

    monkeypatch.setitem(sys.modules, "app.rag.qdrant_store", _qdrant_module(_Store))
    monkeypatch.setitem(sys.modules, "app.rag.kb", _kb_module(_broken_kb))
    assert kg._corpus_docs() == []


@pytest.mark.xfail(
    reason="_build_entities assumes every botanical_synonyms value is a dict, so a malformed "
    "entry raises AttributeError instead of being skipped (knowledge_graph.py:72)",
    strict=False,
)
def test_build_entities_skips_malformed_synonym_entries():
    built = kg._build_entities(
        {
            "botanical_synonyms": {"ING-X": "not-a-dict"},
            "api_monographs": [],
            "acts_and_gazettes": [],
        }
    )
    assert not any(key.startswith("ING:") for key in built["nodes"])
    assert built["aliases"] == {}


@pytest.mark.xfail(
    reason="no botanical_identity edge is ever emitted between an ingredient and its botanical "
    "node, although the module contract documents that relation (knowledge_graph.py:132)",
    strict=False,
)
def test_build_edges_links_ingredient_to_botanical():
    built = kg._build_entities(LEXICON)
    edges = kg._build_edges(built["nodes"], [])
    assert any(
        edge["from"] == "ING:ING-Ashwagandha" and edge["to"] == "BOT:Withania somnifera"
        for edge in edges
    )


@pytest.mark.xfail(
    reason="regulatory-status compound nodes such as 'India/FSSAI — restricted' are typed "
    "'authority' and leak into the public authorities list (knowledge_graph.py:157)",
    strict=False,
)
def test_authorities_list_excludes_status_compounds(graph_env):
    graph = kg.build_graph(force=True)
    assert not any(" — " in name for name in graph["authorities"])


@pytest.mark.xfail(
    reason="search_entities appends a match before checking the limit, so limit=0 still returns "
    "one result (knowledge_graph.py:331)",
    strict=False,
)
def test_search_entities_zero_limit_returns_no_matches(graph_env):
    out = kg.search_entities("a", limit=0)
    assert out["match_count"] == 0
    assert out["matches"] == []
