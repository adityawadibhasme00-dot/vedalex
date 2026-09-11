# IP-SAKTI Sahayak — REST & OpenAPI Specification (v1)

> **Theme**: *"IP-SAKTI Sahayak — A multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes."*

---

## 1. Base URL & Protocol

- **Base URL**: `http://localhost:8000/api/v1`
- **Protocol**: HTTPS / REST JSON
- **Headers**:
  - `Content-Type: application/json`
  - `Accept-Language: en | hi | mr | ta | te | kn | bn | gu | ml | sa`
  - `X-Session-ID: <UUID>`

---

## 2. API Endpoints Overview

### 2.1 Innovation Passport Endpoints
- `POST /passport/create` — Create or intake a new Innovation Passport from raw text/voice transcript.
- `GET /passport/{id}` — Retrieve a versioned Innovation Passport.
- `PUT /passport/{id}/update` — Update passport facts, resolve clarification questions.
- `POST /passport/sanitize-document` — Sandboxed upload and prompt-injection defense for PDFs/labels.

### 2.2 Decision & Assessment Endpoints
- `POST /assessment/evaluate` — Run deterministic multi-jurisdiction evaluation across India, US, and Canada.
- `POST /screening/ip-tk` — Run Section 3(p) Traditional Knowledge prior-art screening and formulation fingerprint comparison.
- `GET /assessment/{id}/provenance` — Retrieve the full "Why?" provenance graph (Facts $\to$ Rules $\to$ Gazette Citations $\to$ Findings).

### 2.3 Interactive Decision-Support Endpoints
- `POST /what-if/simulate` — Clone passport, apply a single fact mutation, and return the reactive diff.
- `POST /red-team/challenge` — Generate 2–3 examiner-style objections ("Challenge My Innovation").
- `GET /evidence/{passport_id}` — Retrieve dependency-ordered action checklist and Coverage Meter.
- `PUT /evidence/{item_id}/lifecycle` — Update evidence status (`Missing` $\to$ `Uploaded` $\to$ `Needs Review` $\to$ `Accepted`).

### 2.4 Ecosystem, Notification & Institutional Endpoints
- `GET /regulatory-diff/updates` — Retrieve active gazette amendments and affected user case IDs.
- `POST /expert-handoff/dispatch` — Opt-in escalation to certified patent agent / AYUSH expert with DPDP consent.
- `GET /institutional/cohort-analytics` — Multi-tenant incubator case queue and common evidence gap statistics.
- `POST /evals/run-benchmark` — Execute the gold-case benchmark suite and return UCR and language parity metrics.

---

## 3. Detailed Request & Response Contracts

### 3.1 `POST /assessment/evaluate`
**Request Body**:
```json
{
  "passport_id": "8f3b2a1c-99d4-4e78-9e12-3456789abcde",
  "target_markets": ["India", "United States", "Canada"],
  "language": "mr"
}
```

**Response Body (200 OK)**:
```json
{
  "assessment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "passport_id": "8f3b2a1c-99d4-4e78-9e12-3456789abcde",
  "timestamp": "2026-09-06T19:00:00Z",
  "findings": [
    {
      "jurisdiction": "India",
      "pathway_category": "Ayurveda Aahara (FSSAI 2022) / Classical ASU (Ayush)",
      "status": "condition_satisfied",
      "confidence": "HIGH",
      "conditions_evaluated": [
        "Ingredients listed in Ayurvedic Pharmacopoeia of India (API)",
        "Dosage conforms to classical formulation thresholds",
        "Claim does not state cure or treatment of disease"
      ],
      "supporting_citations": [
        {
          "act_title": "Food Safety and Standards (Ayurveda Aahara) Regulations, 2022",
          "section_reference": "Regulation 4(1) & Schedule I",
          "authority": "FSSAI / Ministry of AYUSH",
          "effective_date": "2022-05-05",
          "exact_passage": "Ayurveda Aahara shall not include Ayurvedic drugs listed under the First Schedule to the Drugs and Cosmetics Act, 1940 unless intended solely for food purposes without disease cure claims.",
          "authority_rank": 1
        }
      ],
      "missing_facts": ["Heavy metal test lab report", "Aqueous extraction certificate"],
      "next_action_steps": [
        "Obtain FSSAI Central License under Ayurveda Aahara category",
        "Submit botanical authentication certificate for Bacopa monnieri"
      ],
      "coverage_limitations": "Evaluated against current FSSAI 2022 gazette; does not substitute for state licensing inspection."
    },
    {
      "jurisdiction": "United States",
      "pathway_category": "Dietary Supplement (DSHEA)",
      "status": "condition_satisfied",
      "confidence": "HIGH",
      "conditions_evaluated": [
        "Botanical dietary ingredient used prior to Oct 15, 1994 (Old Dietary Ingredient)",
        "Proposed claim 'supports healthy sleep' conforms to structure/function criteria"
      ],
      "supporting_citations": [
        {
          "act_title": "Dietary Supplement Health and Education Act of 1994 (DSHEA)",
          "section_reference": "21 U.S.C. 343(r)(6) & 21 CFR 101.93",
          "authority": "US Food and Drug Administration (FDA)",
          "effective_date": "1994-10-25",
          "exact_passage": "A dietary supplement may bear a statement if it describes the role of a nutrient intended to affect the structure or function in humans, provided the manufacturer has substantiation and includes mandatory FDA disclaimer.",
          "authority_rank": 1
        }
      ],
      "missing_facts": ["30-day post-market notification draft"],
      "next_action_steps": [
        "Include mandatory FDA disclaimer on principal display panel",
        "Submit 30-day structure/function claim notification to FDA post-launch"
      ],
      "coverage_limitations": "Assumes conventional dietary supplement form (capsule/tablet); not applicable for intravenous or injectable delivery."
    },
    {
      "jurisdiction": "Canada",
      "pathway_category": "Natural Health Product (NHP)",
      "status": "condition_satisfied",
      "confidence": "HIGH",
      "conditions_evaluated": [
        "Ashwagandha and Brahmi present in NHPID Monograph list",
        "Daily dosage within permitted NHP limits (Withania somnifera < 6000mg dried equivalent)"
      ],
      "supporting_citations": [
        {
          "act_title": "Natural Health Products Regulations (NHPR)",
          "section_reference": "SOR/2003-196 Part 1 & NHPID Monograph",
          "authority": "Health Canada",
          "effective_date": "2004-01-01",
          "exact_passage": "Every natural health product must have a product licence (NPN) before it can be sold in Canada. Formulations conforming to published monographs qualify for expedited Class I review.",
          "authority_rank": 1
        }
      ],
      "missing_facts": ["Foreign Site License Annex for Indian manufacturing facility"],
      "next_action_steps": [
        "Apply for 8-digit Natural Product Number (NPN) via Class I monograph pathway",
        "Audit manufacturing partner for Health Canada GMP Site License equivalence"
      ],
      "coverage_limitations": "Product licensing and Site licensing are distinct requirements under Health Canada."
    }
  ],
  "coverage_meter_score": 82
}
```

---

### 3.2 `POST /what-if/simulate`
**Request Body**:
```json
{
  "passport_id": "8f3b2a1c-99d4-4e78-9e12-3456789abcde",
  "mutations": {
    "proposed_claims": ["Treats chronic insomnia and reverses anxiety disorders"]
  }
}
```

**Response Body (200 OK)**:
```json
{
  "original_claim": "Supports healthy sleep",
  "mutated_claim": "Treats chronic insomnia and reverses anxiety disorders",
  "affected_nodes_count": 3,
  "diffs": [
    {
      "jurisdiction": "United States",
      "prior_classification": "Dietary Supplement (DSHEA)",
      "new_classification": "Unapproved New Drug (21 U.S.C. 321(g))",
      "impact_severity": "CRITICAL_BURDEN_INCREASE",
      "risk_alert": "Disease treatment claims trigger mandatory FDA New Drug Application (NDA) and clinical trial requirements.",
      "removed_requirements": ["DSHEA 30-day structure/function notification"],
      "new_requirements": ["Investigational New Drug (IND) filing", "Phase I-III clinical trial dossier"],
      "new_citations": [
        {
          "act_title": "Federal Food, Drug, and Cosmetic Act (FD&C Act)",
          "section_reference": "21 U.S.C. 321(g)(1)(B)",
          "authority": "US FDA",
          "effective_date": "1938-06-25",
          "exact_passage": "Articles intended for use in the diagnosis, cure, mitigation, treatment, or prevention of disease in man or other animals are drugs.",
          "authority_rank": 1
        }
      ]
    },
    {
      "jurisdiction": "India",
      "prior_classification": "Ayurveda Aahara (Food)",
      "new_classification": "ASU Proprietary Medicine (Drug) under Rule 158-B",
      "impact_severity": "HIGH_BURDEN_INCREASE",
      "risk_alert": "Disease treatment claim disqualifies product from FSSAI Ayurveda Aahara food category; must obtain State AYUSH Drug License.",
      "new_requirements": ["State AYUSH Drug Manufacturing License", "Rule 158-B Safety & Pilot Clinical Trial Data"]
    }
  ]
}
```
