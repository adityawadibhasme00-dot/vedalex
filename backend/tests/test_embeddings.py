import sys
import types
from typing import Any

import numpy as np
import pytest

from app.rag import embeddings as emb


@pytest.fixture
def engine_cls(monkeypatch):
    monkeypatch.setattr(emb.EmbeddingEngine, "_instance", None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("IPSAKTI_USE_BGE_M3", "0")
    yield emb.EmbeddingEngine


def _stub_sentence_transformers(encoder_cls):
    module: Any = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = encoder_cls
    return module


class _RecordingOpenAI:
    created: list[Any] = []
    calls: list[Any] = []

    def __init__(self, api_key=None, timeout=None):
        self.api_key = api_key
        self.timeout = timeout
        _RecordingOpenAI.created.append(self)
        self.embeddings = self

    def create(self, model=None, input=None):
        _RecordingOpenAI.calls.append((model, list(input)))
        data = [
            types.SimpleNamespace(embedding=[float(sum(map(ord, text)))] * emb.OPENAI_3_LARGE_DIM)
            for text in input
        ]
        return types.SimpleNamespace(data=data)


@pytest.fixture
def recording_openai(monkeypatch):
    import openai

    _RecordingOpenAI.created = []
    _RecordingOpenAI.calls = []
    monkeypatch.setattr(openai, "OpenAI", _RecordingOpenAI)
    yield _RecordingOpenAI
    _RecordingOpenAI.created = []
    _RecordingOpenAI.calls = []


def test_hashing_fallback_when_disabled_and_keyless(engine_cls):
    engine = engine_cls()
    assert engine.get_provider() == "hashing-fallback"
    assert engine.get_dim() == emb.HASH_DIM == 192


def test_provider_and_dim_trigger_initialisation(monkeypatch):
    monkeypatch.setattr(emb.EmbeddingEngine, "_instance", None)
    monkeypatch.setenv("IPSAKTI_USE_BGE_M3", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert emb.EmbeddingEngine.get_provider() == "hashing-fallback"
    assert emb.EmbeddingEngine.get_dim() == 192
    monkeypatch.setattr(emb.EmbeddingEngine, "_instance", None)


def test_hash_embedding_is_deterministic_and_normalised(engine_cls):
    engine = engine_cls()
    first = engine.embed(["ashwagandha extract"])
    second = engine.embed(["ashwagandha extract"])
    assert first.shape == (1, emb.HASH_DIM)
    assert first.dtype == np.float32
    np.testing.assert_array_equal(first, second)
    assert np.linalg.norm(first) == pytest.approx(1.0, abs=1e-5)


def test_hash_embedding_separates_different_texts(engine_cls):
    engine = engine_cls()
    left = engine.embed(["ashwagandha extract"])
    right = engine.embed(["brahmi extract"])
    assert not np.allclose(left, right)


def test_hash_embedding_zero_vector_for_blank_text(engine_cls):
    engine = engine_cls()
    for blank in ["", "   ", "\t\n"]:
        vector = engine.embed([blank])
        assert vector.shape == (1, emb.HASH_DIM)
        assert np.count_nonzero(vector) == 0


def test_embed_batch_and_query_shapes(engine_cls):
    engine = engine_cls()
    batch = engine.embed(["alpha", "beta", "gamma"])
    assert batch.shape == (3, 192)
    assert batch.dtype == np.float32
    query = engine.embed_query("single query")
    assert query.shape == (1, 192)
    assert np.linalg.norm(query[0]) == pytest.approx(1.0, abs=1e-5)


def test_bge_m3_provider_when_model_loads(engine_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_BGE_M3", "1")
    created = {}

    class _SentenceTransformer:
        def __init__(self, model_name, **kwargs):
            created["model_name"] = model_name

        def encode(self, texts, **kwargs):
            created["encode_kwargs"] = kwargs
            return np.full((len(texts), emb.BGE_M3_DIM), 0.5, dtype=np.float32)

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _stub_sentence_transformers(_SentenceTransformer),
    )
    engine = engine_cls()
    assert engine.get_provider() == "bge-m3"
    assert engine.get_dim() == emb.BGE_M3_DIM == 1024
    assert created["model_name"] == "BAAI/bge-m3"
    vector = engine.embed(["withania somnifera"])
    assert created["encode_kwargs"]["normalize_embeddings"] is True
    assert created["encode_kwargs"]["show_progress_bar"] is False
    assert created["encode_kwargs"]["batch_size"] == 32
    assert vector.shape == (1, 1024)
    assert np.all(vector == 0.5)


def test_bge_m3_model_name_override(engine_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_BGE_M3", "1")
    monkeypatch.setenv("IPSAKTI_EMBEDDING_MODEL", "custom/bge")
    created = {}

    class _SentenceTransformer:
        def __init__(self, model_name, **kwargs):
            created["model_name"] = model_name

        def encode(self, texts, **kwargs):
            return np.zeros((len(texts), emb.BGE_M3_DIM), dtype=np.float32)

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _stub_sentence_transformers(_SentenceTransformer),
    )
    engine = engine_cls()
    assert engine.get_provider() == "bge-m3"
    assert created["model_name"] == "custom/bge"


def test_bge_m3_load_failure_falls_back_to_hashing(engine_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_BGE_M3", "1")

    class _ExplodingEncoder:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no weights offline")

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _stub_sentence_transformers(_ExplodingEncoder),
    )
    engine = engine_cls()
    assert engine.get_provider() == "hashing-fallback"
    assert engine.get_dim() == 192
    assert engine.embed(["x"]).shape == (1, 192)


def test_openai_provider_batches_requests(engine_cls, recording_openai, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    engine = engine_cls()
    assert engine.get_provider() == "openai-3-large"
    assert engine.get_dim() == emb.OPENAI_3_LARGE_DIM == 1536
    assert recording_openai.created[0].api_key == "unit-test-key"
    texts = [f"document number {index} alpha" for index in range(450)]
    vectors = engine.embed(texts)
    assert [len(batch) for _model, batch in recording_openai.calls] == [200, 200, 50]
    assert all(model == "text-embedding-3-large" for model, _batch in recording_openai.calls)
    assert vectors.shape == (450, 1536)
    expected = np.array(
        [[float(sum(map(ord, text)))] * 1536 for text in texts],
        dtype=np.float32,
    )
    np.testing.assert_allclose(vectors, expected)


def test_openai_client_failure_falls_back_to_hashing(engine_cls, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")

    class _ExplodingClient:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("bad key")

    import openai

    monkeypatch.setattr(openai, "OpenAI", _ExplodingClient)
    engine = engine_cls()
    assert engine.get_provider() == "hashing-fallback"
    assert engine.get_dim() == 192


def test_singletons_share_state_between_calls(engine_cls, monkeypatch):
    monkeypatch.setenv("IPSAKTI_USE_BGE_M3", "0")
    first = engine_cls()
    second = engine_cls()
    assert second is first
    assert engine_cls.get_provider() == "hashing-fallback"


@pytest.mark.xfail(
    reason="embed() silently falls back to 192-dim hashing vectors while get_dim() still reports "
    "1024 when the bge model handle is gone, producing a dimension mismatch (embeddings.py:102)",
    strict=False,
)
def test_embed_dimension_matches_reported_dimension(engine_cls):
    engine = engine_cls()
    engine._provider = "bge-m3"
    engine._dim = emb.BGE_M3_DIM
    engine._model = None
    assert engine.get_dim() == emb.BGE_M3_DIM
    vector = engine.embed(["withania somnifera"])
    assert vector.shape[1] == engine.get_dim()
