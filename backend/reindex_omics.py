import os
import sys
import time

os.environ["IPSAKTI_USE_BGE_M3"] = "1"
os.environ["IPSAKTI_USE_RERANKER"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app.rag.qdrant_store as qs

qs.QdrantVectorStore._instance = None

from app.rag.retrieval_pipeline import HybridRetriever
from app.rag.kb import collect_knowledge_documents
from app.rag.embeddings import EmbeddingEngine

engine = EmbeddingEngine()
print("Embedding provider:", engine.get_provider(), "| dim:", engine.get_dim(), flush=True)

docs = collect_knowledge_documents()
categories = {}
for d in docs:
    categories[d.get("category", "?")] = categories.get(d.get("category", "?"), 0) + 1
print("Total docs:", len(docs), flush=True)
print("Categories:", categories, flush=True)

start = time.time()
result = HybridRetriever.reindex_all()
print(f"REINDEX DONE in {time.time()-start:.1f}s", flush=True)
print("Result:", result, flush=True)

stats = qs.QdrantVectorStore().get_collection_stats()
print("Final collection stats:", stats, flush=True)
print("COMPLETE", flush=True)