# Deep Dive 2 — Hybrid RAG

`backend/app/rag/` — `retrieval_pipeline.py`, `boolean_search.py`,
`faiss_retriever.py`, `qdrant_store.py`, `embeddings.py`, `reranker.py`,
`official_web_retriever.py`

## The problem

A single retrieval strategy fails on this corpus:

- **Dense vectors alone** blur exactly the distinction the product turns on.
  "Ashwagandha for stress" and "Ashwagandha for arthritis" land near each other;
  one is a legitimate Ayurvedic medicine claim, the other is a Schedule-D
  scheduling question. Cosine similarity does not know that.
- **Keyword alone** misses paraphrase. A patent claim and a monograph describing
  the same composition share almost no tokens.
- **Live web alone** is unauditable and rate-limited. It cannot be the spine of
  a regulatory answer.

So retrieval is layered: cheap and precise first, expensive and semantic second,
live official sources last, and **every layer can be traced**.

## The stack

```
query
  │
  ├─ 1. Boolean search      app/rag/boolean_search.py
  │      deterministic AND/OR/NOT/PHRASE + field filters
  │      → exact section hits, fully explainable
  │
  ├─ 2. Dense retrieval     faiss_retriever.py / qdrant_store.py
  │      BGE-M3, 1024-dim, multilingual
  │      → paraphrase, cross-language, related provisions
  │
  ├─ 3. Rerank              reranker.py
  │      BGE cross-encoder, scores (query, passage) jointly
  │      → precision at the top of the list
  │
  ├─ 4. Live official web   official_web_retriever.py
         domain-whitelisted, 3 fetches/query, 6h cache
         → amendments the local corpus predates
  │
  └─ merge → dedupe → RRF-style fusion → top-k with citations
```

## Layer 1 — Boolean search is a language, not a filter

`boolean_search.py` compiles a real expression grammar: `AND`, `OR`, `NOT`,
quoted `PHRASE`, parentheses, and `field:value` filters (`authority:`, `act:`,
`section:`). It is deterministic, so the same query returns the same hits and the
user can see *why* a document matched.

This matters for the trust story. When a user asks "which sections of the Drugs
and Cosmetics Act mention a licence to sell?", the answer can be
"these three, because the expression selected them" rather than "a model felt
these were relevant".

Corpus loading is generation-tracked:

```python
if _CORPUS_CACHE:
    if _CORPUS_LOADED_AT_GENERATION is None:
        # supplied by a caller, not loaded here — authoritative
        _CORPUS_LOADED_AT_GENERATION = generation
        return _CORPUS_CACHE
    if _CORPUS_LOADED_AT_GENERATION == generation:
        return _CORPUS_CACHE
# generation moved: a reindex happened, possibly in another replica
```

`invalidate_corpus_cache()` bumps a counter held in the **shared** cache with
`ttl=0`. `ttl=0` is the important part: it means *no expiry*, not *memory only*.
A replica that re-indexes bumps the counter, and every other replica notices its
recorded generation no longer matches and reloads. Without this, replica B keeps
answering from a corpus that no longer exists after a reindex on replica A.

## Layer 2/3 — Dense then rerank

Embedding is BGE-M3 by default (`IPSAKTI_USE_BGE_M3=1`): 1024-dim and
multilingual, which is what makes Hindi/Tamil/Bengali queries work against an
English corpus. There is a hashing fallback that logs a loud warning — degraded
semantic quality, never a crash.

Dense retrieval proposes; the cross-encoder disposes. A bi-encoder embeds query
and passage independently, so it cannot model their interaction. The BGE
reranker scores the pair jointly, which is why it goes after retrieval rather
than replacing it. Reranking everything is quadratic and pointless; reranking the
top-50 is where the precision actually comes from.

Both are now **sidecar-aware**. `IPSAKTI_MODEL_SERVER_URL` points at a separate
service hosting BGE-M3 + the cross-encoder. If the sidecar is healthy, the web
tier never loads ~4GB of model weights and stays cheap to autoscale; if it is
not, embedding and reranking fall back to in-process. Two consequences:

- `backend` scales for **request count**, `modelserver` scales for **throughput**.
- Each replica stops paying to hold identical model state.

If the reranker cannot be reached at request time it **passes through** rather
than silently swapping in a weaker model — a degraded ranking is visible, a
quietly-different ranking is not.

## Layer 4 — Live official web, and its blast radius

`official_web_retriever.py` fetches from government domains only, under a hard
budget: 3 fetches per query, 6h cache, disabled entirely by
`IPSAKTI_LIVE_WEB=0`.

Domain validation matters more here than anywhere else in the system, because
this is the only component that makes network requests on a user-supplied path.
It must reject lookalike suffixes (`evil-india-code.nic.in.attacker.com`),
userinfo tricks (`https://india-code.nic.in@attacker.com`), non-HTTP schemes, and
internal addresses (`169.254.169.254`, `localhost`). There are open XFAILs
recording that `_fetch_url` still performs no URL validation of its own and does
not re-validate redirect targets — the whitelist is checked, the raw fetcher is
not. **That is the sharpest remaining SSRF edge in the codebase** and is
tracked as such rather than hidden.

The page cache moved from a module dict to the shared `SharedCache`. A per-process
dict meant every replica re-fetched the same government pages and separately got
rate-limited; now the fetches are shared, survive restarts, and are visible via
`stats()`. Both backends return the same shape, so behaviour does not depend on
whether Redis happens to be up.

## Fusion and why RRF

Boolean and dense results are merged with reciprocal-rank fusion rather than
score normalisation. RRF only needs each list's *rank*, so a lexical score of
`1.0` and a cosine of `0.83` do not have to be made commensurable — which they
cannot honestly be, since they measure different things. Rank-based fusion is the
standard answer precisely because the scores are incommensurable.

## Architecture selector

`IPSAKTI_RAG_DEFAULT` picks the composition for `POST /rag/search`:

| Value | Composition |
| --- | --- |
| `hybrid` (default) | boolean + dense + rerank |
| `production` | + official web + result cache + rate limit |
| `graph` | + local knowledge graph, optional Neo4j |
| `agentic` | multi-step, tool-using, verified |

`production` adds a Redis result cache (`IPSAKTI_RAG_CACHE_TTL`) and a per-user
rate limit (`IPSAKTI_RAG_RATE_LIMIT`).

## Cost discipline

The expensive things are bounded on purpose:

- reranking applies to the top-50 only
- live web is capped at 3 fetches per query and off by default for tests
- official-page cache is 6h
- entailment vectors are cached in the shared cache, so a re-verified claim does
  not re-embed its passages

## Known limits

- Hybrid fusion weights are tuned, not learned; there is no offline eval harness
  in-repo that would justify changing them.
- Live-web results are not citation-grade on their own — a government page is
  evidence that the text exists, not proof of interpretation.
- The reranker passthrough means latency spikes are possible when the sidecar
  is unhealthy rather than silent quality loss.
- Qdrant payload indexes are no-ops in local mode (warned at startup).
