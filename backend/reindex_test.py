import os
import sys

os.environ["IPSAKTI_USE_BGE_M3"] = "0"
os.environ["IPSAKTI_USE_RERANKER"] = "0"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import time
from app.rag.retrieval_pipeline import HybridRetriever

start = time.time()
stats = HybridRetriever.reindex_all()
elapsed = time.time() - start

print("Reindex complete in %.2fs" % elapsed)
print("Total docs:", stats.get("total_documents"))
print("Upserted:", stats.get("upserted_to_qdrant"))
print("BM25 index size:", stats.get("bm25_index_size"))