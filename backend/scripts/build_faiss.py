import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rag.kb import collect_knowledge_documents  # noqa: E402


def main():
    from app.rag.faiss_retriever import FAISSIndex

    all_documents = collect_knowledge_documents()
    if not all_documents:
        all_documents = [
            {
                "content": "Ayurvedic Pharmacopoeia of India - Standard references for herbal drug quality control and standardization.",
                "source": "bootstrap",
                "category": "pharmacopoeia",
                "chunk_index": 0,
            },
            {
                "content": "Section 3(p) of Indian Patents Act 1970 - Traditional knowledge or aggregation of known properties is not patentable.",
                "source": "bootstrap",
                "category": "regulations",
                "chunk_index": 0,
            },
            {
                "content": "Charaka Samhita - foundational Ayurvedic text covering Kayachikitsa (internal medicine).",
                "source": "bootstrap",
                "category": "ayurveda",
                "chunk_index": 0,
            },
        ]

    from collections import Counter
    by_cat = Counter(d.get("category", "unknown") for d in all_documents)
    print(f"\nTotal documents to index: {len(all_documents)}")
    for cat, count in by_cat.most_common():
        print(f"  {cat:<22} {count}")

    from app.services.retrieval_engine import HybridRetrievalEngine
    HybridRetrievalEngine.load_database()
    print(f"Statutory passages DB: {len(HybridRetrievalEngine._passages_db)}")

    index = FAISSIndex()
    index.build(all_documents)
    print("FAISS index built successfully!")


if __name__ == "__main__":
    main()