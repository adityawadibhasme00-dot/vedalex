# Scaling: S1–S5

What was changed to make IP-SAKTI runnable as more than one replica, and why
each piece exists. Every item below was verified — see *Verification* at the
bottom.

The single rule that shaped all of it: **anything that must be true of the whole
deployment cannot live in one process's heap.** Module-level dicts, per-replica
schedulers, in-process model weights and inline multi-minute work are all the
same bug in different clothes.

---

## S0 — Get blocking work off the event loop *(shipped, `f711c20`)*

79 pure-sync FastAPI handlers were declared `async def`, so Starlette ran them on
the event loop. A single slow retrieval blocked *every* concurrent request, not
just its own.

- `app/core/async_bridge.py` — `run_sync`, `run_sync_timed`
- `scripts/demote_sync_routes.py` — AST-verified codemod
- Multi-step RAG / copilot orchestration wrapped in `run_sync`

AST-based, not regex: the demoter parses each handler and only touches
`def`/`async def` for functions that are genuinely synchronous, so a signature or
decorator is never mangled.

---

## S1 — Shared state

### Database pool
`app/core/database.py` now uses an explicit `QueuePool` with
`IPSAKTI_DB_POOL_SIZE` / `_MAX_OVERFLOW` / `_POOL_TIMEOUT` / `_POOL_RECYCLE`.
SQLite keeps `NullPool` (pooling a file-backed SQLite connection across threads
is a correctness problem, not a performance one).

Size the pool to `replicas × pool_size`; Postgres `max_connections` is the
ceiling you will hit first otherwise.

### Shared cache
`app/core/cache.py` — one interface, two backends: Redis when `REDIS_URL` is
reachable, bounded in-process LRU otherwise. Every operation degrades to memory
on Redis error, so an outage costs hit rate, never availability.

Wired into the three hot dicts that were per-process:
- `rag/official_web_retriever.py` — fetched page text, 6h TTL
- `rag/boolean_search.py` — corpus generation counter, `ttl=0`
- `rag/semantic_entailment.py` — evidence embedding vectors

Three bugs this work surfaced, all of which fail *only* when Redis is present:

1. **`ttl=0` never wrote to Redis.** The guard was `if client and ttl > 0`, so
   "no expiry" was silently "memory only". The boolean corpus-generation counter
   is the thing that tells a replica another replica re-indexed — it was
   invisible. Now `ttl=0` uses `SET` without expiry.
2. **`json.dumps(..., default=str)` corrupted vectors.** A NumPy array
   round-tripped from Redis came back as its *repr string*, and every downstream
   `float()` raised. Dev with no Redis passed; the first Redis read in production
   failed. `_jsonable()` now converts arrays/tensors to lists.
3. **Backends disagreed on shape.** Memory returned an `ndarray`, Redis returned
   a list — so behaviour depended on whether Redis happened to be up. `set()`
   normalises once and both backends return the same thing.

`invalidate_prefix()` was added for families of derived entries (a whole
corpus generation's query results).

---

## S2 — Single-writer lease

`app/core/lock.py` — Redis `SET NX PX`, with a file-lock fallback for
single-replica local dev.

Applied to ingestion and the law sentinel. N replicas polling the same
government pages is how a deployment gets blocked from noticing an amendment —
rate limits, IP bans, and duplicated writes. Now exactly one replica works per
cycle.

The TTL is load-bearing: a crashed holder is released automatically, so a dead
replica cannot wedge ingestion permanently. The lock is **not** reentrant and
has no heartbeat — long enough work must run under one acquire/renew cycle, and
`get_scheduler_status()` reports the TTL so the mismatch is visible.

---

## S3 — Model sidecar

`app/serving/model_server.py` — `/health`, `/embed`, `/rerank`.
`rag/embeddings.py` and `rag/reranker.py` probe `IPSAKTI_MODEL_SERVER_URL` and
fall back to in-process loading.

BGE-M3 + the BGE cross-encoder are ~4GB. In-process, every replica pays for
identical model state and cannot be cheaply autoscalled. As a sidecar:

- scale `backend` for **request count**, `modelserver` for **throughput**
- `model_cache` volume holds weights across restarts
- an unhealthy sidecar means the web tier loads locally rather than failing

The reranker **passes through** when the sidecar is unreachable at request time
rather than silently substituting a weaker model: a degraded ranking is visible,
a quietly-different ranking is not.

---

## S4 — Background job queue

`app/core/jobs.py` — submit → id → poll. Redis-backed with an in-process
fallback, so the offline demo and tests work with no Redis. No arq/celery
dependency, but the same submit/poll shape.

Handlers in `app/core/job_handlers.py`:

| Job | Does |
| --- | --- |
| `corpus_reindex` | rebuild the retrieval index |
| `indiacode_harvest` | fetch + embed + upsert India Code sections |
| `patent_corpus_harvest` | fetch + embed + upsert curated documents |
| `law_sentinel_run` | poll sources, flag content-hash changes |
| `ingestion_cycle` | one ingestion cycle now |
| `dossier_export` | dossier / markdown / PDF off the request path |

Exposed at `POST/GET /api/v1/jobs` (`jobs_router.py`).

**The race that had to be fixed.** `submit` both pushed to Redis *and* started a
local thread. The dedicated worker then popped the same id and ran it again — two
full reindex passes writing one index. `execute()` now claims atomically via
`SET NX EX`; the loser skips. `IPSAKTI_INLINE_JOBS=0` makes the queue the single
execution path in compose, but the claim makes overlap safe regardless, so it is
an efficiency knob, not a correctness one.

A lease TTL reclaims a job whose worker died mid-run.

**Access control.** Submit is **admin-only**, reads require a user. These
handlers re-fetch government sources, rewrite the index and burn embedding
budget — an unauthenticated `POST /jobs` is a DoS lever, not a convenience.
Verified: anonymous → 401, `researcher` → 403, `admin` → 202.

A second worker bug: `python -m app.core.jobs` created a *second* module object,
so the worker held an empty handler registry and every job would have failed
with "handler not registered in this process". It now imports the canonical
`app.core.jobs` and drives that instance.

---

## S5 — Module decomposition

`agent_executors.py` was 8,559 lines. The shared grounding primitives
(corpus loading, ingredient resolution, retrieval, evidence shaping) are now
`app/services/innolab/_shared.py` (30 names, `__all__` explicit).

The boundary was chosen by AST analysis, not by eye: the prefix was proven to be
**closed** — it references nothing defined below the cut — before extracting.
All 39 registered agent slugs still execute, and
`tests/test_innolab_split.py` pins the public surface (`execute_agent`,
`EXECUTORS`, `input_schema`, `sample_query`, `extract_features`,
`_hub_execution`, `_workflow_trace`) plus the shared names, so a future
refactor cannot silently move a helper or drop a slug.

**Not done:** the `_hub_*` agents (lines 1108–8559) are still in one file. They
interlock heavily — `_hub_fto` and `_hub_design_fto` share
`_fto_activity_matrix`, `_hub_novelty` and `_hub_tdoc_novelty` share ref
classifiers — so splitting them means untangling dependencies, not moving lines.
That is a separate change with its own verification pass, not something to slip
into a scaling PR.

---

## Deployment shape

```
docker compose up
  postgres  qdrant  redis
  modelserver        ← BGE-M3 + reranker, scale for throughput
  backend            ← API, scale for requests, modelserver optional
  jobworker          ← python -m app.core.jobs
  ingestionworker    ← python -m app.services.ingestion_scheduler
  frontend
```

Replicas are now interchangeable: state is in Postgres, Redis and Qdrant;
coordination is via lock and queue claims; model weights are in a sidecar.
Adding a second `backend` needs no code change.

---

## Verification

| Check | Result |
| --- | --- |
| `pytest tests` | **2195 passed, 1 skipped, 165 xfailed** |
| `compileall app` | clean |
| All 39 agent slugs | 39/39 execute |
| `npm run typecheck` | clean |
| `npm run lint` | 0 errors, 3 pre-existing warnings |
| `docker compose config` | 8 services, valid |
| Live: `/health`, `/rag/ask`, `/rag/boolean-search`, `/admin/status` | 200 |
| Live: `/jobs*` anonymous | 401 |
| Live: `/jobs` POST as `researcher` | 403 |
| Live: `law_sentinel_run` end-to-end | `done` — watched `india_code, ip_india, nba, wipo` |

New tests: `tests/test_scaling_primitives.py` (22 — cache semantics incl. the
two real bugs, lock exclusivity/TTL across threads, exactly-once job claiming,
anonymous rejection), `tests/test_innolab_split.py` (11 — split surface + every
slug).

---

## Follow-ups not in this change

- **`_fetch_url` performs no URL validation** and does not re-validate redirect
  targets. The domain whitelist is checked, the raw fetcher is not — the
  sharpest remaining SSRF edge. Open XFAILs document it.
- Path traversal in upload filename validation; HTML served unsanitised from a
  `.txt`.
- Several routers serve passport data without authentication or ownership
  checks (`screening`, `what_if`, `whitespace`).
- The `_hub_*` split (see S5).
- `agent_executors.py` has three open XFAIL defects: unknown slugs report
  `agent_slug='unknown'`, and two novelty agents dereference `closest` without
  a `None` guard.
