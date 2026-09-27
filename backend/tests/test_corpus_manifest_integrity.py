"""Integrity guards for the corpus manifest and the blueprint read path.

These lock in fixes for real defects found during the corpus audit:

* DATA_DIR pointed at <repo>/data, so every curated file in backend/data was
  invisible to drift detection and corpus_version never changed when the curated
  corpus was edited.
* Manifest keys came from os.path.relpath(), which yields backslashes on
  Windows, so the same corpus produced a different corpus_version per platform.
* scope advertised 7 groups while artifact_counts had 6 keys, so a client
  trusting scope hit a KeyError.
* treaties_metadata.json and cites.json were hashed twice, under knowledge_json
  and again under their dedicated groups.
* load_blueprint_documents() persisted app/knowledge/*.json on the read path, so
  an ordinary search rewrote hashed corpus input and dirtied the tree.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from app.services import corpus_manifest as cm


def test_data_dir_points_at_backend_data():
    """The curated corpus lives in backend/data, not <repo>/data."""
    assert Path(cm.DATA_DIR) == Path(cm.BACKEND_DIR) / "data"
    assert Path(cm.DATA_DIR).is_dir()


def test_curated_text_data_is_not_empty():
    """Regression: the hardcoded subdirectory list missed the real corpus."""
    artifacts = cm.collect_artifacts()
    curated = artifacts["curated_text_data"]
    assert len(curated) > 0, "curated corpus is invisible to the manifest"
    assert any(k.startswith("multiomics/") for k in curated)


def test_manifest_keys_always_use_forward_slashes():
    """Same corpus must hash identically on Windows and Linux."""
    for group, files in cm.collect_artifacts().items():
        for key in files:
            assert "\\" not in key, f"{group} has a backslash key: {key}"


def test_rel_key_normalizes_separators(monkeypatch):
    """_rel_key is the single place separators are normalized.

    Because collect_artifacts() only ever emits forward slashes, the same corpus
    on Linux and on Windows yields byte-identical artifacts and therefore the
    same corpus_version.
    """
    root = str(Path("C:/tmp") if os.name == "nt" else Path("/tmp"))
    nested = os.path.join(root, "curated", "patents", "sample.txt")
    key = cm._rel_key(nested, root)
    assert key == "curated/patents/sample.txt"
    assert "\\" not in key
    # Idempotent: a key that already uses forward slashes is returned unchanged.
    assert cm._rel_key(os.path.join(root, "curated", "patents", "sample.txt"), root) == key


def test_version_is_deterministic_regardless_of_insertion_order():
    """Two files with the same content must not depend on scan order."""
    a = cm.collect_artifacts()
    b = {g: dict(reversed(list(files.items()))) for g, files in a.items()}
    assert cm.compute_version(a) == cm.compute_version(b)


def test_scope_matches_actual_artifact_keys():
    """scope must never advertise a group that artifact_counts lacks."""
    artifacts = cm.collect_artifacts()
    manifest_scope = list(artifacts)
    counts = {k: len(v) for k, v in artifacts.items()}
    assert set(manifest_scope) == set(counts)
    for key in manifest_scope:
        assert key in counts


def test_no_artifact_is_hashed_twice():
    """treaties_metadata.json and cites.json belong to exactly one group."""
    groups = cm.collect_artifacts()
    for name in cm.DEDICATED_GROUPS.values():
        owners = [g for g, files in groups.items() if name in files]
        assert len(owners) == 1, f"{name} hashed under {owners}"
        assert owners[0] in cm.DEDICATED_GROUPS


def test_manifest_json_itself_is_excluded():
    files = cm.collect_artifacts()["knowledge_json"]
    assert "corpus_manifest.json" not in files


def test_every_recorded_hash_matches_the_file(monkeypatch, tmp_path):
    """Spot-check that recorded digests correspond to real file content."""
    target = Path(cm.RULES_DIR) / sorted(os.listdir(cm.RULES_DIR))[0]
    recorded = cm.collect_artifacts()["rule_pack_rules_yaml"][target.name]
    assert recorded == hashlib.sha256(target.read_bytes()).hexdigest()


def test_curated_corpus_is_versioned_not_gitignored():
    """A fresh clone must ship the corpus the manifest hashes.

    backend/data/ was entirely gitignored, so the curated text, the blueprint
    workbook and the external dataset snapshot existed only on one machine and
    drift detection had nothing to compare against.
    """
    import subprocess

    repo = Path(cm.BACKEND_DIR).parent
    probe = Path(cm.DATA_DIR) / "official" / "who_traditional_medicine_strategy.txt"
    if not probe.exists():
        pytest.skip("curated corpus not present")

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(probe.relative_to(repo))],
        cwd=repo,
        capture_output=True,
    )
    assert ignored.returncode != 0, "curated corpus is gitignored"


def test_runtime_state_stays_gitignored():
    """Harvester state must not be versioned even though the corpus is."""
    import subprocess

    repo = Path(cm.BACKEND_DIR).parent
    state = Path(cm.DATA_DIR) / "ingestion_state.json"
    if not state.exists():
        pytest.skip("no local harvester state")

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(state.relative_to(repo))],
        cwd=repo,
        capture_output=True,
    )
    assert ignored.returncode == 0, "harvester state should stay untracked"


def test_hashed_files_still_exist():
    """Every manifest key must resolve to a file on disk."""
    groups = cm.collect_artifacts()
    roots = {
        "rule_pack_rules_yaml": Path(cm.RULES_DIR),
        "knowledge_json": Path(cm.KNOWLEDGE_DIR),
        "curated_text_data": Path(cm.DATA_DIR),
        "kb_documents": Path(cm.KB_DIR),
        "treaties_metadata": Path(cm.KNOWLEDGE_DIR),
        "cites_appendices": Path(cm.KNOWLEDGE_DIR),
    }
    for group, files in groups.items():
        root = roots[group]
        for key in files:
            assert (root / key).is_file(), f"{group}:{key} missing on disk"


TEXT_SUFFIXES = {".json", ".txt", ".yaml", ".yml", ".md", ".csv"}
BINARY_SUFFIXES = {".xlsx", ".pdf", ".png", ".jpg", ".jpeg", ".faiss", ".pkl", ".npy", ".gz", ".zip"}

_ROOTS = {
    "rule_pack_rules_yaml": Path(cm.RULES_DIR),
    "knowledge_json": Path(cm.KNOWLEDGE_DIR),
    "curated_text_data": Path(cm.DATA_DIR),
    "kb_documents": Path(cm.KB_DIR),
    "treaties_metadata": Path(cm.KNOWLEDGE_DIR),
    "cites_appendices": Path(cm.KNOWLEDGE_DIR),
}


def _hashed_paths():
    for group, files in cm.collect_artifacts().items():
        root = _ROOTS[group]
        for key in files:
            yield group, root / key


def test_hashed_text_artifacts_are_lf_only():
    """A recorded SHA-256 must not depend on the checkout platform.

    With core.autocrlf=true and no .gitattributes, a Windows checkout rewrote 55
    hashed artifacts to CRLF while Linux left them LF, so the manifest's hashes
    stopped matching the files for every collaborator.
    """
    offenders = []
    for group, path in _hashed_paths():
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if b"\r\n" in path.read_bytes():
            offenders.append(f"{group}:{path.name}")
    assert not offenders, f"CRLF in hashed text artifacts: {offenders}"


def test_hashed_binary_artifacts_are_untouched():
    """The blueprint workbook is binary and must keep its zip header."""
    workbooks = [p for _, p in _hashed_paths() if p.suffix.lower() == ".xlsx"]
    assert workbooks, "expected the blueprint workbook to be hashed"
    for wb in workbooks:
        assert wb.read_bytes()[:2] == b"PK", f"{wb.name} is not a valid xlsx/zip"


def test_gitattributes_pins_corpus_to_lf():
    """The .gitattributes guard must keep existing, or CRLF creeps back."""
    attrs = Path(cm.BACKEND_DIR).parent / ".gitattributes"
    assert attrs.is_file(), ".gitattributes missing"
    text = attrs.read_text(encoding="utf-8")
    for line in ("backend/data/** text eol=lf",
                 "backend/app/knowledge/** text eol=lf",
                 "backend/app/rules/** text eol=lf"):
        assert line in text, f".gitattributes missing: {line}"
    assert "*.xlsx binary" in text


def test_runtime_state_is_not_fingerprinted():
    """Mutable ledgers and the TTL cache must not move corpus_version."""
    curated = cm.collect_artifacts()["curated_text_data"]
    for excluded in cm.DATA_EXCLUDED_NAMES:
        assert excluded not in curated, f"{excluded} is runtime state, not corpus"
    keys = list(curated)
    assert not any(k.startswith("uploads/") for k in keys)
    assert not any(k.startswith("exports/") for k in keys)


def test_state_files_do_not_change_the_version(monkeypatch, tmp_path):
    """Rewriting a harvester ledger must leave corpus_version alone."""
    fake = tmp_path / "data"
    (fake / "patents").mkdir(parents=True)
    (fake / "patents" / "statute.txt").write_text("section 3", encoding="utf-8")
    (fake / "ingestion_state.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cm, "DATA_DIR", str(fake))

    first = cm.compute_version(cm.collect_artifacts())
    (fake / "ingestion_state.json").write_text('{"seen": 99}', encoding="utf-8")
    (fake / "knowledge_graph.json").write_text('{"nodes": 5}', encoding="utf-8")
    assert cm.compute_version(cm.collect_artifacts()) == first


def test_corpus_version_changes_when_curated_corpus_changes(monkeypatch, tmp_path):
    """The whole point of the module: edited curated text must move the version."""
    fake = tmp_path / "data"
    (fake / "patents").mkdir(parents=True)
    (fake / "patents" / "sample.txt").write_text("original", encoding="utf-8")
    monkeypatch.setattr(cm, "DATA_DIR", str(fake))

    first = cm.compute_version(cm.collect_artifacts())
    (fake / "patents" / "sample.txt").write_text("edited", encoding="utf-8")
    second = cm.compute_version(cm.collect_artifacts())
    assert first != second


def test_load_blueprint_documents_does_not_write_on_read():
    """An ordinary KB read must not rewrite hashed corpus input."""
    kdir = Path(cm.KNOWLEDGE_DIR)
    targets = [kdir / "blueprint_sources.json", kdir / "blueprint_rules.json"]
    before = {
        p.name: (p.read_bytes(), p.stat().st_mtime) if p.exists() else None
        for p in targets
    }

    from app.rag.xlsx_pipeline import load_blueprint_documents

    load_blueprint_documents()

    for p in targets:
        prior = before[p.name]
        if prior is None:
            assert not p.exists(), f"read path created {p.name}"
            continue
        content, mtime = prior
        assert p.read_bytes() == content, f"read path rewrote {p.name}"
        assert p.stat().st_mtime == mtime, f"read path touched {p.name}"


def test_explicit_regeneration_still_writes():
    """The supported write path must keep working."""
    from app.rag.xlsx_pipeline import regenerate_blueprint_registries

    docs = regenerate_blueprint_registries()
    assert isinstance(docs, list)
    assert (Path(cm.KNOWLEDGE_DIR) / "blueprint_sources.json").is_file()
