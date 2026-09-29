"""
Multi-omics data source harvesters for VEDALEX RAG.

Every returned document uses the standard KB document schema and carries
real, traceable identifiers (UniProt accession, NCBI Gene ID, PubChem CID,
PMID) so the zero-hallucination guard can cite them deterministically.

Data sources (all official / public-domain):
  - NCBI Gene / PubMed (E-utilities)   genomics, transcriptomics
  - UniProt REST                        proteomics
  - PharmGKB                            pharmacogenomics
  - HMDB / PubChem (NCBI)              metabolomics
  - WikiPathways / KEGG                pathway

Harvesters are additive: they return curated seed records first (always
available offline), then replay a committed snapshot of the official external
sources, then opportunistically fetch live updates from the official APIs when
network access is available. API calls are guarded, rate-limited and never block
knowledge base loading.
"""

from typing import Any

from .external import (
    UNAVAILABLE_SOURCES,
    external_status,
    load_external_snapshot,
)
from .seed.curated import build_omics_seed_documents

__all__ = [
    "harvest_multiomics",
    "build_omics_seed_documents",
    "load_external_snapshot",
    "external_status",
    "UNAVAILABLE_SOURCES",
]


def harvest_multiomics(
    include_live: bool = False,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """Return all multi-omics documents (curated seed + snapshot + optional live)."""
    docs: list[dict[str, Any]] = build_omics_seed_documents()
    docs.extend(load_external_snapshot())

    if include_live:
        from . import external

        for _harvester in (
            external.harvest_gbif_taxonomy,
            external.harvest_pubchem_compounds,
            external.harvest_uniprot_entries,
            external.harvest_ncbi_genes,
        ):
            try:
                docs.extend(_harvester(timeout=timeout))
            except Exception:
                pass

    return docs


# ---------------------------------------------------------------------------
# Live API harvesters (optional). Each returns [] on any failure so that the
# knowledge base is never blocked by network issues / rate limits. The
# implementations live in app/rag/datasources/external.py and are the four
# official sources that are reachable without registration. Sources that are
# genuinely unavailable are listed in external.UNAVAILABLE_SOURCES.
# ---------------------------------------------------------------------------
