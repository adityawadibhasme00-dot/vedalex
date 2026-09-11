"""
Production RAG ingestion pipeline for IP-SAKTI / IP-SAKTI.

Pulls every source into the searchable index:
  1. backend/data/**          - curated official corpus (txt/md/json/pdf/docx)
  2. kb/**                    - external knowledge base layout (tkdl/wipo/regulations/...)
  3. app/knowledge/*.json     - canonical statutory/taxonomy seeds
  4. blueprint.xlsx (optional)- 13-sheet RAG metadata workbook (Source Inventory,
                                Evidence Passages, Rules, Source Versions, ...)

Embeddings: BAAI/bge-base-en-v1.5 (set IPSAKTI_USE_SENTENCE_TRANSFORMERS=1). Falls
back to deterministic hashing embeddings so the pipeline always completes.

Usage:
    python scripts/ingest_official.py                    # hash-fallback (fast)
    IPSAKTI_USE_SENTENCE_TRANSFORMERS=1 python scripts/ingest_official.py   # BGE
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rag.kb import collect_knowledge_documents, blueprint_path, official_dir  # noqa: E402


def main():
    from app.rag.faiss_retriever import FAISSIndex
    from app.services.retrieval_engine import HybridRetrievalEngine
    from app.services.ai_copilot import AICopilot

    docs = collect_knowledge_documents()
    print(f"\nTotal chunks to index: {len(docs)}")

    by_cat = Counter(d.get("category", "unknown") for d in docs)
    print("Chunks by category:")
    for cat, count in by_cat.most_common():
        print(f"  {cat:<22} {count}")

    blueprint = blueprint_path()
    print(f"Blueprint workbook:    {'FOUND at ' + blueprint if blueprint else 'not present (optional)'}")
    print(f"Official corpus dir:   {official_dir()}")

    # Statutory passage registry pre-warm (used by the zero-hallucination gate).
    HybridRetrievalEngine.load_database()
    print(f"Statutory passages DB: {len(HybridRetrievalEngine._passages_db)}")

    index = FAISSIndex()
    index.build(docs)
    AICopilot.reset_index()

    emb = "sentence-transformers (BAAI/bge-base-en-v1.5)" if index.model is not None else "hashing-fallback"
    print(f"Embeddings: {emb}")
    print("FAISS index built successfully!\n")


if __name__ == "__main__":
    main()