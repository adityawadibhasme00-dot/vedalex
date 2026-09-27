"""Download a bounded snapshot of official public datasets with full provenance.

Usage (from backend/):
    python -m tools.harvest_external_datasets           # refresh the snapshot
    python -m tools.harvest_external_datasets --check   # verify, no network

Writes backend/data/external/<source>/*.json plus provenance.json recording, for
every dataset: publisher, homepage, license, license URL, citation, the exact
API endpoints queried, retrieval timestamp, record count and the SHA-256 of the
written file. The snapshot is committed so the platform works offline, and the
manifest is itself covered by the corpus manifest's curated_text_data group.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.datasources import external as ex  # noqa: E402

ENDPOINTS: dict[str, list[str]] = {
    "gbif": [
        "https://api.gbif.org/v1/species/match?name={name}",
        "https://api.gbif.org/v1/species/{usageKey}",
        "https://api.gbif.org/v1/species/{usageKey}/synonyms?limit=25",
    ],
    "pubchem": [
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON",
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/"
        + ex.PUBCHEM_PROPERTIES
        + "/JSON",
    ],
    "uniprot": [
        "https://rest.uniprot.org/uniprotkb/search?query=gene_exact:{symbol}+AND+"
        "organism_id:9606+AND+reviewed:true&format=json&size=1",
    ],
    "ncbi_gene": [
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&term="
        "{symbol}[sym]+AND+human[orgn]&retmode=json",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gene&"
        "id={ids}&retmode=json",
    ],
}

HARVESTERS = {
    "gbif": lambda: ex.harvest_gbif_taxonomy(timeout=30),
    "pubchem": lambda: ex.harvest_pubchem_compounds(timeout=30),
    "uniprot": lambda: ex.harvest_uniprot_entries(timeout=30),
    "ncbi_gene": lambda: ex.harvest_ncbi_genes(timeout=30),
}

FILE_FOR_SOURCE = {
    "gbif": "taxonomy/documents.json",
    "pubchem": "compounds/documents.json",
    "uniprot": "entries/documents.json",
    "ncbi_gene": "genes/documents.json",
}


def _write_json(path: str, payload: Any) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _corpus_version() -> str:
    from app.services import corpus_manifest as cm

    return cm.compute_version(cm.collect_artifacts())


def build(check_only: bool = False) -> int:
    out_dir = ex.SNAPSHOT_DIR
    datasets: list[dict[str, Any]] = []
    exit_code = 0

    if check_only:
        manifest = ex.snapshot_manifest()
        if not manifest:
            print("no snapshot present")
            return 1
        for entry in manifest.get("datasets", []):
            path = os.path.join(out_dir, entry["file"].replace("/", os.sep))
            if not os.path.exists(path):
                print(f"MISSING  {entry['file']}")
                exit_code = 1
                continue
            with open(path, "rb") as fh:
                actual = hashlib.sha256(fh.read()).hexdigest()
            ok = actual == entry.get("sha256")
            print(f"{'OK  ' if ok else 'FAIL'}  {entry['file']}  {entry.get('records')} records")
            if not ok:
                exit_code = 1
        return exit_code

    for source, harvester in HARVESTERS.items():
        print(f"harvesting {source} ...", flush=True)
        try:
            docs = harvester()
        except Exception as exc:  # noqa: BLE001
            print(f"  {source} FAILED: {type(exc).__name__}: {exc}")
            datasets.append({
                "source": source,
                "file": FILE_FOR_SOURCE[source],
                "records": 0,
                "error": f"{type(exc).__name__}: {exc}",
                **ex.SOURCE_LICENSES[source],
            })
            exit_code = 1
            continue

        rel = FILE_FOR_SOURCE[source]
        path = os.path.join(out_dir, rel.replace("/", os.sep))
        payload = {
            "source": source,
            "publisher": ex.SOURCE_LICENSES[source]["publisher"],
            "license": ex.SOURCE_LICENSES[source]["license"],
            "endpoints": ENDPOINTS[source],
            "documents": docs,
        }
        digest = _write_json(path, payload)
        datasets.append({
            "source": source,
            "publisher": ex.SOURCE_LICENSES[source]["publisher"],
            "homepage": ex.SOURCE_LICENSES[source]["homepage"],
            "license": ex.SOURCE_LICENSES[source]["license"],
            "license_url": ex.SOURCE_LICENSES[source]["license_url"],
            "citation": ex.SOURCE_LICENSES[source]["citation"],
            "endpoints": ENDPOINTS[source],
            "file": rel,
            "records": len(docs),
            "sha256": digest,
        })
        print(f"  {source}: {len(docs)} records -> {rel}  sha256={digest[:16]}")

    retrieved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest = {
        "schema_version": "1.0",
        "retrieved_at": retrieved_at,
        "corpus_version_at_harvest": _corpus_version(),
        "description": (
            "Bounded snapshot of official, no-registration public datasets used to "
            "supply verifiable identifiers for the medicinal plants, marker compounds "
            "and protein/gene targets already cited by the curated corpus."
        ),
        "datasets": datasets,
        "unavailable_sources": ex.UNAVAILABLE_SOURCES,
    }
    _write_json(os.path.join(out_dir, "provenance.json"), manifest)
    total = sum(d.get("records", 0) for d in datasets)
    print(f"\nsnapshot written: {total} records across {len(datasets)} datasets")
    return exit_code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify the snapshot only")
    args = ap.parse_args()
    return build(check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
