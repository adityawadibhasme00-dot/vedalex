"""Corpus manifest + version tracking for the IP-SAKTI knowledge base.

Computes a content-hash fingerprint over every knowledge artifact (YAML rule
packs, JSON datasets, curated text corpus, treaties metadata) so the platform
can expose a queryable corpus version and detect drift between deployments.

The manifest itself is written to backend/app/knowledge/corpus_manifest.json
by the reindex job; the public endpoint reads it read-only.
"""

import glob
import hashlib
import json
import os
import time
from typing import Any

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # app/
BACKEND_DIR = os.path.dirname(APP_DIR)                                          # backend/
RULES_DIR = os.path.join(APP_DIR, "rules")
KNOWLEDGE_DIR = os.path.join(APP_DIR, "knowledge")
KB_DIR = os.path.join(APP_DIR, "..", "..", "kb")
# The curated corpus lives in backend/data, not <repo>/data. Pointing this at the
# repo root made all 21 curated files invisible to drift detection.
DATA_DIR = os.path.join(BACKEND_DIR, "data")

MANIFEST_PATH = os.path.join(KNOWLEDGE_DIR, "corpus_manifest.json")

# Files that get a dedicated group below; they are excluded from knowledge_json so
# a single file is not hashed twice under two different keys.
DEDICATED_GROUPS = {
    "treaties_metadata": "treaties_metadata.json",
    "cites_appendices": "cites.json",
}

# backend/data also holds mutable runtime state, which must not be fingerprinted:
# the harvester ledgers (*_state.json) and the knowledge-graph TTL cache change
# on every run, so hashing them would make corpus_version churn for no reason
# and destroy the drift signal the manifest exists to provide.
DATA_EXCLUDED_NAMES = frozenset({
    "ingestion_state.json",
    "indiacode_state.json",
    "curated_corpus_state.json",
    "knowledge_graph.json",
})
DATA_EXCLUDED_DIRS = ("uploads", "exports", "__pycache__")


def _chunk_hash(path: str) -> str | None:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except Exception:
        return None


def _rel_key(path: str, root: str) -> str:
    """Manifest key for a file, always with forward slashes.

    os.path.relpath returns backslashes on Windows, so the same corpus hashed on
    two platforms produced two different corpus_version values.
    """
    return os.path.relpath(path, root).replace(os.sep, "/")


def collect_artifacts() -> dict[str, dict[str, str]]:
    artifacts: dict[str, dict[str, str]] = {
        "rule_pack_rules_yaml": {},
        "knowledge_json": {},
        "curated_text_data": {},
        "kb_documents": {},
        "treaties_metadata": {},
        "cites_appendices": {},
    }
    dedicated_names = set(DEDICATED_GROUPS.values())

    for f in sorted(glob.glob(os.path.join(RULES_DIR, "*.yaml"))):
        artifacts["rule_pack_rules_yaml"][os.path.basename(f)] = _chunk_hash(f) or ""

    for f in sorted(glob.glob(os.path.join(KNOWLEDGE_DIR, "*.json"))):
        name = os.path.basename(f)
        if name == "corpus_manifest.json" or name in dedicated_names:
            continue
        artifacts["knowledge_json"][name] = _chunk_hash(f) or ""

    # Scan every curated subdirectory rather than a hardcoded list. The list had
    # fallen behind the corpus: backend/data/multiomics alone holds 31 files and
    # was not tracked at all. Runtime state and caches are excluded.
    for f in sorted(glob.glob(os.path.join(DATA_DIR, "**", "*.*"), recursive=True)):
        if not os.path.isfile(f):
            continue
        rel = _rel_key(f, DATA_DIR)
        if os.path.basename(f) in DATA_EXCLUDED_NAMES:
            continue
        if any(part in DATA_EXCLUDED_DIRS for part in rel.split("/")):
            continue
        artifacts["curated_text_data"][rel] = _chunk_hash(f) or ""

    for f in sorted(glob.glob(os.path.join(KB_DIR, "**", "*.*"), recursive=True)):
        if os.path.isfile(f):
            artifacts["kb_documents"][_rel_key(f, KB_DIR)] = _chunk_hash(f) or ""

    for group, name in DEDICATED_GROUPS.items():
        path = os.path.join(KNOWLEDGE_DIR, name)
        if os.path.exists(path):
            artifacts[group][name] = _chunk_hash(path) or ""

    return artifacts


def compute_version(artifacts: dict[str, dict[str, str]]) -> str:
    payload = json.dumps(artifacts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_manifest() -> dict[str, Any]:
    artifacts = collect_artifacts()
    version = compute_version(artifacts)
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "corpus_version": version,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "industry_signals": "IP-SAKTI Sahayak curated corpus",
        # Derived from what was actually collected, so scope can never advertise
        # a group that artifact_counts does not have.
        "scope": list(artifacts),
        "file_hashes": artifacts,
        "artifact_counts": {k: len(v) for k, v in artifacts.items()},
    }
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    return manifest


def load_manifest() -> dict[str, Any] | None:
    if not os.path.exists(MANIFEST_PATH):
        return None
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def get_corpus_status() -> dict[str, Any]:
    """Public, read-only version snapshot for the admin/status endpoint."""
    manifest = load_manifest()
    if not manifest:
        return {
            "corpus_version": None,
            "manifest_present": False,
            "artifact_counts": {},
            "note": "Run /admin/reindex to generate the corpus manifest.",
        }
    return {
        "corpus_version": manifest.get("corpus_version"),
        "manifest_present": True,
        "generated_at": manifest.get("generated_at"),
        "artifact_counts": manifest.get("artifact_counts"),
        "schema_version": manifest.get("schema_version"),
        "scope": manifest.get("scope"),
    }