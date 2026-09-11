import os
import sys
import json

os.environ["IPSAKTI_USE_BGE_M3"] = "1"
os.environ["IPSAKTI_USE_RERANKER"] = "0"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.rag.retrieval_pipeline import HybridRetriever

r = HybridRetriever.retrieve("Can an Ashwagandha wound-healing formulation be patented in India?", top_k=5)

print("GROUNDING:", json.dumps(r.get("grounding", {})))
print("CONFIDENCE:", r.get("confidence"))
print("SHOULD_REFUSE:", r.get("should_refuse"))
print("STATS:", json.dumps(r.get("retrieval_stats", {}), indent=2))
print()
for i, s in enumerate(r.get("sources", [])[:5]):
    print(f"[{i+1}] {s.get('title', '')[:50]} | {s.get('authority', '')[:30]} | method={s.get('retrieval_method', '')} | score={s.get('score', 0):.3f} | patent={s.get('patent_number', '')} | sec={s.get('section_heading', '')}")
    print("     content:", s.get("content", "")[:120].replace(chr(10), " "))
    print()