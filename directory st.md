# IP-SAKTI Sahayak — Directory Structure & Review Logs

> **Document Purpose**: Complete repository blueprint, module mapping, review logs, and Section 17 Exit Checklist tracking.

---

## 1. Complete Repository Layout

```
SIH Final/
├── project brain.md                     # Master architecture, design invariant, and dataflow doc
├── directory st.md                      # Directory structure, module matrix, and review status
├── plan.md                              # Multi-phase development roadmap (Phases 1–8)
├── tech.md                              # Technical specifications, schemas, budgets & SLOs
├── cloud instructions.md                # Deployment blueprint, Docker, AWS/GCP, and security
├── prd.md                               # Product Requirements Document & User Persona Mapping
├── design.md                            # UI/UX design tokens, glassmorphism specs, screen layouts
├── api documentations.md                # REST & OpenAPI specification for v1 endpoints
├── technical doc.md                     # In-depth technical algorithms, rules, and evals guide
├── backend/                             # Python 3.11 / FastAPI Application Service
│   ├── app/
│   │   ├── main.py                      # FastAPI entry point, middleware, exception handlers
│   │   ├── core/                        # Core configuration, security, confidence & sandboxing
│   │   │   ├── config.py                # Environment configs & latency/token budgets
│   │   │   ├── security.py              # DPDP consent logging, auth & token management
│   │   │   ├── sandboxing.py            # Prompt injection defense & document text sanitizer
│   │   │   └── confidence.py            # 4-band confidence & abstention computation
│   │   ├── models/                      # Pydantic schemas for entities & API contracts
│   │   │   ├── passport.py              # Innovation Passport, Facts & Clarification models
│   │   │   ├── canonical.py             # Botanical & API monograph records
│   │   │   ├── regulatory.py            # Rule definitions, condition states, and findings
│   │   │   ├── evidence.py              # Evidence items, lifecycle states & coverage meter
│   │   │   ├── diff.py                  # What-If diffs & regulatory amendment models
│   │   │   ├── institutional.py         # Tenant accounts, case queues & cohort metrics
│   │   │   └── handoff.py               # Expert escalation queue & liability contracts
│   │   ├── services/                    # Core business logic & deterministic engines
│   │   │   ├── passport_engine.py       # Passport state management & follow-up questioning
│   │   │   ├── ingredient_resolver.py   # Canonical botanical resolution & fingerprinting
│   │   │   ├── ingredient_legality.py   # Cross-jurisdiction ingredient legality checker
│   │   │   ├── rule_engine.py           # 3-state deterministic rule evaluator
│   │   │   ├── retrieval_engine.py      # Hybrid lexical + dense RAG retrieval with authority rank
│   │   │   ├── citation_validator.py    # Strict passage grounding & UCR calculation
│   │   │   ├── what_if_engine.py        # Reactive DAG cloner & attribute mutation diff engine
│   │   │   ├── red_team_module.py       # "Challenge My Innovation" examiner objection simulator
│   │   │   ├── provenance_engine.py     # "Why?" Traceable decision graph builder
│   │   │   ├── regulatory_diff_service.py # Gazette change tracker & case notification engine
│   │   │   ├── multilingual_nlp.py      # Indic NLP, code-switching glossary normalizer
│   │   │   └── expert_handoff_service.py# Expert routing & triage dossier compiler
│   │   ├── rules/                       # Versioned YAML / JSON Rule Packs
│   │   │   ├── india_asu_drugs.yaml     # Drugs & Cosmetics Act ASU rules & Schedule T
│   │   │   ├── india_ayurveda_aahara.yaml# FSSAI Ayurveda Aahara Regulations 2022
│   │   │   ├── india_patent_sec3p.yaml  # Section 3(p) Traditional Knowledge rules
│   │   │   ├── us_fda_dshea.yaml        # US 21 CFR 101 Dietary Supplement vs Drug rules
│   │   │   └── canada_nhpd.yaml         # Health Canada Natural Health Product Regulations
│   │   ├── knowledge/                   # Curated statutory gazettes & monograph databases
│   │   │   ├── acts_and_gazettes.json   # Primary legal gazette passages with effective dates
│   │   │   ├── api_monographs.json      # Ayurvedic Pharmacopoeia of India reference standards
│   │   │   ├── botanical_synonyms.json  # Multilingual Sanskrit/Vernacular/Botanical index
│   │   │   └── permitted_tk_prior_art.json # Permitted demonstration prior art records
│   │   ├── api/                         # REST API Route Controllers
│   │   │   └── v1/
│   │   │       ├── router.py            # Master v1 API Router
│   │   │       ├── passport_router.py   # /api/v1/passport endpoints
│   │   │       ├── assessment_router.py # /api/v1/assessment (India, US, Canada)
│   │   │       ├── screening_router.py  # /api/v1/screening (IP & TK screening)
│   │   │       ├── what_if_router.py    # /api/v1/what-if simulation
│   │   │       ├── red_team_router.py   # /api/v1/red-team challenge
│   │   │       ├── evidence_router.py   # /api/v1/evidence & coverage meter
│   │   │       ├── diff_router.py       # /api/v1/regulatory-diff
│   │   │       ├── handoff_router.py    # /api/v1/expert-handoff
│   │   │       ├── institutional_router.py # /api/v1/institutional cohort analytics
│   │   │       └── evals_router.py      # /api/v1/evals benchmark runner
│   │   └── evals/                       # Evaluation & Benchmark Suite
│   │       ├── gold_cases.json          # 30+ Gold standard cases in EN, HI, MR
│   │       └── benchmark_runner.py      # UCR, Precision, Recall & Language-Parity tests
│   ├── tests/                           # Pytest unit & integration tests
│   │   ├── test_rule_engine.py
│   │   ├── test_what_if.py
│   │   ├── test_sandboxing.py
│   │   ├── test_ingredient_resolver.py
│   │   └── test_sih_demo_script.py      # Automated verification of Section 18 SIH script
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/                            # Next.js 14 / TypeScript / Tailwind CSS Client
    ├── src/
    │   ├── app/                         # Next.js App Router
    │   │   ├── layout.tsx               # Root layout with theme provider & font loaders
    │   │   ├── page.tsx                 # Main application dashboard
    │   │   ├── globals.css              # Custom styling & glassmorphism utilities
    │   │   └── api/                     # Backend proxy routes (if needed)
    │   ├── components/                  # Reusable UI Components
    │   │   ├── Navbar.tsx               # Header with language picker & offline sync badge
    │   │   ├── InnovationPassport.tsx   # Fact intake, botanical autocomplete & confirmations
    │   │   ├── ClarificationAlert.tsx   # Missing decision-critical fact prompt
    │   │   ├── JurisdictionMatrix.tsx   # Side-by-side India / US / Canada comparison
    │   │   ├── CitationPopover.tsx      # Clickable statutory gazette passage viewer
    │   │   ├── ProvenanceGraph.tsx      # Interactive "Why?" decision tree
    │   │   ├── WhatIfSimulator.tsx      # Live reactive claim & ingredient diff editor
    │   │   ├── RedTeamModal.tsx         # "Challenge My Innovation" examiner objections
    │   │   ├── EvidenceGapList.tsx      # Task checklist with lifecycle badges & Coverage Meter
    │   │   ├── ExpertHandoffModal.tsx   # Escalation modal with DPDP Act consent
    │   │   ├── InstitutionalView.tsx    # Incubator case queue & cohort analytics
    │   │   └── VoiceIntakeModal.tsx     # Voice recording simulation & transcript confirmation
    │   ├── lib/                         # Client Utilities
    │   │   ├── api.ts                   # Type-safe backend API client
    │   │   ├── i18n.ts                  # Localization dictionary (EN, HI, MR, TA, TE, etc.)
    │   │   └── offlineStorage.ts        # IndexedDB/LocalStorage draft caching
    │   └── types/                       # TypeScript interfaces mirroring backend contracts
    │       └── index.ts
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.js
    └── postcss.config.js
```

---

## 2. Module Mapping & Ownership

| Directory / Module | Core Functionality | Primary Tech | Specification Reference |
| :--- | :--- | :--- | :--- |
| `backend/app/services/passport_engine.py` | Profile creation, fact origin tagging, clarification query | Python / Pydantic | Section 6.1 |
| `backend/app/services/ingredient_resolver.py` | Canonical botanical normalization & formulation fingerprinting | Regex / Python | Section 7.2.1 |
| `backend/app/services/ingredient_legality.py` | Cross-border ingredient legality checking (FDA/HC/FSSAI) | Python / Dict | Section 7.2.2 |
| `backend/app/services/rule_engine.py` | Deterministic 3-state legal evaluation | YAML Rule Evaluator | Section 6.3 & 6.4 |
| `backend/app/services/retrieval_engine.py` | Hybrid RAG search across Acts & Gazettes with authority rank | BM25 + Vector | Section 8 & 11 |
| `backend/app/services/citation_validator.py` | Strict citation-support & Unsupported Claim Rate (UCR) gate | Python / Regex | Section 7.1.1 |
| `backend/app/services/what_if_engine.py` | Single-attribute mutation DAG diffing | Python Graph Diff | Section 6.6 |
| `backend/app/services/red_team_module.py` | Patent examiner objection simulation | Rule + RAG Check | Section 6.7 |
| `backend/app/services/provenance_engine.py` | Full decision chain ("Why?") synthesis | Tree Builder | Section 6.8 |
| `backend/app/services/regulatory_diff_service.py` | Gazette amendment tracker & affected case notifier | Semantic Diff | Section 7.3.1 |
| `backend/app/services/multilingual_nlp.py` | Multilingual entity normalization (10 Indic languages) | Indic Normalizer | Section 6.9 & 7.1.4 |
| `backend/app/core/sandboxing.py` | Document ingestion prompt-injection defense | Text Sanitizer | Section 7.1.2 |
| `frontend/src/components/*` | Glassmorphic, accessible multilingual user interface | Next.js / Tailwind | Section 7.3.3 & 18 |

---

## 3. Section 17 Exit Checklist Tracking

| # | Checklist Item | Target Spec | Build Status |
| :--- | :--- | :--- | :--- |
| 1 | **Unsupported Claim Rate (UCR)** measured & below threshold | Section 12.2 & 17 | ✅ Implemented in `evals/benchmark_runner.py` |
| 2 | **Confidence/Abstention framework** (4 bands: High/Med/Low/Refuse) | Section 7.1.1 | ✅ Implemented in `core/confidence.py` & UI |
| 3 | **Language-parity gate** passed for EN, HI, MR + expanded search | Section 7.1.4 | ✅ Implemented in `services/multilingual_nlp.py` |
| 4 | **Prompt-injection red-team suite** for uploads | Section 7.1.2 | ✅ Implemented in `core/sandboxing.py` |
| 5 | **DPDP Act-aligned consent flow & grievance contact** | Section 7.1.3 | ✅ Implemented in `core/security.py` & Handoff Modal |
| 6 | **TKDL/Restricted source status** explicitly logged as permitted | Section 11.2 | ✅ Implemented in `knowledge/permitted_tk_prior_art.json` |
| 7 | **Cost & Latency SLOs** defined with concrete numbers (p95 < 12s) | Section 7.2.3 | ✅ Implemented in `core/config.py` |
| 8 | **Expert-handoff consent & liability boundary** | Section 7.3.2 | ✅ Implemented in `services/expert_handoff_service.py` |
| 9 | **Every demo claim clickable to exact source passage** | Section 6.8 & 18 | ✅ Implemented in Citation Popovers & Provenance |
| 10 | **Coverage limitations shown by default** | Section 7.3.3 | ✅ Implemented in Jurisdiction Matrix |

---

## 4. Review, Analysis & Finalization Log

- **Log Entry 1 (Architecture Finalization)**: Modular monolith confirmed over microservices to preserve transactional integrity for legal reasoning and prevent key exposure.
- **Log Entry 2 (RAG & Rules Integration)**: Implemented hybrid RAG search with hard authority hierarchy (Gazette > Regulatory Agency > Patent Office > Academic). LLM restricted to explanation generation.
- **Log Entry 3 (Multilingual Coverage)**: Validated core workflows for English, Hindi, and Marathi, with auxiliary botanical dictionary support across Tamil, Telugu, Kannada, Bengali, Gujarati, Malayalam, and Sanskrit.
- **Log Entry 4 (Demonstration Script Hardening)**: Validated all 10 steps of Section 18 SIH demo workflow.
