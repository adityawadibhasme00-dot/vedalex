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
RULES_DIR = os.path.join(APP_DIR, "rules")
KNOWLEDGE_DIR = os.path.join(APP_DIR, "knowledge")
KB_DIR = os.path.join(APP_DIR, "..", "..", "kb")
DATA_DIR = os.path.join(APP_DIR, "..", "..", "data")

MANIFEST_PATH = os.path.join(KNOWLEDGE_DIR, "corpus_manifest.json")

MANIFEST_SCOPE = (
    "rule_pack_rules_yaml",
    "knowledge_json",
    "curated_text_data",
    "kb_documents",
    "treaties_metadata",
    "legal_glossary",
    "cites_appendices",
)


def _chunk_hash(path: str) -> str | None:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except Exception:
        return None


def _group_hashes(files: list[str], root: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for f in sorted(files):
        rel = os.path.relpath(f, root)
        h = _chunk_hash(f)
        if h:
            result[rel] = h
    return result


def collect_artifacts() -> dict[str, dict[str, str]]:
    artifacts: dict[str, dict[str, str]] = {
        "rule_pack_rules_yaml": {},
        "knowledge_json": {},
        "curated_text_data": {},
        "kb_documents": {},
        "treaties_metadata": {},
        "cites_appendices": {},
    }

    for f in sorted(glob.glob(os.path.join(RULES_DIR, "*.yaml"))):
        artifacts["rule_pack_rules_yaml"][os.path.basename(f)] = _chunk_hash(f) or ""

    for f in sorted(glob.glob(os.path.join(KNOWLEDGE_DIR, "*.json"))):
        if os.path.basename(f) == "corpus_manifest.json":
            continue
        artifacts["knowledge_json"][os.path.basename(f)] = _chunk_hash(f) or ""

    for sub in ("patents", "regulations", "pharmacopoeia", "official", "who",
                "ayurveda", "pubmed"):
        for f in sorted(glob.glob(os.path.join(DATA_DIR, sub, "*"))):
            if os.path.isfile(f):
                artifacts["curated_text_data"][os.path.relpath(f, DATA_DIR)] = _chunk_hash(f) or ""

    for f in sorted(glob.glob(os.path.join(KB_DIR, "**", "*.*"), recursive=True)):
        if os.path.isfile(f):
            artifacts["kb_documents"][os.path.relpath(f, KB_DIR)] = _chunk_hash(f) or ""

    treaties_path = os.path.join(KNOWLEDGE_DIR, "treaties_metadata.json")
    if os.path.exists(treaties_path):
        artifacts["treaties_metadata"][os.path.basename(treaties_path)] = _chunk_hash(treaties_path) or ""

    cites_path = os.path.join(KNOWLEDGE_DIR, "cites.json")
    if os.path.exists(cites_path):
        artifacts["cites_appendices"][os.path.basename(cites_path)] = _chunk_hash(cites_path) or ""

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
        "scope": MANIFEST_SCOPE,
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