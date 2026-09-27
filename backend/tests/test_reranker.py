import sys
import types
from typing import Any

import numpy as np
import pytest

from app.rag.reranker import Reranker


@pytest.fixture
def reranker_cls(monkeypatch):
    monkeypatch.setattr(Reranker, "_instance", None)
    monkeypatch.setattr(Reranker, "_model", None)
    monkeypatch.setattr(Reranker, "_available", False)
    monkeypatch.setattr(Reranker, "_attempted", False)
    yield Reranker


def _stub_reranker_module(cross_encoder_cls):
    module: Any = types.ModuleType("sentence_transformers")
    module.CrossEncoder = cross_encoder_cls
    return module


class _OrderedModel:
    def __init__(self, scores):
        self.scores = scores
        self.pairs: Any = None

    def predict(self, pairs, show_progress_bar=False):
        self.pairs = pairs
        return list(self.scores)


class _BrokenModel:
    def predict(self, pairs, show_progress_bar=False):
        raise RuntimeError("cross encoder exploded")


def _enabled_instance(reranker_cls, monkeypatch, model):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")
    instance = reranker_cls()
    instance._model = model
    instance._available = True
    return instance


def test_disabled_by_environment(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")

    class _WouldLoad:
        def __init__(self, *args, **kwargs):
            raise AssertionError("model must not load while disabled")

    monkeypatch.setitem(sys.modules, "sentence_transformers", _stub_reranker_module(_WouldLoad))
    instance = reranker_cls()
    assert reranker_cls.is_available() is False
    assert instance._model is None
    assert instance.rerank("q", [{"content": "a"}], top_k=1) == [
        {"content": "a", "rerank_score": 1.0, "original_rank": 0}
    ]


def test_load_failure_falls_back_to_passthrough(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "1")

    class _ExplodingCrossEncoder:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no weights offline")

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _stub_reranker_module(_ExplodingCrossEncoder),
    )
    instance = reranker_cls()
    assert reranker_cls.is_available() is False
    out = instance.rerank("q", [{"content": "a", "score": 0.4}], top_k=1)
    assert out == [{"content": "a", "score": 0.4, "rerank_score": 0.4, "original_rank": 0}]


def test_successful_load_wires_model_and_scores(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "1")
    monkeypatch.setenv("IPSAKTI_RERANKER_MODEL", "stub/reranker")
    created: dict[str, Any] = {}

    class _CrossEncoder:
        def __init__(self, model_name, max_length=512, device=None):
            created.update(model_name=model_name, max_length=max_length, device=device)

        def predict(self, pairs, show_progress_bar=False):
            return [1.0] * len(pairs)

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _stub_reranker_module(_CrossEncoder),
    )
    instance = reranker_cls()
    assert instance._available is True
    assert created == {"model_name": "stub/reranker", "max_length": 512, "device": "cpu"}
    out = instance.rerank("q", [{"content": "a"}], top_k=1)
    assert out[0]["rerank_score"] == 1.0
    assert out[0]["original_rank"] == 0


def test_constructor_is_singleton_and_loads_once(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")
    first = reranker_cls()
    first._model = "sentinel"
    second = reranker_cls()
    assert second is first
    assert second._model == "sentinel"


def test_passthrough_preserves_order_and_scores(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")
    instance = reranker_cls()
    passages = [
        {"content": "first", "score": 0.9},
        {"content": "second"},
        {"content": "third", "score": 0.1},
    ]
    out = instance.rerank("query", passages, top_k=5)
    assert [item["content"] for item in out] == ["first", "second", "third"]
    assert [item["rerank_score"] for item in out] == [0.9, 0.5, 0.1]
    assert [item["original_rank"] for item in out] == [0, 1, 2]
    assert passages == [
        {"content": "first", "score": 0.9},
        {"content": "second"},
        {"content": "third", "score": 0.1},
    ]


def test_passthrough_respects_top_k(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")
    instance = reranker_cls()
    passages = [{"content": str(i)} for i in range(6)]
    out = instance.rerank("query", passages, top_k=2)
    assert [item["content"] for item in out] == ["0", "1"]
    assert [item["original_rank"] for item in out] == [0, 1]
    assert len(passages) == 6


def test_rerank_empty_input(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")
    instance = reranker_cls()
    assert instance.rerank("query", []) == []
    assert instance.rerank("query", [], top_k=3) == []


def test_model_scores_sort_and_truncate(reranker_cls, monkeypatch):
    model = _OrderedModel([0.2, 0.9, 0.6])
    instance = _enabled_instance(reranker_cls, monkeypatch, model)
    passages = [{"content": "x"}, {"content": "y"}, {"content": "z"}]
    out = instance.rerank("query", passages, top_k=2)
    assert [(item["content"], item["rerank_score"], item["original_rank"]) for item in out] == [
        ("y", 0.9, 1),
        ("z", 0.6, 2),
    ]
    assert "rerank_score" not in passages[0]


def test_model_receives_truncated_content(reranker_cls, monkeypatch):
    model = _OrderedModel([1.0])
    instance = _enabled_instance(reranker_cls, monkeypatch, model)
    long_content = "a" * 600
    out = instance.rerank("query", [{"content": long_content}], top_k=1)
    query, passage = model.pairs[0]
    assert query == "query"
    assert len(passage) == 512
    assert out[0]["rerank_score"] == 1.0


def test_model_receives_numpy_scores(reranker_cls, monkeypatch):
    class _NumpyModel:
        def predict(self, pairs, show_progress_bar=False):
            return np.array([0.3, 0.9, 0.6])

    instance = _enabled_instance(reranker_cls, monkeypatch, _NumpyModel())
    out = instance.rerank("query", [{"content": "x"}, {"content": "y"}, {"content": "z"}], top_k=3)
    assert [item["rerank_score"] for item in out] == [0.9, 0.6, 0.3]
    assert [item["original_rank"] for item in out] == [1, 2, 0]


def test_model_failure_falls_back_to_original_order(reranker_cls, monkeypatch):
    instance = _enabled_instance(reranker_cls, monkeypatch, _BrokenModel())
    passages = [{"content": "a", "score": 0.9}, {"content": "b", "score": 0.2}]
    out = instance.rerank("query", passages, top_k=5)
    assert [item["content"] for item in out] == ["a", "b"]
    assert [item["rerank_score"] for item in out] == [0.9, 0.2]


def test_model_handles_missing_content_key(reranker_cls, monkeypatch):
    model = _OrderedModel([0.7])
    instance = _enabled_instance(reranker_cls, monkeypatch, model)
    out = instance.rerank("query", [{"score": 0.7}], top_k=1)
    assert model.pairs[0] == ("query", "")
    assert out[0]["rerank_score"] == 0.7


def test_passthrough_used_when_model_missing(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")
    instance = reranker_cls()
    instance._available = True
    instance._model = None
    out = instance.rerank("query", [{"content": "a"}], top_k=1)
    assert out == [{"content": "a", "rerank_score": 1.0, "original_rank": 0}]


@pytest.mark.xfail(
    reason="rerank() zips predictions against passages, so a short predict() result silently "
    "drops passages instead of falling back (reranker.py:99)",
    strict=False,
)
def test_rerank_keeps_every_passage_when_predict_returns_fewer_scores(reranker_cls, monkeypatch):
    instance = _enabled_instance(reranker_cls, monkeypatch, _OrderedModel([0.9]))
    out = instance.rerank("query", [{"content": "x"}, {"content": "y"}, {"content": "z"}], top_k=10)
    assert [item["content"] for item in out] == ["x", "y", "z"]


@pytest.mark.xfail(
    reason="is_available() reads the class attribute _available while _try_load() writes the "
    "instance attribute, so a successfully loaded reranker still reports unavailable "
    "(reranker.py:66)",
    strict=False,
)
def test_is_available_true_after_successful_load(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "1")

    class _CrossEncoder:
        def __init__(self, *args, **kwargs):
            pass

        def predict(self, pairs, show_progress_bar=False):
            return [1.0] * len(pairs)

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _stub_reranker_module(_CrossEncoder),
    )
    instance = reranker_cls()
    assert instance._model is not None
    assert reranker_cls.is_available() is True


@pytest.mark.xfail(
    reason="the singleton marks itself attempted on first init and never reloads, so enabling "
    "IPSAKTI_USE_RERANKER after the first construction leaves the reranker unloaded (reranker.py:35)",
    strict=False,
)
def test_reranker_reloads_when_enabled_after_initial_disable(reranker_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "0")
    instance = reranker_cls()
    assert instance._model is None

    class _CrossEncoder:
        def __init__(self, *args, **kwargs):
            pass

        def predict(self, pairs, show_progress_bar=False):
            return [1.0] * len(pairs)

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _stub_reranker_module(_CrossEncoder),
    )
    monkeypatch.setenv("IPSAKTI_USE_RERANKER", "1")
    reloaded = reranker_cls()
    assert reloaded is instance
    assert instance._model is not None
