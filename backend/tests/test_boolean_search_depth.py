import sys
import types
from typing import Any

import pytest

from app.rag import boolean_search as bs

PROBLEM = (
    "A synergistic herbal formulation of Ashwagandha with Brahmi "
    "for cognitive wellness in capsule form for the Indian market"
)

DOCS = [
    {"content": "alpha beta gamma delta", "source": "s1", "title": "Doc One"},
    {"content": "alpha only appears here", "source": "s2", "title": "Doc Two"},
    {"content": "beta gamma without alpha", "source": "s3", "title": "Doc Three"},
    {"content": "nothing relevant at all", "source": "s4", "title": "Doc Four"},
]


@pytest.fixture(autouse=True)
def _fresh_corpus():
    bs.invalidate_corpus_cache()
    yield
    bs.invalidate_corpus_cache()


@pytest.fixture
def seeded_corpus(monkeypatch):
    monkeypatch.setattr(bs, "_load_corpus", lambda: [dict(doc) for doc in DOCS])
    yield


def _stub_qdrant(module_cls_docs):
    module: Any = types.ModuleType("app.rag.qdrant_store")
    module.QdrantVectorStore = module_cls_docs
    return module


def _stub_kb(collector):
    module: Any = types.ModuleType("app.rag.kb")
    module.collect_knowledge_documents = collector
    return module


@pytest.mark.parametrize("expression", ["", "   ", "\t\n"])
def test_compile_rejects_empty_expression(expression):
    with pytest.raises(ValueError, match="empty boolean expression"):
        bs.compile_expression(expression)


@pytest.mark.parametrize("expression", ["alpha AND", "alpha OR NOT", "(alpha AND"])
def test_compile_rejects_dangling_operator(expression):
    with pytest.raises(ValueError, match="unexpected end of expression"):
        bs.compile_expression(expression)


@pytest.mark.parametrize("expression", ["alpha)", "alpha beta)", "alpha AND beta)"])
def test_compile_rejects_trailing_token(expression):
    with pytest.raises(ValueError, match="unexpected token"):
        bs.compile_expression(expression)


def test_compile_rejects_leading_operator():
    with pytest.raises(ValueError, match="unexpected token"):
        bs.compile_expression("AND alpha")


@pytest.mark.parametrize("expression", ["alpha:", "alpha :", "title=", "title ="])
def test_compile_rejects_field_without_value(expression):
    with pytest.raises(ValueError, match="missing value for field"):
        bs.compile_expression(expression)


def test_compile_accepts_unbalanced_open_parenthesis():
    node = bs.compile_expression("(alpha AND beta")
    assert node is not None


def test_compile_accepts_redundant_parentheses():
    node = bs.compile_expression("(alpha)")
    assert node is not None


def test_field_single_token_forms_are_equivalent():
    corpus = [{"content": "x", "year": 2024}]
    for expression in ("year:2024", "year=2024"):
        assert bs.search(expression, corpus=corpus)["matched"] == 1


def test_field_spaced_forms_are_equivalent():
    corpus = [{"content": "x", "year": 2024}]
    for expression in ("year : 2024", "year = 2024"):
        assert bs.search(expression, corpus=corpus)["matched"] == 1


def test_field_alias_resolution():
    corpus = [
        {"content": "x", "publication_number": "US-1234"},
        {"content": "y", "doc_id": "US-9999"},
    ]
    assert bs.search("patent_number:US-1234", corpus=corpus)["matched"] == 1
    assert bs.search("patent_number:US-9999", corpus=corpus)["matched"] == 1


def test_field_without_structured_metadata_matches_nothing():
    assert bs.search("patent_number:US-1", corpus=[{"content": "x"}])["matched"] == 0


def test_field_falls_back_to_text_for_jurisdiction():
    corpus = [
        {"content": "the application was granted in India"},
        {"content": "no location mentioned"},
    ]
    out = bs.search("jurisdiction:India", corpus=corpus)
    assert out["matched"] == 1
    assert out["results"][0]["content"] == "the application was granted in India"


def test_field_structured_value_wins_over_text():
    corpus = [{"content": "granted in India", "jurisdiction": "EP"}]
    assert bs.search("jurisdiction:EP", corpus=corpus)["matched"] == 1
    assert bs.search("jurisdiction:India", corpus=corpus)["matched"] == 0


def test_field_year_comparison_operators():
    corpus: list[dict[str, Any]] = [
        {"content": "recent", "publication_year": 2021},
        {"content": "old", "publication_year": 2019},
        {"content": "unknown vintage"},
    ]
    newer = bs.search("year = >2020", corpus=corpus)
    assert [hit["content"] for hit in newer["results"]] == ["recent"]
    older = bs.search("year = <2020", corpus=corpus)
    assert [hit["content"] for hit in older["results"]] == ["old"]


def test_field_year_equality_accepts_string_and_int():
    corpus: list[dict[str, Any]] = [{"content": "a", "year": "2021"}, {"content": "b", "year": 2020}]
    assert bs.search("year:2021", corpus=corpus)["matched"] == 1
    assert bs.search("year=2020", corpus=corpus)["matched"] == 1


def test_field_comparison_without_years_matches_nothing():
    corpus = [{"content": "no year metadata"}]
    assert bs.search("year = >2020", corpus=corpus)["matched"] == 0


def test_term_matches_whole_tokens_only():
    assert bs.search("cat", corpus=[{"content": "concatenate datasets"}])["matched"] == 0
    assert bs.search("cat", corpus=[{"content": "the cat sat"}])["matched"] == 1


def test_term_also_matches_source_field():
    corpus = [{"content": "the dataset", "source": "cat-farm"}]
    assert bs.search("cat", corpus=corpus)["matched"] == 1


def test_term_matching_is_case_insensitive():
    corpus = [{"content": "Ashwagandha extract"}]
    assert bs.search("ASHWAGANDHA", corpus=corpus)["matched"] == 1
    assert bs.search("ashwagandha", corpus=corpus)["matched"] == 1


def test_phrase_matches_substring_of_content():
    assert bs.search('"winter cherry"', corpus=[{"content": "a winter cherry extract"}])["matched"] == 1
    assert bs.search('"winter cherry"', corpus=[{"content": "a cherry extract"}])["matched"] == 0


def test_and_requires_every_term():
    corpus = [{"content": "alpha beta"}, {"content": "alpha only"}, {"content": "beta only"}]
    out = bs.search("alpha AND beta", corpus=corpus)
    assert out["matched"] == 1
    assert [hit["content"] for hit in out["results"]] == ["alpha beta"]


def test_or_accepts_any_term():
    corpus = [{"content": "alpha beta"}, {"content": "alpha only"}, {"content": "beta only"}]
    out = bs.search("alpha OR beta", corpus=corpus)
    assert out["matched"] == 3


def test_not_excludes_matching_documents():
    corpus = [{"content": "alpha present"}, {"content": "beta only"}]
    out = bs.search("NOT alpha", corpus=corpus)
    assert [hit["content"] for hit in out["results"]] == ["beta only"]


def test_double_negation_inverts_twice():
    corpus = [{"content": "alpha here"}, {"content": "beta here"}]
    out = bs.search("NOT NOT alpha", corpus=corpus)
    assert [hit["content"] for hit in out["results"]] == ["alpha here"]


def test_or_binds_looser_than_and():
    corpus = [{"content": "alpha"}, {"content": "beta gamma"}, {"content": "delta"}]
    out = bs.search("alpha OR beta AND gamma", corpus=corpus)
    assert sorted(hit["content"] for hit in out["results"]) == ["alpha", "beta gamma"]


def test_parentheses_override_precedence():
    corpus = [{"content": "alpha"}, {"content": "beta gamma"}, {"content": "delta"}]
    out = bs.search("((alpha OR beta) AND NOT gamma)", corpus=corpus)
    assert [hit["content"] for hit in out["results"]] == ["alpha"]


def test_unbalanced_expression_still_evaluates():
    out = bs.search("(alpha AND beta", corpus=[{"content": "alpha beta"}])
    assert out["matched"] == 1
    assert out["expression"] == "(alpha AND beta"


def test_parenthesised_term_evaluates():
    out = bs.search("(alpha)", corpus=[{"content": "alpha here"}])
    assert out["matched"] == 1


def test_near_expression_evaluates_without_raising():
    out = bs.search("alpha NEAR/3 beta", corpus=[{"content": "alpha beta"}])
    assert out["expression"] == "alpha NEAR/3 beta"
    assert out["leaf_terms"] == ["ALPHA", "BETA"]
    assert isinstance(out["matched"], int)


def test_near_requires_both_operands():
    corpus = [{"content": "alpha only"}, {"content": "beta only"}]
    assert bs.search("alpha NEAR/5 beta", corpus=corpus)["matched"] == 0


def test_search_reports_leaf_terms_and_ratio_for_single_term():
    out = bs.search("alpha", corpus=[{"content": "alpha present"}])
    assert out["expression"] == "alpha"
    assert out["leaf_terms"] == ["ALPHA"]
    assert out["matched"] == 1
    hit = out["results"][0]
    assert hit["bool_matches"] == 1
    assert hit["bool_ratio"] == 1.0
    assert hit["bool_rank"] == 1


def test_search_ranks_documents_matching_more_leaves_first():
    corpus = [
        {"content": "beta only"},
        {"content": "alpha and beta together"},
        {"content": "alpha only"},
    ]
    out = bs.search("alpha OR beta", corpus=corpus)
    assert out["matched"] == 3
    assert out["results"][0]["content"] == "alpha and beta together"
    assert [hit["bool_rank"] for hit in out["results"]] == [1, 2, 3]


def test_search_respects_top_k():
    corpus = [{"content": f"alpha filler {index}"} for index in range(5)]
    out = bs.search("alpha", corpus=corpus, top_k=2)
    assert out["matched"] == 5
    assert len(out["results"]) == 2
    assert [hit["bool_rank"] for hit in out["results"]] == [1, 2]


def test_search_skips_documents_without_content():
    corpus: list[dict[str, Any]] = [
        {"content": "   "},
        {"content": None},
        {"title": "no content key"},
        {"content": "alpha here"},
    ]
    out = bs.search("alpha", corpus=corpus)
    assert out["matched"] == 1
    assert [hit["content"] for hit in out["results"]] == ["alpha here"]


def test_search_over_empty_corpus():
    out = bs.search("alpha", corpus=[])
    assert out["matched"] == 0
    assert out["results"] == []
    assert out["leaf_terms"] == ["ALPHA"]


def test_doc_text_normalises_content():
    assert bs._doc_text({"content": "Hello World"}) == "hello world"
    assert bs._doc_text({"content": None}) == ""
    assert bs._doc_text({}) == ""
    assert bs._doc_text({"content": 42}) == "42"


def test_search_uses_cached_corpus():
    bs._CORPUS_CACHE = [{"content": "alpha cached", "source": "cache"}]
    out = bs.search("alpha")
    assert out["matched"] == 1
    assert out["results"][0]["source"] == "cache"


def test_invalidate_corpus_cache_drops_cached_documents(monkeypatch):
    bs._CORPUS_CACHE = [{"content": "alpha cached", "source": "cache"}]
    bs.invalidate_corpus_cache()
    assert bs._CORPUS_CACHE == []
    import app.rag.retrieval_pipeline as retrieval_pipeline

    monkeypatch.setattr(
        retrieval_pipeline.HybridRetriever,
        "_bm25_corpus",
        [{"content": "alpha from bm25", "source": "bm25"}],
    )
    docs = bs._load_corpus()
    assert [doc["source"] for doc in docs] == ["bm25"]


def test_load_corpus_prefers_existing_bm25_index(monkeypatch):
    import app.rag.retrieval_pipeline as retrieval_pipeline

    seeded = [{"content": "alpha from bm25", "source": "bm25"}]
    monkeypatch.setattr(retrieval_pipeline.HybridRetriever, "_bm25_corpus", seeded)
    assert bs._load_corpus() == seeded
    assert bs._CORPUS_CACHE == seeded


def test_load_corpus_falls_back_to_knowledge_base(monkeypatch):
    import app.rag.retrieval_pipeline as retrieval_pipeline

    monkeypatch.setattr(retrieval_pipeline.HybridRetriever, "_bm25_corpus", [])

    class _EmptyStore:
        def get_all_documents(self, limit=5000):
            return []

    monkeypatch.setitem(sys.modules, "app.rag.qdrant_store", _stub_qdrant(_EmptyStore))
    monkeypatch.setitem(
        sys.modules,
        "app.rag.kb",
        _stub_kb(lambda: [{"content": "alpha from kb", "source": "kb"}]),
    )
    docs = bs._load_corpus()
    assert [doc["source"] for doc in docs] == ["kb"]
    assert bs._CORPUS_CACHE == docs


def test_load_corpus_returns_empty_when_every_source_fails(monkeypatch):
    import app.rag.retrieval_pipeline as retrieval_pipeline

    monkeypatch.setattr(retrieval_pipeline.HybridRetriever, "_bm25_corpus", [])

    class _BrokenStore:
        def __init__(self):
            raise RuntimeError("qdrant unavailable")

    def _broken_kb():
        raise RuntimeError("kb unavailable")

    monkeypatch.setitem(sys.modules, "app.rag.qdrant_store", _stub_qdrant(_BrokenStore))
    monkeypatch.setitem(sys.modules, "app.rag.kb", _stub_kb(_broken_kb))
    assert bs._load_corpus() == []


def test_search_loads_corpus_implicitly(monkeypatch):
    import app.rag.retrieval_pipeline as retrieval_pipeline

    monkeypatch.setattr(retrieval_pipeline.HybridRetriever, "_bm25_corpus", [])

    class _EmptyStore:
        def get_all_documents(self, limit=5000):
            return []

    monkeypatch.setitem(sys.modules, "app.rag.qdrant_store", _stub_qdrant(_EmptyStore))
    monkeypatch.setitem(
        sys.modules,
        "app.rag.kb",
        _stub_kb(lambda: [{"content": "alpha implicit load", "source": "kb"}]),
    )
    out = bs.search("alpha")
    assert out["matched"] == 1
    assert out["results"][0]["source"] == "kb"


def test_merged_reference_list_deduplicates_across_searches():
    shared = {"source": "s1", "content": "shared hit", "bool_matches": 3}
    other = {"source": "s2", "content": "second hit", "bool_matches": 1}
    merged = bs.merged_reference_list(
        [
            {"name": "Boolean Search 1", "results": [shared, other]},
            {"name": "Boolean Search 2", "results": [dict(shared)]},
        ]
    )
    assert len(merged) == 2
    assert merged[0]["bool_searches"] == ["Boolean Search 1", "Boolean Search 2"]
    assert merged[0]["bool_search_count"] == 2
    assert merged[1]["bool_search_count"] == 1


def test_merged_reference_list_breaks_ties_on_bool_matches():
    strong = {"source": "s", "content": "strong", "bool_matches": 5}
    weak = {"source": "s", "content": "weak", "bool_matches": 2}
    merged = bs.merged_reference_list([{"name": "S1", "results": [weak, strong]}])
    assert [entry["content"] for entry in merged] == ["strong", "weak"]


def test_merged_reference_list_respects_top_k():
    docs = [
        {"source": f"s{index}", "content": f"c{index}", "bool_matches": index}
        for index in range(5)
    ]
    merged = bs.merged_reference_list([{"name": "S1", "results": docs}], top_k=2)
    assert [entry["content"] for entry in merged] == ["c4", "c3"]


def test_merged_reference_list_counts_each_search_once():
    doc = {"source": "s", "content": "same", "bool_matches": 1}
    merged = bs.merged_reference_list([{"name": "S1", "results": [doc, dict(doc)]}])
    assert len(merged) == 1
    assert merged[0]["bool_searches"] == ["S1"]
    assert merged[0]["bool_search_count"] == 1


def test_merged_reference_list_tolerates_missing_identifiers():
    doc = {"content": "no identifiers at all", "bool_matches": 1}
    merged = bs.merged_reference_list([{"name": "S1", "results": [doc]}])
    assert len(merged) == 1
    assert merged[0]["bool_searches"] == ["S1"]


def test_merged_reference_list_tolerates_missing_results():
    assert bs.merged_reference_list([{"name": "S1"}]) == []
    assert bs.merged_reference_list([]) == []


def test_fmt_quotes_multiword_terms():
    assert bs._fmt("ashwagandha") == "ASHWAGANDHA"
    assert bs._fmt("winter cherry") == '"winter cherry"'


def test_term_variants_expand_lexicon_members(monkeypatch):
    monkeypatch.setattr(
        bs,
        "_SYNONYMS",
        {"ING-TEST": ["ashwagandha", "winter cherry", "asagandh"]},
    )
    variants = bs._term_variants("Ashwagandha")
    assert variants[0] == "ashwagandha"
    assert set(variants) == {"ashwagandha", "winter cherry", "asagandh"}
    assert len(variants) == len(set(variants))


def test_term_variants_keep_unknown_terms(monkeypatch):
    monkeypatch.setattr(bs, "_SYNONYMS", {"ING-TEST": ["ashwagandha"]})
    assert bs._term_variants("compound") == ["compound"]


def test_is_botanical_term(monkeypatch):
    monkeypatch.setattr(bs, "_SYNONYMS", {"ING-TEST": ["ashwagandha"]})
    assert bs._is_botanical_term("ashwagandha") is True
    assert bs._is_botanical_term("paracetamol") is False


def test_load_synonyms_reads_shipped_lexicon():
    synonyms = bs._load_synonyms()
    assert synonyms
    assert "ING-ASHWAGANDHA" in synonyms
    names = synonyms["ING-ASHWAGANDHA"]
    assert names
    assert names == list(dict.fromkeys(names))
    assert all(name == name.lower() and len(name) > 1 for name in names)


def test_load_synonyms_returns_empty_when_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "_SYNONYMS_PATH", str(tmp_path / "absent.json"))
    assert bs._load_synonyms() == {}


def test_meaningful_terms_prefers_botanical_tokens():
    terms = bs._meaningful_terms("ashwagandha capsule wellness blend 2024")
    assert terms[0] == "ashwagandha"
    assert "2024" not in terms
    assert terms.index("capsule") < terms.index("blend")
    assert terms.index("capsule") < terms.index("wellness")


def test_meaningful_terms_drops_stopwords_and_duplicates():
    assert bs._meaningful_terms("the method of the method for ashwagandha") == ["ashwagandha"]


def test_meaningful_terms_keeps_quoted_phrases():
    terms = bs._meaningful_terms('"winter cherry" extract')
    assert "winter cherry" in terms
    assert "extract" in terms
    assert len(terms) <= 6


def test_meaningful_terms_caps_at_six_tokens():
    terms = bs._meaningful_terms("alpha beta gamma delta epsilon zeta eta theta iota kappa")
    assert len(terms) == 6


def test_meaningful_terms_empty_for_stopword_only_query():
    assert bs._meaningful_terms("a the of to is are") == []
    assert bs._meaningful_terms("1234 5678") == []


def test_build_searches_returns_five_named_strategies(seeded_corpus):
    plans = bs.build_searches(PROBLEM, top_k=4, jurisdiction="IN")
    assert [plan["name"] for plan in plans] == [
        "Boolean Search 1",
        "Boolean Search 2",
        "Boolean Search 3",
        "Boolean Search 4",
        "Boolean Search 5",
    ]
    for plan in plans:
        assert plan["expression"]
        assert isinstance(plan["matched"], int)
        assert isinstance(plan["results"], list)
        assert isinstance(plan["leaf_terms"], list)
        bs.compile_expression(plan["expression"])


def test_build_searches_is_deterministic(seeded_corpus):
    first = bs.build_searches(PROBLEM, top_k=3, jurisdiction="IN")
    second = bs.build_searches(PROBLEM, top_k=3, jurisdiction="IN")
    assert first == second


def test_build_searches_returns_empty_for_stopword_query(seeded_corpus):
    assert bs.build_searches("a the of to is are") == []
    assert bs.build_searches("1234 5678") == []


@pytest.mark.xfail(
    reason="per-leaf match views are rebuilt for every leaf, so bool_matches counts each leaf "
    "several times and bool_ratio can exceed 1.0 (boolean_search.py:486)",
    strict=False,
)
def test_bool_ratio_never_exceeds_one():
    out = bs.search("alpha AND beta", corpus=[{"content": "alpha beta"}])
    hit = out["results"][0]
    assert hit["bool_matches"] <= len(out["leaf_terms"])
    assert hit["bool_ratio"] <= 1.0


@pytest.mark.xfail(
    reason="_near_match looks up uppercase parser tokens in a lowercase position map, so the "
    "NEAR operator never matches any document (boolean_search.py:389)",
    strict=False,
)
def test_near_matches_terms_within_window():
    corpus = [
        {"content": "alpha beta gamma"},
        {"content": "alpha one two three four five six seven beta"},
    ]
    out = bs.search("alpha NEAR/5 beta", corpus=corpus)
    assert [hit["content"] for hit in out["results"]] == ["alpha beta gamma"]


@pytest.mark.xfail(
    reason="quoted values keep the internal PHRASE: token prefix, so `field = \"value\"` never "
    "matches (boolean_search.py:216 and boolean_search.py:252)",
    strict=False,
)
def test_quoted_field_value_after_equals():
    corpus = [{"content": "x", "title": "Doc One"}]
    out = bs.search('title = "Doc One"', corpus=corpus)
    assert out["matched"] == 1


@pytest.mark.xfail(
    reason="Boolean Search 3 is skipped entirely when jurisdiction is None, returning only 4 of "
    "the 5 documented strategies (boolean_search.py:570)",
    strict=False,
)
def test_build_searches_without_jurisdiction_returns_five(seeded_corpus):
    plans = bs.build_searches(PROBLEM, jurisdiction=None)
    assert len(plans) == 5
