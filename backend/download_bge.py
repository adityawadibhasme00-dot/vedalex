import os
os.environ["IPSAKTI_USE_BGE_M3"] = "1"

from sentence_transformers import SentenceTransformer

print("Downloading/loading BAAI/bge-m3 ...", flush=True)
model = SentenceTransformer("BAAI/bge-m3")
print(f"Model loaded: dim={model.get_sentence_embedding_dimension()}", flush=True)

emb = model.encode(["Test embedding for cache warm-up"], normalize_embeddings=True)
print(f"Cache warm-up done. shape={emb.shape}", flush=True)
print("COMPLETE", flush=True)