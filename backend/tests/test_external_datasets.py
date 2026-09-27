"""Tests for the external official-dataset harvesters and the committed snapshot.

The snapshot is committed data, so these tests verify the snapshot is internally
consistent and properly attributed, and that harvesters degrade to [] rather
than raising when the network is unavailable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.rag.datasources import external as ex
from app.rag.datasources import harvest_multiomics


# ---------------------------------------------------------------------------
# Provenance contract
# ---------------------------------------------------------------------------

def test_snapshot_present():
    assert ex.snapshot_manifest() is not None, "run tools/harvest_external_datasets"


def test_every_dataset_is_attributed():
    m = ex.snapshot_manifest()
    assert m["datasets"]
    for d in m["datasets"]:
        assert d.get("publisher"), f"{d['source']} missing publisher"
        assert d.get("license"), f"{d['source']} missing license"
        assert d.get("license_url"), f"{d['source']} missing license_url"
        assert d.get("citation"), f"{d['source']} missing citation"
        assert d.get("endpoints"), f"{d['source']} missing endpoints"
        assert d.get("records", 0) > 0, f"{d['source']} harvested no records"


def test_every_dataset_records_a_sha256_that_matches():
    m = ex.snapshot_manifest()
    for d in m["datasets"]:
        path = Path(ex.SNAPSHOT_DIR) / d["file"]
        assert path.is_file(), f"missing {d['file']}"
        import hashlib

        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == d["sha256"], f"{d['file']} checksum drifted"


def test_record_count_matches_the_payload():
    m = ex.snapshot_manifest()
    for d in m["datasets"]:
        path = Path(ex.SNAPSHOT_DIR) / d["file"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert len(payload["documents"]) == d["records"], f"{d['file']} count mismatch"


def test_unavailable_sources_are_declared_not_faked():
    """Restricted sources must be recorded, never silently invented."""
    declared = {u["source"] for u in ex.UNAVAILABLE_SOURCES}
    for expected in ("tkdl", "api_monographs", "patent_fulltext"):
        assert expected in declared, f"{expected} must be declared unavailable"
    for u in ex.UNAVAILABLE_SOURCES:
        assert u.get("reason"), f"{u['source']} missing a reason"
        assert u.get("status")
    assert ex.snapshot_manifest()["unavailable_sources"]


# ---------------------------------------------------------------------------
# Record contract
# ---------------------------------------------------------------------------

def _snapshot_docs():
    return ex.load_external_snapshot()


def test_snapshot_replays_documents():
    docs = _snapshot_docs()
    assert len(docs) == sum(d["records"] for d in ex.snapshot_manifest()["datasets"])


def test_every_record_has_authority_and_citable_url():
    for d in _snapshot_docs():
        assert d.get("authority")
        assert d.get("source_url", "").startswith("https://")
        assert d.get("authority_level", 0) >= 5, "external sources are primary"


def test_every_record_carries_a_resolvable_identifier():
    required = {
        "GBIF-": "gbif_usage_key",
        "PUBCHEM-": "pubchem_cid",
        "UNIPROT-": "uniprot_accession",
        "NCBI-GENE-": "ncbi_gene_id",
    }
    seen = 0
    for d in _snapshot_docs():
        for prefix, field in required.items():
            if d["doc_id"].startswith(prefix):
                assert d.get(field), f"{d['doc_id']} has no {field}"
                seen += 1
    assert seen > 0, "no typed records in the snapshot"


def test_gbif_records_cover_every_indexed_ingredient():
    """Plant taxonomy must line up with botanical_synonyms.json."""
    kb = Path(ex.SNAPSHOT_DIR).parents[1] / "app" / "knowledge" / "botanical_synonyms.json"
    known = set(json.loads(kb.read_text(encoding="utf-8")))
    covered = {d.get("canonical_id") for d in _snapshot_docs() if d.get("canonical_id")}
    assert known <= covered, f"uncovered ingredients: {known - covered}"


def test_gbif_family_is_present():
    for d in _snapshot_docs():
        if d["doc_id"].startswith("GBIF-"):
            assert d.get("gbif_family"), f"{d['doc_id']} has no family"


def test_records_inherit_provenance_fields():
    for d in _snapshot_docs():
        assert d.get("external_source")
        assert d.get("external_license")
        assert d.get("external_retrieved")


def test_no_placeholder_or_empty_content():
    for d in _snapshot_docs():
        assert len(d.get("content", "")) > 40, f"{d['doc_id']} has thin content"


# ---------------------------------------------------------------------------
# Resilience
# ---------------------------------------------------------------------------

def test_harvesters_return_empty_offline(monkeypatch):
    """A network failure must yield [], never raise into the KB load path."""
    monkeypatch.setattr(ex, "_http_json", lambda *a, **k: None)
    assert ex.harvest_gbif_taxonomy(timeout=1) == []
    assert ex.harvest_pubchem_compounds(timeout=1) == []
    assert ex.harvest_uniprot_entries(timeout=1) == []
    assert ex.harvest_ncbi_genes(timeout=1) == []


def test_missing_snapshot_is_not_fatal(monkeypatch, tmp_path):
    monkeypatch.setattr(ex, "SNAPSHOT_DIR", str(tmp_path))
    assert ex.snapshot_manifest() is None
    assert ex.load_external_snapshot() == []
    status = ex.external_status()
    assert status["snapshot_present"] is False
    assert status["unavailable_sources"]


def test_harvest_multiomics_includes_snapshot_without_network(monkeypatch):
    """The default KB load must pick the snapshot up and make no network call."""
    def _boom(*a, **k):
        raise AssertionError("offline KB load attempted a network call")

    monkeypatch.setattr(ex, "_http_json", _boom)
    docs = harvest_multiomics(include_live=False)
    assert any(d["doc_id"].startswith("GBIF-") for d in docs)


def test_harvest_multiomics_live_is_additive(monkeypatch):
    base = harvest_multiomics(include_live=False)
    monkeypatch.setattr(ex, "_http_json", lambda *a, **k: None)
    with_live = harvest_multiomics(include_live=True)
    assert len(with_live) == len(base), "failed live calls must not drop snapshot docs"


def test_snapshot_dir_is_inside_backend_data():
    """The snapshot must live in backend/data so the manifest tracks it."""
    assert Path(ex.SNAPSHOT_DIR).name == "external"
    assert Path(ex.SNAPSHOT_DIR).parent.name == "data"
    assert os.path.isdir(ex.SNAPSHOT_DIR)


@pytest.mark.parametrize("source", ["gbif", "pubchem", "uniprot", "ncbi_gene"])
def test_license_metadata_present_for_each_source(source):
    assert source in ex.SOURCE_LICENSES
    meta = ex.SOURCE_LICENSES[source]
    assert meta["license"] and meta["homepage"].startswith("https://")
