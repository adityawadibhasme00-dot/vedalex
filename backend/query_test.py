import os
import sys

os.environ["IPSAKTI_USE_BGE_M3"] = "0"
os.environ["IPSAKTI_USE_RERANKER"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
from app.rag.retrieval_pipeline import HybridRetriever

query = "Can an Ashwagandha wound-healing formulation be patented in India?"

start = time.time()
result = HybridRetriever.retrieve(query, top_k=5)
elapsed = time.time() - start

print("=" * 70)
print("QUERY:", query)
print("TIME: %.2fs" % elapsed)
print("=" * 70)
print("GROUNDING:", json.dumps(result.get("grounding", {}), indent=2)[:600])
print("CONFIDENCE:", result.get("confidence"))
print("SHOULD_REFUSE:", result.get("should_refuse"))
print("RETRIEVAL_STATS:", json.dumps(result.get("retrieval_stats", {}), indent=2))
print()
print("TOP SOURCES:")
for i, s in enumerate(result.get("sources", [])[:5]):
    print(f"  [{i+1}] {s.get('title', 'N/A')} | {s.get('authority', '')} | method={s.get('retrieval_method', '')} | score={s.get('score', 0):.3f}")
    print(f"       Section: {s.get('section_heading', '')} | Patent: {s.get('patent_number', '')} | Year: {s.get('publication_year', '')}")
    print(f"       Content: {s.get('content', '')[:150]}...")
    print()