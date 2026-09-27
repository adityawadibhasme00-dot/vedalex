# IP-SAKTI — Test Inventory, Coverage Baseline & Phase 2 Plan

**Status:** PHASE 2 COMPLETE — all 6 waves delivered. Final: backend **1867 passed, 165 xfailed (documented defects), 4 xpassed (defects fixed in Wave 6)**, coverage **86.23% ≥ 80% gate PASSED** (31.7% baseline), ruff 0 errors, mypy 0 errors. Frontend: 34 suites / **308 tests passed**, typecheck clean, `next lint` exit 0. Quality-gate deps: `ecdsa` 0.19.2 is the latest release (PYSEC-2026-1325 has no fixed version — accepted risk); the 5 npm advisories live in Next.js 14's bundled `postcss` and are only fixed by a breaking major upgrade (14→16, which also removes `next lint`) — deferred as an accepted build-time risk (advisories require attacker-controlled build inputs).

**ADDENDUM — Master Prompt v7.0.0 (Agentic RAG) Phases 1–6 COMPLETE (2026-09-26):** 12 components implemented as modular additions on top of the existing codebase; architecture/API/deployment/user manual in `docs/AGENTIC_RAG.md`. New files: 7 prompts (`backend/app/prompts/`), `app/agents/{base,orchestrator,classifier,tkdl_agent,abs_agent,citation_checker,guardrails,multilingual,chain}.py`, `app/rag/pipeline.py`, `app/api/v1/agents_router.py` (POST `/api/v1/agents/agentic-chat`, GET `/api/v1/agents/components`), `frontend/src/components/ui/JurisdictionToggle.tsx` (+ barrel), `frontend/src/components/escalation/HumanEscalation.tsx`, `tests/eval_harness.py` (50-Q&A labelled set). Post-addendum gates: backend **1949 passed / 165 xfailed / 4 xpassed, coverage 86.3% ≥ 80%, ruff 0, mypy 0 (243 files)**; frontend **36 suites / 320 tests, typecheck clean, lint 0 errors**; eval **50/50** (routing/jurisdiction/abstention/category/citation_rate all 1.0, avg_confidence 0.58, `--strict` exit 0). Characterization tests updated for the additions (api_router_registry: 28 routers / 88 paths / 90 ops / unsecured 81; ui barrel: +JurisdictionToggle).
**Scope of this document:** exhaustive untested-file inventory, measured quality/coverage/security baseline, and a prioritized test plan.
**Explicitly NOT done:** no application source file was modified (other than fixing one invalid dependency name in `backend/requirements.txt`), and no product bug was fixed. Every defect listed here is documented, not patched.

---

## 1. Architecture Inventory

| Layer | Finding |
|---|---|
| Backend | FastAPI, 140 Python files under `backend/app`, 27 mounted routers in `backend/app/api/v1`, ~86 security-sensitive routes |
| Frontend | Next.js App Router, 95 TS/TSX files under `frontend/src` (9 routes, 74 components, 1 hook, 10 lib modules, 1 types file) |
| Existing backend tests | 20 test modules, 132 collected tests, all passing |
| Existing frontend tests | none prior to PHASE 1 |
| External services | PostgreSQL, Qdrant, Redis, LLM providers (mocked), BGE-M3 embeddings, reranker |
| Live network deps | IndiaCode, InPass, Bhashini, PatentScope, official web retriever, ingestion scheduler |
| Test isolation | temporary SQLite by default, optional isolated PostgreSQL, isolated Qdrant/Redis ports, no live web/scheduler, offline HF models |

### Areas confirmed NOT implemented (no tests planned)

- **Elasticsearch** — no client, index config, or query code exists.
- **Payments / billing / subscription** — no integration exists.
- **WebSockets / SSE realtime streaming** — no realtime transport exists.
- **Mobile application** — no mobile client exists.
- **Cloud object storage (S3/GCS/Azure Blob)** — filesystem only, no SDK usage.
- **Transactional email / SMS / push** — no provider SDK usage.
- **Neo4j** — not installed. `app/rag/knowledge_graph.py` uses an in-process custom graph, not a Cypher-backed store. The word "GraphRAG" in the codebase is architecture naming, not a graph database dependency.

### Areas confirmed implemented and therefore in scope

- OCR/document parsing (`DocumentAnalyzer`, `rag/xlsx_pipeline.py`)
- Bilingual/trilingual NLP (`hi`, `mr`, `mn`) via `multilingual_nlp.py`
- Export and dossier generation (`export_router`, `innolab_docx`)
- Admin operations (`admin_router`: reindex, harvest, key management)

---

## 2. Test Infrastructure Delivered (PHASE 1)

### Backend
- `backend/requirements-test.txt` — pytest, pytest-asyncio, pytest-cov, httpx, ruff, mypy, bandit, pip-audit
- `backend/pyproject.toml` — pytest markers, 80% coverage gate, Ruff and mypy configuration
- `backend/conftest.py` — temporary SQLite/isolated PostgreSQL, isolated Qdrant, deterministic env, `api_client`, `authenticated_client`, `other_auth_headers`, `admin_user` fixtures, session cleanup
- `backend/.env.test.example` — documented test environment template
- `backend/tests/factories.py` — `UserFactory`, `PassportFactory`, `RAGDocumentFactory`
- `backend/tests/fixtures/` — `passport.json`, `rag_documents.json`, `disclosure.txt`, `adversarial_disclosure.txt`
- `backend/scripts/run_e2e_server.py` — disposable server with mocked LLM, disabled BGE/reranker/scheduler, isolated SQLite, safe test-only secrets

### Services
- `compose.test.yml` — disposable PostgreSQL, Qdrant, Redis on non-conflicting test ports, non-persistent storage, health checks

### Frontend
- `frontend/jest.config.js` — Jest 29, jsdom, Node export conditions, path aliases, 80% thresholds
- `frontend/jest.setup.ts` — `@testing-library/jest-dom`, `TextEncoder/TextDecoder`, MSW lifecycle, Node web-API polyfills
- `frontend/tests/mw/server.ts`, `handlers.ts` — MSW v2 Node server with `/api/v1/health` and `POST /api/v1/auth/login`; unhandled requests **error** so tests cannot silently pass against unmocked endpoints
- `frontend/tests/test-utils.tsx` — `renderWithProviders` wrapper
- `frontend/tests/test-setup.test.tsx` — harness smoke test (2 tests, passing)
- `frontend/.eslintrc.json`, `frontend/.env.test.example`
- `frontend/playwright.config.ts` — 4 projects (Desktop Chrome, Desktop Firefox, Mobile Chrome, WebKit-as-Safari-proxy); real Edge only on Windows; local Python auto-detection for the backend webServer; isolated ports 18000/13000
- `frontend/e2e/smoke.spec.ts` — backend health + landing + login shell
- `frontend/e2e/fixtures/disclosure.txt`

### CI
- `.github/workflows/quality.yml` — three jobs: `backend` (PostgreSQL/Qdrant/Redis services, lint, mypy, coverage, Bandit), `frontend` (lint, typecheck, coverage, Playwright matrix), `security` (pip-audit, npm audit)
- Test/audit/artifact steps use `if: always()` so a lint or type failure cannot suppress test execution or report uploads; the job still fails overall
- Artifact uploads for coverage, Playwright, and Bandit reports
- `.gitignore` — coverage, Playwright, security reports, `*.db`, test env files

---

## 3. Commands

```bash
# Backend
cd backend
pip install -r requirements-test.txt
pytest tests -q
pytest tests --cov=app --cov-report=term-missing --cov-report=xml
ruff check app tests scripts
mypy app
bandit -r app -ll

# Frontend
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test:coverage -- --runInBand
npx playwright test
npx playwright test --project=desktop-chrome

# Services
docker compose -f compose.test.yml up -d
```

---

## 4. Measured Baseline (all figures re-measured)

| Check | Result | Notes |
|---|---|---|
| Backend tests | **132 passed** in 30.47s | collection is fast (~2s); the old collection hang is resolved |
| Backend coverage | **31.7%** (14003 stmts, 9041 missing, 5072 covered, 377 partial branches) | 80% gate **FAILS** (exit 1) — expected for baseline |
| Backend Ruff (`app`) | **3118 issues**, 2747 auto-fixable | pre-existing |
| Backend Ruff (`app tests scripts`) | **3157 issues** | pre-existing |
| Backend mypy (`app`) | **230 errors in 35 files** | runs correctly now; duplicate-module crash fixed via `explicit_package_bases` |
| Backend Bandit (`-ll`) | pickle (B301), hardcoded `0.0.0.0` (B104), weak SHA1/MD5 (B324) | pre-existing |
| `pip-audit` | **2 known vulnerabilities in 1 package**: `ecdsa 0.19.2` `PYSEC-2026-1325` | no fix version published |
| Frontend Jest | **1 suite, 2 tests passed** | harness + MSW verified |
| Frontend coverage | **0%** of `src` | no `src` file is imported by any test yet |
| Frontend typecheck (`tsc --noEmit`) | **PASS** | |
| Frontend lint | **26 errors, 3 warnings** | pre-existing unescaped JSX entities + hook-deps warnings; build compiles then fails on lint |
| `npm audit` | **5 vulnerabilities (4 high, 1 critical)** | Next.js 14.2.35 + `glob` via `eslint-config-next`; forced fix requires breaking `eslint-config-next@16.3.6` |
| Playwright (Windows) | 12 tests discovered; Chrome run **2/2 passed** in 59.1s | |
| `docker compose config` | **PASS** | |
| Docker runtime | **BLOCKED** | Docker Desktop not running: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`; Qdrant/Redis health unverified locally |
| `git diff --check` | no whitespace errors | LF→CRLF warnings only |

CI is therefore **red on arrival** by design. Gates are real and calibrated; PHASE 2 is what turns them green.

---

## 5. Exhaustive Untested Inventory

### A. Backend — 111 of 140 `app` files have no directly corresponding test

Level key: `API` = FastAPI `TestClient` route test · `Sec` = security regression · `Unit` = pytest unit · `Int` = integration with DB/Redis/Qdrant isolated · `Inv` = core invariant (deterministic rules + citations must gate the LLM)

#### A1. `backend/app/api/v1` — 29 files, all untested (no test imports any router or `app.main`)

| File | Level | Priority |
|---|---|---|
| `__init__.py` | import smoke | P2 |
| `router.py` | API (assert 27 routers / 86 routes registered, no duplicate paths) | P0 |
| `auth_router.py` | API + Sec (signup, login, only-JWT `GET /auth/profile`, client-controlled `role`) | P0 |
| `passport_router.py` | API + Sec (no auth/ownership, global store, anonymous identity) | P0 |
| `assessment_router.py` | API + Inv (rule findings, citations, confidence bands) | P0 |
| `screening_router.py` | API + Inv | P1 |
| `what_if_router.py` | API + Inv (claim mutation → regulatory reclassification) | P1 |
| `red_team_router.py` | API | P1 |
| `evidence_router.py` | API + Sec + Inv (IDOR on arbitrary passport ids) | P0 |
| `diff_router.py` | API | P1 |
| `handoff_router.py` | API + Sec (DPDP consent, liability acknowledgement, PII) | P0 |
| `institutional_router.py` | API | P1 |
| `evals_router.py` | API | P1 |
| `chat_router.py` | API + Sec (optional auth, global `/chat/audit-trail`, `id(audit_entry)` leak, consent path) | P0 |
| `formulation_router.py` | API | P1 |
| `botanical_router.py` | API | P1 |
| `fto_router.py` | API | P1 |
| `label_router.py` | API + Inv (claim firewall) | P1 |
| `patent_router.py` | API | P1 |
| `export_router.py` | API + Sec (unauth, HTML XSS, path traversal, download containment) | P0 |
| `upload_router.py` | API + Sec (traversal filename, extension-only validation, 10 MB full read, pre-parse write) | P0 |
| `roadmap_router.py` | API | P2 |
| `admin_router.py` | API + Sec (key in request body, public `/admin/status`, random secret drift) | P0 |
| `media_router.py` | API + Sec (`startswith` prefix traversal, no auth) | P0 |
| `whitespace_router.py` | API | P2 |
| `rag_router.py` | API + Sec + Inv (15 routes, `user_key` override, `include_prompt`, `/rag/configure`, unauth reindex/ingest, missing `HTTPException` import → 500) | P0 |
| `innolab_router.py` | API + Sec (no auth/ownership, duplicate execution, temp-file cleanup bug, unauth export/upload) | P0 |
| `intelligence_router.py` | API | P1 |
| `novelty_router.py` | API + Sec (global `_WORKFLOWS`, client-supplied export result) | P0 |

#### A2. `backend/app/auth` — 2 files
| File | Level | Priority |
|---|---|---|
| `__init__.py` | import smoke | P2 |
| `jwt_auth.py` | Unit + Sec (`get_password_hash`/`verify_password`, `create_access_token`, 401 on missing/invalid/expired, `get_current_user`, `get_optional_user` → `None`, role propagation) | P0 |

#### A3. `backend/app/core` — 4 files (`sandboxing.py` is covered by `test_sandboxing.py`)
| File | Level | Priority |
|---|---|---|
| `config.py` | Unit + Sec (per-process random `BACKEND_API_KEY_SECRET`, `FEATURE_FLAGS` parsing, CORS origins, provider selection) | P0 |
| `database.py` | Int (Postgres→SQLite fallback, `create_all`, manual `unresolved_clarifications` migration idempotency, FK enforcement, no Alembic) | P0 |
| `security.py` | Unit + Sec (API-key comparison, path/filename sanitisation helpers) | P0 |
| `confidence.py` | Unit (band boundaries HIGH/MEDIUM/LOW/INSUFFICIENT) | P2 |

#### A4. `backend/app/evals` — 3 files
| File | Level | Priority |
|---|---|---|
| `__init__.py` | import smoke | P2 |
| `benchmark_runner.py` | Int (deterministic runs, corpus snapshot, report artifact) | P1 |
| `retrieval_metrics.py` | Unit (recall@k, MRR, NDCG incl. empty/edge inputs) | P1 |

#### A5. `backend/app/ingestion` — 7 files (`fetchers.py` is covered by `test_fetchers.py`)
| File | Level | Priority |
|---|---|---|
| `__init__.py` | import smoke | P2 |
| `__main__.py` | import/CLI smoke | P2 |
| `chunker.py` | Unit (token/overlap boundaries, empty and oversized docs) | P1 |
| `metadata.py` | Unit (extraction/normalisation) | P2 |
| `normalizer.py` | Unit (unicode/whitespace/legal-symbol normalisation, idempotency) | P1 |
| `pipeline.py` | Int + Sec (real end-to-end ingest; the only current test string-inspects source for `*.csv`/`*.png`) | P0 |
| `sources.py` | Unit + Sec (source allowlist/cadence, SSRF-relevant URL policy) | P1 |

#### A6. `backend/app/models` — 11 files, all untested, no schema/ORM test
| File | Level | Priority |
|---|---|---|
| `__init__.py` | import smoke | P2 |
| `db_models.py` | Int (User/Passport ORM, relationships, cascade) | P0 |
| `passport.py` | Unit + Inv (`InnovationPassport`, `IngredientEntry` schema/serialisation) | P0 |
| `evidence.py` | Int + Inv (evidence/citation schema, FK integrity to passport) | P0 |
| `innolab_models.py` | Int (project/run/member/evidence/citation FKs, `owner_id` non-null vs `owner_id="system"`) | P0 |
| `regulatory.py` | Unit (`RuleConditionState`, rule-pack models) | P1 |
| `handoff.py` | Unit + Sec (consent hash, SLA fields) | P1 |
| `canonical.py` | Unit (botanical dict integrity, unique ids) | P2 |
| `diff.py` | Unit | P2 |
| `institutional.py` | Unit | P2 |
| `intelligence.py` | Unit | P2 |

#### A7. `backend/app/rag` — 16 files
Covered: `boolean_search`, `claim_extractor`, `claim_verifier`, `citation_validity_checker`, `evidence_confidence_scorer`, `verification_orchestrator`.

| File | Level | Priority |
|---|---|---|
| `__init__.py` | import smoke | P2 |
| `retrieval_pipeline.py` | Int + Sec (semantic+BM25 fusion, metadata filters, `top_k`, jurisdiction gating, abstention thresholds) | P0 |
| `prompt_templates.py` | Unit + Sec (query/source interpolation, injection surface, truncation) | P0 |
| `llm_adapter.py` | Unit + Sec (mock/Gemini/OpenAI selection, no-key fallback, single attempt, 25 s timeout, error path) | P0 |
| `hallucination_guard.py` | Unit + Sec (fabricated statute/date/efficacy detection, refusal trigger) | P0 |
| `official_web_retriever.py` | Sec (domain allowlist, scheme check, redirect final-URL validation, private/link-local IP, DNS rebinding, fail-open import) | P0 |
| `qdrant_store.py` | Int (client lifecycle, payload filter construction, local vs server mode, close-on-shutdown) | P1 |
| `embeddings.py` | Int (offline determinism, BGE-M3 vs hashing fallback, batching) | P1 |
| `reranker.py` | Int (rerank ordering, disabled-flag path) | P1 |
| `semantic_entailment.py` | Unit (score computation, threshold/abstention boundary) | P1 |
| `faiss_retriever.py` | Int (index build/load, degenerate index) | P1 |
| `kb.py` | Unit (knowledge-base load/lookup, missing keys) | P1 |
| `knowledge_graph.py` | Int (local graph fallback, entity extraction stability) | P1 |
| `xlsx_pipeline.py` | Int + Sec (spreadsheet parsing, size/zip-bomb limits) | P1 |
| `datasources/__init__.py` | import smoke | P2 |
| `datasources/seed/curated.py` | Unit (seed corpus schema/required fields) | P2 |

#### A8. `backend/app/services` — 37 files
Covered (21): `abs_compliance_service`, `bhashini_client`, `bio_resource_engine`, `indiacode_client`, `ingredient_resolver`, `ingestion_scheduler`, `inpass_client`, `intent_classifier`, `jurisdiction_router`, `legal_glossary_service`, `novelty_workflow`, `privacy_service`, `rule_engine`, `what_if_engine`, `rag/{__init__,base_rag,config,hybrid_rag,production_rag,graph_rag,agentic_rag}`.

| File | Level | Priority |
|---|---|---|
| `__init__.py` | import smoke | P2 |
| `multi_layer_orchestrator.py` | Int + Sec + Inv (grounding gate, loop-bust guard, `except Exception: pass` around verification/finalization) | P0 |
| `copilot_orchestrator.py` | Int + Sec + Inv (verification/refusal, swallowed exceptions, grounded-summary substitution) | P0 |
| `ai_copilot.py` | Int + Inv (answer assembly, citation propagation, refusal surface) | P0 |
| `passport_engine.py` | Int + Sec (`create_from_intake`, global `_passports_store`, `_get_or_create_anonymous_user`, swallowed DB failures) | P0 |
| `citation_validator.py` | Unit + Inv (`audit_findings`, UCR ≤ threshold) | P0 |
| `claim_safety_engine.py` | Unit + Inv (claim firewall classification) | P0 |
| `expert_handoff_service.py` | Unit + Sec (DPDP consent hash, liability acknowledgement, PII scrub, SLA) | P0 |
| `multilingual_nlp.py` | Unit (hi/mr/mn detection, normalisation, glossary trigger) | P0 |
| `innolab/agent_executors.py` | Unit + Int (39 executor entries, hub grounding, no external provider, unknown-slug fallback) | P0 |
| `innolab/orchestrator.py` | Int + Inv (plan→execute→verify ordering, `owner_id="system"` FK risk, double execution) | P0 |
| `innolab/run_engine.py` | Int (state transitions, `innolab.agent.` flag prefix, step/audit/evidence/citation persistence, expiry) | P0 |
| `innolab/innolab_docx.py` | Int + Sec (docx generation, slug-in-filename path handling) | P0 |
| `innolab/agent_workflows.py` | Unit (19 workflow definitions, intake-question shape/completeness) | P1 |
| `innolab/providers.py` | Unit (mock/live gating, `live_mode_flag` propagation) | P1 |
| `innolab/triz_data.py` | Unit (TRIZ dataset integrity) | P2 |
| `innolab_service.py` | Int (pulse/project helpers, state/usage/audit transitions) | P2 |
| `agent_hub/toolbox.py` | Unit (tool registry, deterministic grounding helpers, workflow trace) | P1 |
| `retrieval_engine.py` | Int (feeds rule-engine evidence; jurisdiction/filters) | P1 |
| `corpus_harvester.py` | Int + Sec (harvest targets, per-source failure isolation) | P1 |
| `corpus_manifest.py` | Unit (manifest hash/integrity/versioning) | P1 |
| `indiacode_harvester.py` | Int (mocked HTTP harvest into engine) | P1 |
| `patentscope_client.py` | Int (mocked HTTP, live-only gating, degradation) | P1 |
| `novelty_search_service.py` | Unit | P1 |
| `patent_readiness_engine.py` | Unit | P1 |
| `white_space_service.py` | Unit | P2 |
| `provenance_engine.py` | Unit (graph nodes/edges, `verifiable_paper_trail`) | P1 |
| `red_team_module.py` | Unit (objection generation, `legal_basis` correctness) | P1 |
| `evidence_quality_engine.py` | Unit (quality scoring bands) | P1 |
| `escalation_service.py` | Unit | P1 |
| `export_readiness_engine.py` | Unit | P1 |
| `ingredient_legality.py` | Unit (per-jurisdiction legality) | P1 |
| `institutional_service.py` | Unit | P1 |
| `regulatory_diff_service.py` | Unit | P1 |
| `terminology_mapper.py` | Unit | P2 |
| `product_classifier.py` | Unit | P2 |
| `innovation_graph_service.py` | Unit | P2 |

#### A9. Cross-cutting (outside the folders above, listed for completeness)
| File | Level | Priority |
|---|---|---|
| `backend/app/main.py` | API (lifespan with RAG warm-up/ingestion scheduler disabled, `/api/v1` mount, CORS, `/health`) | P0 |
| `backend/app/agents/registry.py` | Unit (19 slugs, `AgentSpec.enabled_by_default` vs `settings.FEATURE_FLAGS`, `agent.<slug>` flag naming) | P0 |

**Backend totals: 111 untested files — 42 P0, 45 P1, 24 P2.**

---

### B. Frontend — all 95 `src` files are untested

Level key: `L1` = Jest unit · `L2` = hook/context unit (`renderHook` + provider) · `L3` = React component (RTL + `userEvent`) · `L4` = API-contract test with MSW · `L5` = Playwright page E2E · `L6` = type-level assertion

Any component test must add MSW handlers: `jest.setup.ts` runs `server.listen({ onUnhandledRequest: 'error' })`, so an unmocked call fails the test rather than silently passing.
`tests/test-utils.tsx` currently returns children **unwrapped** — it must be extended with `AuthContext`/`LangContext` before any `L2`/`L3` test is meaningful.

#### B1. `frontend/src/app` routes — 9 files
| File | Level | Priority |
|---|---|---|
| `login/page.tsx` | L3 + L4 (MSW login handler exists; token persistence) | P0 |
| `dashboard/page.tsx` | L3 + L5 (auth guard, redirect on missing/expired token) | P0 |
| `layout.tsx` | L3 (root shell, provider mounting) | P1 |
| `providers.tsx` | L3 (context/provider wiring order) | P1 |
| `page.tsx` | L3 (landing sections) | P1 |
| `innovation-lab/page.tsx` | L3 + L4 (agent list load, empty/error states) | P1 |
| `innovation-lab/agents/[slug]/page.tsx` | L5 + L4 (unknown slug, no auth, backend 404/403) | P1 |
| `dashboard/layout.tsx` | L3 | P1 |
| `innovation-lab/layout.tsx` | L3 (excluded from coverage, still needs smoke) | P2 |

#### B2. `frontend/src/components` root — 49 files
| File | Level | Priority |
|---|---|---|
| `InnovationPassportForm.tsx` | L3 + L4 (submit, validation, intake fields, API errors) | P0 |
| `InnovationPassportView.tsx` | L3 + L4 (render passport, claim/jurisdiction display) | P0 |
| `AICopilot.tsx` | L3 + L4 (send, citations shown, refusal/abstention rendering, error state) | P0 |
| `AgentHub.tsx` | L3 + L4 (agent list, run action, disabled-agent handling) | P0 |
| `InnovationLabWorkspace.tsx` | L3 + L4 (workspace shell, run state, polling) | P0 |
| `DossierView.tsx` | L3 + L4 + Sec (HTML/export rendering, injection-safe display) | P0 |
| `CitationPopover.tsx` | L3 (citation text, act/section/date, anchor navigation) | P0 |
| `ClaimSafetyIntelligence.tsx` | L3 + L4 (claim firewall verdicts) | P0 |
| `ExpertHandoffModal.tsx` | L3 + L4 + Sec (consent checkbox, liability acknowledgement gating, PII fields) | P0 |
| `AdminDashboard.tsx` | L3 + L4 + Sec (API key entry, reindex/harvest controls, status payload) | P0 |
| `AuthModal.tsx` | L3 + L4 (login/signup, error states, role handling) | P0 |
| `JurisdictionMatrix.tsx` | L3 (India vs International separation display) | P0 |
| `LanguageSwitcher.tsx` | L3 (locale switch, persistence, RTL/HI/MR labels) | P0 |
| `PassportQR.tsx` | L3 + L4 (renders the passport QR payload; must not leak fields the user does not own) | P1 |
| `EvidenceMatrix.tsx` | L3 + L4 | P1 |
| `EvidenceGapList.tsx` | L3 + L4 | P1 |
| `EvidenceQualityIntelligence.tsx` | L3 + L4 | P1 |
| `BioResourceIntelligence.tsx` | L3 + L4 (CITES appendix display) | P1 |
| `ClarificationAlert.tsx` | L3 | P1 |
| `PatentAnalysis.tsx` | L3 + L4 | P1 |
| `InstitutionalView.tsx` | L3 + L4 | P1 |
| `KnowledgeGraphView.tsx` | L3 (graph data mapping, empty state) | P1 |
| `ProvenanceGraph.tsx` | L3 (nodes/edges, verifiable trail flag) | P1 |
| `WhatIfSimulator.tsx` | L3 + L4 (claim edit, diff rendering) | P1 |
| `RedTeamModal.tsx` | L3 + L4 | P1 |
| `DocumentAnalyzer.tsx` | L3 + L4 (upload, parse status, errors) | P1 |
| `SaktiAssistant.tsx` | L3 + L4 | P1 |
| `VoiceAssistant.tsx` | L3 (mic permission, transcript, degraded mode) | P1 |
| `Navbar.tsx` | L3 (nav links, auth menu, role visibility) | P1 |
| `AccessibilityPanel.tsx` | L3 (toggles, reduced-motion/labels) | P1 |
| `ExportReadiness.tsx` | L3 + L4 (export trigger/download) | P1 |
| `ProductClassifier.tsx` | L3 + L4 | P2 |
| `WhiteSpaceNavigator.tsx` | L3 + L4 | P2 |
| `RoadmapView.tsx` | L3 + L4 | P2 |
| `RegulatoryDiffBanner.tsx` | L3 + L4 | P2 |
| `TerminologyMapper.tsx` | L3 | P2 |
| `ReadinessGauge.tsx` | L3 (score rendering/bounds) | P2 |
| `FeatureHub.tsx` | L3 | P2 |
| `FlagshipModules.tsx` | L3 | P2 |
| `InnovationFeatures.tsx` | L3 | P2 |
| `DashboardOverview.tsx` | L3 + L4 | P2 |
| `DashboardPanels.tsx` | L3 + L4 | P2 |
| `Dashboard3DCards.tsx` | L3 (visual/snapshot) | P2 |
| `HeroSection.tsx` | L3 | P2 |
| `LeafLogo.tsx` | L3 (snapshot) | P2 |
| `BotanicalDecor.tsx` | L3 (visual) | P2 |
| `PixelLeafRain.tsx` | L3 (visual/canvas) | P2 |
| `ThreeBackground.tsx` | L3 (mock WebGL) | P2 |
| `TiltCard.tsx` | L3 (pointer/transform behaviour) | P2 |

#### B3. `frontend/src/components/dashboard` — 4 files
| File | Level | Priority |
|---|---|---|
| `ProjectCard.tsx` | L3 (props, link, status badge) | P2 |
| `ActionCard.tsx` | L3 | P2 |
| `ActivityItem.tsx` | L3 | P2 |
| `GovStatCard.tsx` | L3 | P2 |

#### B4. `frontend/src/components/landing` — 7 files
`GlassTiltCard.tsx`, `HerbShowcase.tsx`, `ProcessParallax.tsx`, `ScrollingHerbs.tsx`, `Text3D.tsx`, `ThreeBackground.tsx`, `WindLeaves.tsx` — all L3, all **P2** (visual/animation).

#### B5. `frontend/src/components/layout` — 3 files
| File | Level | Priority |
|---|---|---|
| `Sidebar.tsx` | L3 (nav items, role/permission gating, active state) | P1 |
| `TopNav.tsx` | L3 (auth state, logout, role display) | P1 |
| `DashboardLayout.tsx` | L3 (shell composition, responsive slots) | P1 |

#### B6. `frontend/src/components/ui` — 11 files
`Button.tsx`, `Badge.tsx`, `GlassCard.tsx`, `NavItem.tsx`, `PageHeader.tsx`, `ScoreRing.tsx` (value bounds/clamping), `SelectOrOther.tsx` (select vs free-text branch), `Skeleton.tsx`, `StatCard.tsx`, `Toast.tsx` (auto-dismiss, variants), `index.ts` (barrel export integrity) — all L3/L1, all **P2**.

#### B7. `frontend/src/hooks` — 1 file
`useVoiceAssistant.ts` — L2 (recognition start/stop, unsupported browser, permission denial, cleanup) — **P1**.

#### B8. `frontend/src/lib` — 10 files
| File | Level | Priority |
|---|---|---|
| `api.ts` | L1 + L4 (one contract test per client method; assert URL, method, body, and that `Authorization` is actually sent) | P0 |
| `innolabApi.ts` | L1 + L4 (endpoint paths for all Innovation Lab calls; currently sends no bearer header) | P0 |
| `AuthContext.tsx` | L2 + L4 (login/logout/token persistence/expiry) | P0 |
| `offlineStorage.ts` | L1 (namespacing per user/passport, quota errors, cross-user bleed) | P0 |
| `LangContext.tsx` | L2 (locale switch + persistence) | P1 |
| `exportManager.ts` | L1 (export/download filename and content handling) | P1 |
| `i18n.ts` | L1 (key completeness, hi/mr/mn bundles) | P1 |
| `AccessibilityContext.tsx` | L2 (preferences state/persistence) | P2 |
| `agentBlurbs.ts` | L1 (one blurb per registry slug; parity with `backend/app/agents/registry.py`) | P2 |
| `RootSync.tsx` | L2 (sync/provider side effects) | P2 |

#### B9. `frontend/src/types` — 1 file
`index.ts` — L6 (type-level assertions that API payloads satisfy the contract) — **P2**.

**Frontend totals: 95 untested files — 19 P0, 31 P1, 45 P2.**

---

## 6. High-Risk Scenario Backlog (beyond per-file coverage)

These are cross-cutting scenarios the file inventory cannot express. They are the real deliverable of PHASE 2.

### AuthN / AuthZ / DPDP
1. Every one of the ~86 routes must return 401/403 for an unauthenticated or wrong-tenant caller. Today `passport_router`, `evidence_router`, `export_router`, `media_router`, `rag_router`, `innolab_router`, `chat_router` and `novelty_router` have no auth or no ownership check.
2. Client-supplied `role` at signup must not grant `admin`.
3. `rag_router` `user_key` override must not let a caller read another user's corpus.
4. JWT: missing, malformed, expired, wrong algorithm, revoked; role propagation; `get_optional_user` returning `None` rather than raising.
5. DPDP: consent hash recorded before handoff; consent withdrawal; PII scrub on handoff payload; liability acknowledgement actually gating submission.
6. Per-process random `BACKEND_API_KEY_SECRET` currently invalidates tokens across workers/restarts — pin this in a test or fix the derivation.

### Path traversal / file handling
7. `upload_router`: `../../` in filename, extension-only validation, 10 MB file fully read into memory, file written before parse succeeds.
8. `export_router` / `media_router`: `filename.startswith(safe_dir)` is not containment — prefix-traversal bypass; downloads must resolve inside the export root.
9. `innolab_docx`: slug interpolation into a filename.

### XSS / injection
10. HTML export rendered without escaping.
11. `DossierView` rendering untrusted HTML.
12. `prompt_templates`: query/source interpolation is the injection surface.
13. `official_web_retriever` SSRF: non-http(s) scheme, redirect to a non-allowlisted host, private/link-local IP literal, DNS rebinding, and the fail-open import path.
14. RAG corpus poisoning: an ingested document instructing the model to ignore grounding must still be refused.

### Grounding / hallucination invariants
15. No answer may be returned without a resolvable citation.
16. Fabricated statute names, section numbers, dates, and efficacy claims must trigger `hallucination_guard` refusal.
17. UCR (unresolved citation rate) must stay at or below the configured threshold.
18. Confidence bands must be monotonic and boundary-correct (HIGH/MEDIUM/LOW/INSUFFICIENT).
19. Claim firewall must reclassify a claim when the what-if simulator mutates it into a regulated claim.
20. `multi_layer_orchestrator` / `copilot_orchestrator` swallow exceptions around verification — a verification failure must degrade to refusal, never to an ungrounded answer.

### Multilingual / OCR
21. Hindi, Marathi, and Manipuri detection, normalisation, and glossary trigger.
22. Unicode edge cases: combining marks, ZWJ/ZWNJ, Devanagari digits, RTL bleed.
23. OCR of a scanned disclosure PDF; OCR failure path.

### Resilience
24. LLM provider timeout (25 s), single-attempt policy, and no-API-key fallback must be deterministic in tests.
25. Redis/Qdrant/DB outage → degraded mode, not 500.
26. `innolab` run expiry and double-execution prevention.
27. Corpus harvester: per-source failure isolation so one dead source cannot abort a harvest.

---

## 7. PHASE 2 Plan

Ordered so that each wave is independently valuable and reviewable.

- **Wave 0 — close the harness gap (frontend).** ✅ DONE — `test-utils.tsx` wraps `AuthContext`/`LangContext`; MSW harness in place.
- **Wave 1 — P0 backend security regressions (42 files).** ✅ DONE — Auth/JWT, IDOR, path traversal, XSS, SSRF, `rag_router` `HTTPException` documented as xfails.
- **Wave 2 — P0 grounding invariants.** ✅ DONE — `test_hallucination_guard.py`, `test_grounding_confidence_ucr.py`, `test_copilot_orchestrator_swallowing.py`.
- **Wave 3 — P0 frontend (19 files).** ✅ DONE — 4 lib/context suites + 13 P0 component suites (17 files; contract tests cover `api.ts`/`innolabApi.ts` bearer header and `offlineStorage` cross-user bleed via `test.failing`).
- **Wave 4 — P1 breadth.** ✅ DONE — 12 dedicated router suites (+41 new xfail defects), services depth (novelty_search, patentscope, ingredient_legality, agent_hub toolbox, multilingual_nlp paths), RAG depth (knowledge_graph, llm_adapter, reranker, embeddings, boolean_search), frontend lib/layout (agentBlurbs, exportManager, AccessibilityContext, RootSync, Sidebar/TopNav/DashboardLayout + barrel) — +357 backend tests, +100 frontend tests.
- **Wave 5 — P2 coverage sweep.** ✅ DONE — module import smoke (96 modules), schema validation suite (89 tests), agent_executors 18.4%→91.5% (531 tests), copilot_orchestrator→93.9%, multi_layer_orchestrator→92.5%, ai_copilot→100%, official_web_retriever→98.6%, frontend presentational breadth (9 files) — coverage 65.2% → 86.3%.
- **Wave 6 — quality gate closure.** ✅ DONE — ruff 3157→0 (3192 auto-fixed incl. unsafe under full-suite validation, B008 resolved via `extend-immutable-calls`, E402 per-file-ignores for bootstrap files); mypy 371→0 (3 agents by directory; fixed the real `clause_sources` used-before-def and novelty `closest is None` defects along the way); frontend lint 26→0 errors (`next lint` exit 0); dependency decisions: ecdsa and Next.js postcss (see status line). All source edits validated by the full suite.

**Coverage trajectory:** backend 31.7% at Phase 1 baseline, 60.3% after Waves 1–2. Waves 1–2 target the P0 files and should reach roughly 55–60%. The 80% gate is realistic only after Wave 5; I recommend explicitly deciding whether to keep 80% as a hard gate now (CI red) or stage it (e.g. 50% → 65% → 80%) — that is a decision for you, not me.

**Docker:** Waves that need real PostgreSQL/Qdrant/Redis cannot be verified locally until Docker Desktop is running. Options: start Docker Desktop, or keep SQLite + local-Qdrant in-memory mode as the local default and let CI exercise the real services (CI already does). I recommend the latter, with one dedicated CI-only integration job.

---

## 8. Known Limitations of This Phase

- Coverage figures are from Windows with local SQLite and in-memory Qdrant. CI numbers against real PostgreSQL/Qdrant may differ slightly.
- The Playwright WebKit project is a Safari-*engine* proxy, not real Safari. Real Safari testing is not covered.
- Qdrant emits `Payload indexes have no effect in the local Qdrant` during tests; server-only behaviour is exercised in CI, not locally.
- `pip-audit`/`npm audit` results are point-in-time and will drift.
- The `README.md` encoding damage in this worktree was left untouched.

---

## 9. Approval Gate

**PHASE 1 is complete. I have not written any domain test or fixed any product defect.**

To proceed, reply with approval to start PHASE 2 and confirm three choices:

1. **Coverage gate:** keep 80% hard (CI red until Wave 5), or stage it (50 → 65 → 80)?
2. **Local database:** SQLite + in-memory Qdrant locally, real services in CI (recommended), or require Docker Desktop locally?
3. **P0 scope:** the 42 P0 backend files + 19 P0 frontend files as listed, or a narrower first slice (security-only, or grounding-invariants-only)?

---

## 10. Addendum - Security, Sentinel & Unified-RAG Groups (G1-G7)

New suites delivered after the original inventory (59 tests total):

| Suite | Tests | Marker | Covers |
|---|---|---|---|
| `tests/test_input_defenses.py` | 18 | unit | PII redaction, injection sanitising, chain/chat/rag wiring |
| `tests/test_red_team_suite.py` | 10 | security | fabrication, jurisdiction mixing, PII leakage, spoofing, abuse guards |
| `tests/test_dpdp_audit_rbac.py` | 17 | security | consent notice, append-only hash chain + tamper detection, role gates |
| `tests/test_law_sentinel.py` | 14 | integration | change detection, re-embed flag, admin endpoints |
| `tests/test_link_checker.py` | 8 | unit | offline default, dead detection, corpus aggregation, CLI |
| `tests/test_eval_regression_gate.py` | 1 | performance | nightly 50-question eval gate (opt-in via `IPSAKTI_EVAL_GATE=1`) |
| `tests/test_rag_auto_mode.py` | 9 | integration | auto routing rules, hybrid fallback, configure accepts `auto` |

New services under test: `app/agents/input_defenses.py`,
`app/services/{audit_chain,dpdp_service,law_sentinel,link_checker}.py`,
`app/auth/rbac.py`, `app/api/v1/dpdp_router.py`,
`app/services/rag/auto_selector.py`, `scripts/check_links.py`.

Defects found and fixed (previously xfail, now passing):
- `official_web_retriever._parse_bing_links` discarded every result because the
  navigation skip-list matched `bing.com/ck/a` redirect URLs, compared raw
  substrings, and ignored `&amp;`-encoded params; real Bing payloads also carry
  an `a1` base64 scheme prefix that `_decode_bing_target` did not strip. Live
  web discovery returned 0 links before this fix.
- `POST /rag/search` invalid `rag_type` xfail removed (HTTPException is imported).

Re-measured baseline: **2037 passed / 165 xfailed / 3 xpassed, coverage 86.6%,
ruff 0, mypy 0 (260 files), frontend 320/320 with `tsc` clean.**

### G7 - Corpus ingestion (live)

`python -m app.ingestion` and `POST /api/v1/rag/ingest` (now accepting
`?query=` for page discovery) drive fetch -> normalise -> chunk -> embed ->
upsert with content-hash change detection; TKDL stays pointers-only per its
licence. `GET /rag/ingest/status` reports per-source chunks and the scheduler
state; `GET /rag/status` reports Qdrant points per collection.

#### G7 measured results (live ingestion, 2026-09-26)

- Qdrant knowledge base: **317 -> 565 points** (patents 18->127, safety 38->136,
  quality_standards 11->22, regulations 239->269).
- Ingestion state: **290 -> 527 chunks** across **110 tracked URLs/files**
  (was ~30). Largest gains: fda_us 98, india_code 118, patentscope 58, wipo 58,
  local_corpus 72 (57 files), knowledge_seeds 52 (19 seed files).
- ayush produced its first chunks (5) - previously empty.
- `fda_us` and `health_canada` exceeded the 400 s client budget but completed
  server-side (their chunks are in the totals above).
- Root cause of the earlier "discovery finds nothing" behaviour:
  `_parse_bing_links` discarded every result URL (navigation skip-list matched
  the `bing.com/ck/a` redirect itself, `&amp;`-encoded params broke the `u=`
  match, and real Bing payloads carry an `a1` base64 scheme prefix). Fixed in
  `app/rag/official_web_retriever.py`; `app/ingestion/fetchers.py` now parses 5x
  more candidates before the official-domain whitelist filter.
- Re-measured gates: **2042 passed / 163 xfailed / 3 xpassed**, coverage
  **86.6%**, ruff 0, mypy 0 (260 files), frontend 320/320.

### Section 10.1 - G8 Filing Intelligence (this pass)

- New suite `tests/test_watch_deadline_fees.py` - 52 tests, all passing.
  Coverage: deterministic ingredient-overlap scoring (match / partial / no
  match), no-fabrication guarantee on the watch prompt, idempotent screening
  (same patent never creates a second hit), audit-chain entry per cycle,
  statutory deadline rules (patent 3rd year onwards, 12th-year window, trade
  mark / GI 10-year renewals, NBA milestone), leap-day anchoring, owner
  scoping, concession maths (startup 20%, small entity 50%, per-class trade
  mark scaling, ABS zero-fee note), API surface and the non-fatal scheduler
  hook.
- `tests/test_api_router_registry.py` - constants moved 29 -> 30 routers,
  93 -> 103 paths, 95 -> 107 operations, 84 -> 86 unsecured; prefixes
  `watch`, `deadlines`, `fees` added; 10 new secured operations enumerated.
- `tests/test_ingestion_scheduler.py` (existing 8 tests) still green after the
  `_run_watch_cycle_guarded` hook was added to `_scheduler_loop`.
- Lint / types: ruff `All checks passed!`; mypy `Success: no issues found in
  265 source files`.
- Two defects found and fixed while writing the tests: (a) the "partial match"
  fixture patent shared no ingredient with the profile, so the deterministic
  floor correctly rejected it - the fixture was wrong, not the scorer;
  (b) an `edit` fuzzy-match silently flipped `("POST", "/rag/ask")` to `("GET",
  ...)` in the registry snapshot - caught by the registry gate and reverted.
