# Eureka Parity Checklist — Innovation Lab (IP-SAKTI)

Mission: **every agent in the website's Innovation Lab must take the same inputs, run the same workflow**
and deliver the same structured outputs as the corresponding **PatSnap Eureka** agent.

Verified against:
- Actual code: `backend/app/services/innolab/agent_workflows.py` (steps + questions — source of truth),
  `backend/app/services/innolab/agent_executors.py` (sections + evidence), frontend wizard (`frontend/src/app/innovation-lab/agents/[slug]/page.tsx`).
- Eureka behaviour researched from PatSnap Eureka product pages, Eureka blog guides, PatSnap Help Center and Open-Platform API docs.

Source-of-truth mapping rule: a workflow change in `agent_workflows.py` automatically changes the wizard sidebar, the run trace and the orchestrator — so one fix propagates everywhere.

Legend for status:
- ✅ Done & verified live
- 🟡 Present but approximated in the offline build (honest placeholders, no fabricated data)
- 🔴 TBD / gap

---

## 1. Engineering

### 1.1 TRIZ — Eureka *TRIZ (Engineering)*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Technical problem + system | `problem_text`, `system_name` | ✅ |
| Improving parameter | `improve_aspect` (Speed/Cost/Yield/Quality/Efficiency/Sustainability/Safety/Stability) | ✅ |
| Worsening trade-off (contradiction) | `tradeoff` | ✅ |
| Constraints | `constraint` | ✅ |
| **Workflow** | | |
| Frame → Analyze → Solve (3 phases w/ checkpoints) | 7 steps, phase-grouped (frame, decompose, causal chain, matrix, cluster prior art, directions, refine) | ✅ |
| 39×39 contradiction matrix / 40 principles | matrix row in code (principle ranking) | 🟡 static principle set |
| **Output** | | |
| Contradiction + recommended principles | `sections` → *TRIZ contradiction* + *Recommended inventive principles* | ✅ |
| Prior-art analogies, risks, validation | `findings`, `evidence`, `suggestions` | ✅ |
| Data sources | *Data sources (where this answer is grounded)* rail | ✅ |

### 1.2 Quick Research — Eureka *Quick Research Report*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Research topic | `problem_text` | ✅ |
| Region(s) | `target_markets` | ✅ |
| Time horizon | `timeframe` (5y/10y/latest/all) | ✅ |
| **Workflow** | | |
| Parse → auto 8-module outline → confirm → generate w/ citations | 9 steps, one per module | ✅ |
| **Output** | | |
| 8 fixed report modules (background, market, status, evolution, key patents, innovation ideas) | `sections` 8 fixed modules; claims cite real passages | ✅ |
| Citations + export | summary + evidence + sources rail | ✅ |

### 1.3 Find Solutions — Eureka *Find Solutions*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Technical task | `problem_text` | ✅ |
| Current process | `process_desc` | ✅ |
| Constraints to respect | `constraint` | ✅ |
| Success goal | `improve_aspect` | ✅ |
| **Workflow** | | |
| Task → recommend constraints → confirm → directions → select → mind map | 5 steps incl. "Recommend constraints to confirm" | ✅ |
| **Output** | | |
| Recommended constraints | `sections` → *Recommended constraints* | ✅ |
| Technical-solution mind map + evidence | *Solution mind map* + *Evidence pack* | ✅ |

---

## 2. IP

### 2.1 Novelty Search — Eureka *Novelty Search*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Invention disclosure (200–500 words) | `problem_text` | ✅ |
| Components | `ingredients` | ✅ |
| Process features | `process_desc` | ✅ |
| IPC/CPC expected classes | `ipc_codes` | ✅ |
| Jurisdictions | `target_markets` | ✅ |
| **Workflow** | | |
| Disclosure → **confirm extracted features F1..Fn (editable)** → multi-strategy search → compare feature-by-feature → structured comparison report | 5 steps; wizard has the **confirm-understanding** step that POSTs `extract-features` and lets the user add/edit features before the run | ✅ |
| Hybrid strategies: semantic, keyword×4, IPC/CPC, family/citation; RAG/RAT examiner-style retrieval | named strategies in trace + `strategy_groups` | ✅ |
| **Output** | | |
| Feature-by-feature verdicts | `sections` → *Extracted core technical features* + *Feature-by-feature verdicts* | ✅ |
| **Structured comparison report** (feature ↔ closest reference ↔ disclosure level ↔ evidence) | `sections` → *Prior-art search strategies* + *Structured comparison report* | ✅ |
| Novelty assessment (level + score + risks) | *Novelty assessment* | ✅ |
| Closest prior art + evidence | findings/evidence + sources rail | ✅ |

### 2.2 FTO (Hiro) — Eureka *FTO Search*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Product/technical solution | `problem_text` | ✅ |
| Concerned claim language | `proposed_claims` | ✅ |
| Components | `ingredients` | ✅ |
| Markets / authorities (USPTO/EPO/CNIPA etc.) | `target_markets` | ✅ |
| **Workflow** | | |
| Describe solution → **confirm extracted features** → "Confirm features & start search" → screening & search-strategy trace → element-wise claim chart (independent-first) → Create FTO report | 6 steps | ✅ |
| Multi-strategy search + transparent search path | *Build FTO search strategy (trace)* + *Keyword & terminology expansion* | ✅ |
| **Output** | | |
| High/Medium/Low risk buckets | `sections` → *FTO risk classification* | ✅ |
| **Element-wise claim chart** (claim language, product evidence, preliminary mapping Identified/Not identified/Uncertain, rationale, reviewer question) | *Element-wise claim chart (independent claims first)* | ✅ |
| Screening labels (include / exclude with reason / monitor / status uncertain) | *Candidate screening (status labels)* | ✅ |
| Structured product features + clarification flags | *Structured product features (confirm & edit)* | ✅ |
| Options + accountable review (redesign/monitor/licence/market timing) | *Options & accountable review* | ✅ |
| Search scope & strategy appendix | *FTO search scope & strategy appendix* | ✅ |

### 2.3 Design FTO — Eureka *Design FTO*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Design image | `image_path` (optional; offline build uses described design `problem_text`) | 🟡 |
| Product type | `product_type` | ✅ |
| Markets (jurisdiction) | `target_markets` | ✅ |
| **Workflow** | | |
| Image → patent-standard line drawings → image-db search → design-feature comparison → risk + design-arounds | 4 steps; image-to-line-drawings is inferred from the design text offline | 🟡 |
| **Output** | | |
| Per-match: similarity score, registration number, legal status, jurisdiction | *Similar-design register check* — honest placeholder rows ("to query — register lookup"), **no fabricated D-numbers**, caption states no design-register DB connected | ✅ (honest) |
| Design-arounds | *Design-around suggestions* | ✅ |
| Risk level | summary + finding | ✅ |

### 2.4 Patent Drafting — Eureka *Patent Drafting*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Invention description | `problem_text` | ✅ |
| Core elements | `ingredients` | ✅ |
| Process steps | `process_desc` | ✅ |
| Intended claims | `proposed_claims` (optional) | ✅ |
| Claim strategy steering (broad↔narrow) | `claim_strategy` (Broad / Balanced / Narrow) | ✅ |
| Auto vs Copilot mode | `mode` (Auto / Copilot) | ✅ |
| Filing jurisdiction (rule libraries) | `target_markets` (CGPDTM/USPTO/EPO/CNIPA/CIPO) | ✅ |
| **Workflow** | | |
| Upload invention description → extract key technical elements (terms map) → embedded prior-art search → plan outline & confirm essential features → claim tree (ind→dep) → specification → figures → **mandatory dual-track compliance review** → Word export | 9 steps | ✅ |
| **Output** | | |
| Editable **terms map** of key technical elements | `sections` → *Key technical elements (terms map)* | ✅ |
| **Embedded prior-art search** (family docs, citations, legal events, claim context) | `sections` → *Embedded prior-art search* | ✅ |
| Confirmed essential features + outline | `sections` → *Drafting outline & confirmed essential features* | ✅ |
| Claims tree (independent product/method/use + dependents, editable/reorderable) | `sections` → *Claims tree* | ✅ |
| Application map (jurisdiction template) | `sections` → *Application map* | ✅ |
| Figures + automatic reference-numeral labelling | `sections` → *Figures & reference numerals* | ✅ |
| **Compliance review — dual-track (semantic + deterministic): claim dependencies, antecedent basis, vague language, abstract word limit, prohibited wording, numbering** | `sections` → *Compliance review (mandatory dual-track)* — every check returns pass/warn/fail with detail | ✅ |
| Abstract with office word-limit compliance | compliance review row (≤150 USPTO / ≤250 other) + *Application map* abstract | ✅ |
| Word export | export step + note | 🟡 full .docx generation = export stub |

### 2.5 Invention Disclosure — Eureka *Invention Disclosure*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Raw idea / background + means + effects | `problem_text`, `formulation_text`, `improve_aspect` | ✅ |
| Inventors, filing intent | `inventors`, `filing_intent` | ✅ |
| **Workflow** | | |
| Structured questionnaire → extract technical features + inventive concept → 4-dimension interpretation panel (subject/application/mechanism/outcome) → regenerate & export | 5 steps incl. "Refine via the interpretation panel" | ✅ |
| **Output** | | |
| Who·What·Why questionnaire capture | `sections` → *Who · What · Why (structured questionnaire capture)* | ✅ |
| Interpretation panel (4 dimensions, editable) | *Interpretation panel (4 dimensions, editable)* | ✅ |
| Structured disclosure document | *Generated disclosure document* | ✅ |

### 2.6 Office Action Response — Eureka *Office Action Response*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Office action text | `office_action_text` | ✅ |
| Current claims | `proposed_claims` | ✅ |
| Invention context | `problem_text` | ✅ |
| Jurisdiction | `target_markets` | ✅ |
| **Workflow** | | |
| Parse → rejection analysis table → jurisdiction grounds (§101/102/103/112, Art 52–57/83–84, CNIPA 26.2/26.3/22/33) → ranked strategies → draft | 5 steps | ✅ |
| **Output** | | |
| Rejection analysis table | `sections` → *Rejection analysis table* | ✅ |
| Ranked response strategies | *Ranked response strategies* | ✅ |
| Draft response | findings + suggestions | 🟡 full filing-ready response = stub |

### 2.7 Essentiality Claim Chart — Eureka *Essentiality Claim Chart (AICC)*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Patent number | `patent_number` | ✅ |
| Standard documents (else auto-recommend) | `standard_name` | ✅ |
| Claim numbers | `proposed_claims` | ✅ |
| **Workflow** | | |
| Resolve patent → recommend TS/TR → recall sections → **per-claim-limitation AICC chart** → conclusion | 5 steps | ✅ |
| **Output** | | |
| Limitation-level AICC | `sections` → *Limitation-level essentiality claim chart* | ✅ |
| Essentiality conclusion | *Essentiality conclusion* | ✅ |

### 2.8 tDoc Novelty Search — Eureka *tDoc Novelty Search*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Disclosure / patent number | `disclosure_text` | ✅ |
| Title/summary | `problem_text` | ✅ |
| Jurisdictions | `target_markets` | ✅ |
| **Workflow** | | |
| Ingest → index TDoc corpus → run novelty → surface overlaps → compile | 5 steps; shares novelty executor with TDoc corpus routing | ✅ |
| **Output** | | |
| Similarity assessment vs TDoc-type corpus | same report shape as novelty + sources rail | ✅ |

---

## 3. Life Sciences

### 3.1 Document Analyzer — Eureka *Document Analyzer*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Document text | `document_text` | ✅ |
| Document type | `document_kind` (CoA/Monograph/Patent/Lab/Label/Gazette) | ✅ |
| Jurisdiction | `target_markets` | ✅ |
| **Workflow** | | |
| Ingest → exec summary → tables/figures/entities → export → table/figure tools → Q&A | 6 steps | ✅ |
| **Output** | | |
| Executive summary | `sections` → *Executive summary* | ✅ |
| Extracted biomedical entities | *Extracted biomedical entities* (drugs/targets/diseases/orgs) | ✅ |
| Table & figure tools + Q&A | *Document tools* + findings | 🟡 Q&A is canned |

### 3.2 LCA Biotherapeutic — Eureka *Lead Compound – Biotherapeutic (Synapse)*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Patent / biologic target / candidate space | `problem_text` | ✅ |
| Sequences (H/L chains, CDRs) | `sequences` | ✅ |
| Claims focus | `proposed_claims` | ✅ |
| **Workflow** | | |
| Ingest (large files) → OCSR → NER/normalise → sequence compare + epitope → scope/legal → developability | 7 steps | ✅ |
| **Output** | | |
| Top-5 core patents | `sections` → *Top core patents* | ✅ |
| 5–10 optimal molecules (FASTA/SDF-ready) | *Optimal molecules* | ✅ |

### 3.3 LCA Small Molecule — Eureka *Lead Compound – Small Molecule (Synapse)*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Compounds / patent | `compound_desc` | ✅ |
| Goal | `problem_text` | ✅ |
| Markets | `target_markets` | ✅ |
| **Workflow** | | |
| Ingest → OCSR → assay NER → **Lipinski developability** → rank leads → landscape/FTO pass | 6 steps | ✅ |
| **Output** | | |
| Lipinski scores (MW, LogP, HBD/HBA) | `sections` → *Developability (Lipinski)* | ✅ |
| Ranked leads + SMILES | *Optimal molecules* (SMILES included) | ✅ |

### 3.4 SAR Data Extraction — Eureka *SAR Data Extraction (Synapse)*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Structures + activities (or patent ref) | `compound_desc` | ✅ |
| Activity metric | `activity_metric` (IC50/EC50/%inhibition/MIC/Potency) | ✅ |
| **Workflow** | | |
| Extract structure+experiment records → standardise to SMILES → **human validate (Value/Structure Source, Structure Match)** → export CSV/Excel/SDF | 5 steps | ✅ |
| **Output** | | |
| SAR record set (Eureka column schema) | `sections` → *SAR records* (structure, target, subject, method, purpose, endpoint, value, unit, dosing, SMILES) | ✅ |
| Analysis views + cliff comparison | *Analysis views* | ✅ |

### 3.5 Antibody Target Prediction — Eureka *Target Prediction*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Antibody / target | `antibody_desc` | ✅ |
| CDR sequences | `sequences` | ✅ |
| Use case | `problem_text` | ✅ |
| **Workflow** | | |
| Normalise → curated R&D + BLAST → affinity cross-check → predict → ranked shortlist | 5 steps | ✅ |
| **Output** | | |
| Ranked prediction card w/ scores | `sections` → *Predicted target* + ranked shortlist | ✅ |

### 3.6 Markush Drafting — Eureka *Markush or Matter*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Core structure (scaffold) | `core_structure` | ✅ |
| Substituent ranges (R-groups) | `variant_features` | ✅ |
| Coverage intent | `scope_intent` (Broad/Balanced/Narrow) | ✅ |
| **Workflow** | | |
| Parse MOL/CDX/SDF → scaffold + attachment points → Markush scaffold + R-groups → edit (dependent claims update live) → claim set export | 5 steps; offline build parses textual scaffold instead of MOL files | 🟡 |
| **Output** | | |
| Markush scaffold + coverable/not listing | `sections` → *Markush structure* | ✅ |
| Word/SDF export | export stub | 🟡 |

---

## 4. Materials

### 4.1 Formulation — Eureka *Formulation (Filot-like)*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Formulation objective/constraint | `problem_text` | ✅ |
| Ingredients (or reformulation brief) | `ingredients` | ✅ |
| Process/extraction | `process_desc` | ✅ |
| Solvent preference | `solvent_pref` (decoction/hydroalcoholic/honey/ghrita/milk/asava) | ✅ |
| Markets | `target_markets` | ✅ |
| Target claims | `proposed_claims` | ✅ |
| **Workflow** | | |
| Brief → nomenclature (INCI) → evidence index → functional categories → screen + ranges → **benchmarked candidates (2 per dimension)** → risk check → table | 7 steps | ✅ |
| **Output** | | |
| Benchmark: 2 formulations per dimension w/ sources | `sections` → *Benchmarked formulation candidates* (source = real corpus ref via `_real_ref`, **no fabricated patents**) | ✅ |
| Formulation table + risk check | *Formulation table*, *Risk check* | ✅ |

### 4.2 Materials Find Solutions — Eureka *Materials Find Solutions*
| Eureka | Our build | Status |
|---|---|---|
| **Inputs** | | |
| Material challenge + performance target | `material_challenge` | ✅ |
| Current material | `current_material` | ✅ |
| Target property | `performance_target` (moisture/flow/compressibility/cost/regulatory/taste) | ✅ |
| **Workflow** | | |
| Task → recommend directions → confirm → thinking chain → **mind map** → per-node evidence pack → deep-dive implementation plan | 7 steps | ✅ |
| **Output** | | |
| Recommended directions | `sections` → *Recommended solution directions* | ✅ |
| Mind map nodes + per-node evidence (maturity, reliability, industry cases, challenges) | *Mind map nodes* + *Evidence pack* | ✅ |

---

## Global run-everything checks

| Check | Verification | Status |
|---|---|---|
| Every agent answers with `ok=True`, sections + data sources | 19/19 agent sweep, plus live HTTP run (`formulation` → 4 sections) | ✅ |
| Confirm-understanding step feeds confirmed features into the run | TRIZ run: `execution.validated = "User confirmed 2 extracted feature(s) before this run"` | ✅ |
| Unknown/gap → says "gap reported, not guessed" | fallback path in `agent_executors.py` | ✅ |
| No fabricated patent/registration numbers anywhere | formulation ✅ design-FTO ✅ (register rows = honest placeholders) | ✅ |
| Same workflow shown in wizard sidebar, run trace and orchestrator | single source `agent_workflows.py` | ✅ |

## Known honest gaps (need real Eureka access / data, not code)
1. Eureka searches **200M+ live patents** and premium literature/sequence/chemical databases. Our offline build searches a local patent/PubMed/regulatory corpus and labels each answer's real sources in the *Data sources* rail.
2. Image-processing agents (Design FTO line drawings, Markush MOL/CDX/SDF parsing, LCA OCSR from images) derive from **textual descriptions** in this build — enable an upload+OCR/OCSR pipeline to close.
3. File-export stubs (Word draft, CSV/SDF/Excel) are surfaced but not fully generated offline.