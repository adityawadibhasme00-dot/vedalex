import os
import shutil
import sys
import time

os.environ["IPSAKTI_USE_BGE_M3"] = "1"
os.environ["IPSAKTI_USE_RERANKER"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "rag", "qdrant_local_data")

print("Wiping local Qdrant data dir...", flush=True)
if os.path.isdir(DATA_DIR):
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    print("Wiped:", DATA_DIR, flush=True)

import app.rag.qdrant_store as qs

qs.QdrantVectorStore._instance = None
qs.QdrantVectorStore._client = None
qs.QdrantVectorStore._collection_ready = False

print("Instantiating fresh Qdrant store...", flush=True)
store = qs.QdrantVectorStore()

stats = store.get_collection_stats()
print("Fresh collection stats:", stats, flush=True)

print("Running full reindex with BGE-M3...", flush=True)
from app.rag.retrieval_pipeline import HybridRetriever
from app.rag.embeddings import EmbeddingEngine

engine = EmbeddingEngine()
print("Embedding provider:", engine.get_provider(), "| dim:", engine.get_dim(), flush=True)

start = time.time()
result = HybridRetriever.reindex_all()
print(f"REINDEX DONE in {time.time()-start:.1f}s", flush=True)
print("Result:", result, flush=True)

stats = store.get_collection_stats()
print("Final collection stats:", stats, flush=True)
print("COMPLETE", flush=True)