# IP-SAKTI Sahayak — Product Requirements Document (PRD)

> **Theme**: *"IP-SAKTI Sahayak — A multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes."*

---

## 1. Product Overview

IP-SAKTI Sahayak is an intelligent, multilingual decision-support platform designed to solve the critical "Access to Action" gap in the Ayurveda sector. It empowers researchers, MSMEs, startups, and incubators to navigate:
1. **Intellectual Property & Traditional Knowledge**: Patentability screening under Indian Patents Act Section 3(p) and WIPO standards.
2. **Multi-Jurisdiction Regulatory Pathways**: ASU Classical vs Proprietary Drug (India), Ayurveda Aahara Food (FSSAI), Dietary Supplement vs New Drug (US FDA DSHEA), and Natural Health Products (Health Canada NHPR).
3. **Biological Diversity Compliance**: Biological Diversity Act (BDA) and Access and Benefit Sharing (ABS) mandates.

---

## 2. Target User Personas & Pain-Point Mapping

| User Persona | Core Goal | Critical Pain Point Solved |
| :--- | :--- | :--- |
| **Early-Stage Innovator** | Understand if formulation is patentable or "just TK in disguise" | Canonical botanical screening against Section 3(p) prior art with clear difference analysis. |
| **Ayurveda MSME / Startup** | Identify fastest regulatory pathway to market in India | Deterministic classification between ASU Drug and FSSAI Ayurveda Aahara. |
| **Export-Oriented Brand** | Commercialize formulation in US & Canada | Side-by-side regulatory comparison matrix with per-ingredient legality checks (FDA NDI / NHPID). |
| **Academic Researcher** | Validate novelty of herbal extract modification | Evidence-gap checklist and examiner objection simulation before publishing or filing. |
| **Incubator / IP Cell** | Efficiently triage 50+ startup cases | Multi-tenant case queue, reviewer assignment, and aggregate cohort gap analytics. |
| **Regional-Language User** | Access legal guidance in native language | Native multilingual intake and citation-grounded output in Hindi, Marathi, Tamil, Telugu, etc. |

---

## 3. Detailed Functional Requirements

### FR-1: Guided Innovation Passport Intake
- **FR-1.1**: Support structured intake of dosage form, intended use, plant parts, extraction solvent, botanical binomials, proposed claims, target markets, and business role.
- **FR-1.2**: Assign origin status to every fact: `user_confirmed`, `document_extracted`, `inferred`, `unknown`.
- **FR-1.3**: Trigger proactive follow-up clarification questions when missing facts alter legal outcomes.

### FR-2: Canonical Botanical Resolver & Formulation Fingerprinting
- **FR-2.1**: Map vernacular/Sanskrit names (e.g. *Ashwagandha*, *Asgandh*, *Amukkara*) to Ayurvedic Pharmacopoeia of India (API) monographs and botanical binomials (*Withania somnifera*).
- **FR-2.2**: Compute formulation fingerprints based on ingredient ratios and solvent processes.

### FR-3: Deterministic Rule Engine & Multi-Jurisdiction Pathways
- **FR-3.1**: Evaluate India ASU Drug rules (Drugs & Cosmetics Act 1940) and FSSAI Ayurveda Aahara Regulations 2022.
- **FR-3.2**: Evaluate US FDA DSHEA (21 CFR 101.93) structure/function vs disease claims.
- **FR-3.3**: Evaluate Health Canada NHPR Product Licensing vs Site Licensing.
- **FR-3.4**: Enforce strict 3-state evaluation (`condition_satisfied`, `not_satisfied`, `insufficient_information`).

### FR-4: Hybrid RAG & Strict Citation Validation
- **FR-4.1**: Hybrid BM25 lexical and dense multilingual semantic retrieval over statutory gazettes.
- **FR-4.2**: Enforce Unsupported Claim Rate (UCR) gate; reject or abstain if claims lack direct statutory passage support.
- **FR-4.3**: Surface 4 calibrated confidence bands (`High`, `Medium`, `Low`, `Insufficient Evidence`).

### FR-5: Reactive What-If Simulator
- **FR-5.1**: Provide live mutation editor for claim text and ingredient ratios.
- **FR-5.2**: Recompute only affected rule nodes and render instant side-by-side diffs.

### FR-6: "Challenge My Innovation" Red-Team Examiner Simulator
- **FR-6.1**: Surface 2–3 examiner-style patent/regulatory objections under Section 3(p) TK and safety guidelines.

### FR-7: Traceable Decision Workspace ("Why?" Provenance View)
- **FR-7.1**: Render interactive decision path: *User Fact $\to$ Rule $\to$ Condition $\to$ Gazette Passage $\to$ Finding*.
- **FR-7.2**: Make every citation clickable to reveal exact gazette excerpt and effective date.

### FR-8: Living Regulatory-Diff & Notification Service
- **FR-8.1**: Monitor statutory gazette amendments and identify affected saved user cases.

### FR-9: Expert Handoff Bridge
- **FR-9.1**: Route complex cases to certified patent agents or AYUSH consultants with DPDP consent and liability boundary.

### FR-10: Institutional Multi-Tenancy
- **FR-10.1**: Provide incubator cohort dashboards, reviewer triage queues, and aggregate compliance analytics.

---

## 4. Non-Functional Requirements

- **Latency**: p95 $<12\text{s}$ for cached public queries, $<45\text{s}$ for fresh cross-jurisdiction RAG.
- **Security**: Prompt injection stripping for all document uploads; DPDP Act 2023 compliance; zero API keys in client code.
- **Multilingual Parity**: Classification and citation accuracy within $5\%$ tolerance across English, Hindi, and Marathi.
- **Accessibility & Offline**: High-contrast WCAG 2.1 AA compliant UI; local draft caching in offline mode.
