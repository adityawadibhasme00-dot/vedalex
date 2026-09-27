"""
IP-SAKTI automated corpus ingestion.

Mapping from the master build prompt to this package:
  backend/ingestion/sources.py        -> corpus registry + priority table
  backend/ingestion/fetchers.py       -> guarded HTML/PDF/local fetchers
  backend/ingestion/normalizer.py     -> cleanup + dedup
  backend/ingestion/metadata.py       -> provenance metadata contract
  backend/ingestion/chunker.py        -> semantic, provision-preserving chunker
  backend/ingestion/pipeline.py       -> orchestrator (embed -> Qdrant upsert)

Run from backend/:  python -m app.ingestion --sources p0 --mode update
"""