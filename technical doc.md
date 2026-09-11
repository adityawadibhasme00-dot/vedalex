# IP-SAKTI Sahayak — Comprehensive Technical Documentation

> **Theme**: *"IP-SAKTI Sahayak — A multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes."*

---

## 1. Architectural Foundations

IP-SAKTI Sahayak is engineered as a high-reliability, citation-grounded decision-support system. It prevents hallucinations by decoupling legal logic from language models.

### System Invariant Flow:
1. **Intake & Canonicalization**: Converts raw multilingual user inputs into typed, canonical botanical records.
2. **Deterministic Evaluation**: Evaluates versioned rule packs across jurisdictions with strict 3-state output (`condition_satisfied`, `not_satisfied`, `insufficient_information`).
3. **Hybrid RAG Retrieval**: Fetches primary statutory gazettes and monograph passages based on a strict authority hierarchy.
4. **Citation & Evidence Validation**: Enforces the Unsupported Claim Rate (UCR) gate.
5. **Grounded Explanation Generation**: Uses the LLM strictly to synthesize explanations referencing exact section passages.

---

## 2. Botanical Canonicalization & Formulation Fingerprinting (Section 7.2.1)

```
+-----------------------------------------------------------------------------------------------+
|                            CANONICAL RESOLUTION ALGORITHM                                     |
|                                                                                               |
|  [ User Multilingual Input: "अश्वगंधा" / "Amukkara" / "Withania somnifera" ]                 |
|                               │                                                               |
|                               ▼                                                               |
|              [ Normalizer & Transliteration Tokenizer ]                                       |
|                               │                                                               |
|                               ▼                                                               |
|       [ Botanical Synonym Trie & Levenshtein / Exact Matcher ]                                |
|                               │                                                               |
|            ┌──────────────────┴──────────────────┐                                            |
|            ▼                                     ▼                                            |
|  [ Match Confidence >= 0.85 ]           [ Match Confidence < 0.85 ]                           |
|            │                                     │                                            |
|            ▼                                     ▼                                            |
|  [ Canonical Botanical Record ]         [ Candidate Matches, None Confirmed ]                 |
|  - API Monograph ID: `API-VOL1-008`     - Triggers user clarification query                   |
|  - Botanical: *Withania somnifera*      - Holds rule evaluation in `insufficient_information` |
|  - Family: Solanaceae                                                                         |
+-----------------------------------------------------------------------------------------------+
```

### Formulation Fingerprint Vector:
A fingerprint $F$ is mathematically defined as:
$$F = \left\{ (I_1, R_1, P_1, S_1), (I_2, R_2, P_2, S_2), \dots, (I_n, R_n, P_n, S_n) \right\}$$
where:
- $I_k$: Canonical Botanical API ID (e.g. `API-VOL1-008`).
- $R_k$: Quantitative ratio percentage ($\sum R_k = 100\%$).
- $P_k$: Plant part utilized (`Root`, `Whole Plant`, `Leaf`, `Bark`).
- $S_k$: Extraction solvent / process (`Aqueous`, `Hydroalcoholic`, `Choorna`, `Taila`).

---

## 3. Deterministic 3-State Rule Evaluation Engine

The rule engine processes versioned YAML rule trees. Each rule specifies:
- **Premises / Conditions**: List of boolean expressions evaluated against passport facts.
- **Statutory Authority Reference**: Gazette section and effective date.
- **Action Precedence**: Explicit dependency ordering (e.g. Classification must resolve before Action Checklist generation).

```python
def evaluate_rule_condition(condition: RuleCondition, passport: InnovationPassport) -> ConditionResult:
    # 1. Check if required fact is present
    fact_value = passport.get_fact_value(condition.fact_key)
    if fact_value is None or fact_value.status == FactOrigin.UNKNOWN:
        return ConditionResult(
            state=RuleConditionState.INSUFFICIENT_INFO,
            missing_fact=condition.fact_key,
            remedy_prompt=condition.clarification_prompt
        )
    
    # 2. Evaluate deterministic predicate
    is_match = condition.predicate.evaluate(fact_value.value)
    if is_match:
        return ConditionResult(state=RuleConditionState.SATISFIED)
    else:
        return ConditionResult(state=RuleConditionState.NOT_SATISFIED)
```

---

## 4. Citation & Evidence Validator (UCR Gate)

The **Unsupported Claim Rate (UCR)** is defined as:
$$\text{UCR} = \frac{N_{\text{unsupported statements}}}{N_{\text{total atomic statements generated}}}$$

### Gate Invariants:
- If $\text{UCR} > 0.05$ ($5\%$), the explanation is automatically rejected and regenerated with higher passage temperature clamping.
- If primary statutory passage is missing from the knowledge base, the system transitions finding to `INSUFFICIENT_EVIDENCE` and suppresses legal conclusions.

### Claim-Level Verification Layer (Level 2/3 Guard)

Beyond UCR, the verification layer decomposes each generated answer into
atomic claims and verifies each claim independently against retrieved evidence.

**Pipeline** (`app/rag/verification_orchestrator.py`):

```
Draft Answer
    ↓
Claim Extraction (claim_extractor.py)
    ↓
Citation Validity Check (citation_validity_checker.py)
    ↓
Per-Claim Semantic Entailment (semantic_entailment.py + claim_verifier.py)
    ↓
Evidence Confidence Scoring (evidence_confidence_scorer.py)
    ↓
Confidence Gate
  /            \
PASS           FAIL
  ↓              ↓
Final Answer   Regenerate (strip unsupported) or Refuse
```

**Per-claim verdicts**: each claim is marked `SUPPORTED`, `CONTRADICTED`,
or `NOT_ENOUGH` based on embedding similarity (BGE-M3 cosine), keyword
coverage, negation-polarity agreement, and contradiction-signal detection.

**Evidence Confidence** is the weighted composite of six signals:

| Signal | Weight |
|---|---|
| Retrieval coverage | 0.20 |
| Citation validity | 0.15 |
| Claim evidence support (entailment ratio) | 0.30 |
| Source authority | 0.15 |
| Source diversity | 0.10 |
| Rule-engine validation | 0.10 |

The gate fails when `support_ratio < 0.50`, any claim is `CONTRADICTED`,
citation validity `< 0.50`, or overall confidence `< 0.35`. Unsupported
claims are then removed (regeneration); if nothing survives, the system
abstains rather than hallucinate.

---

## 5. Adversarial Input Sandboxing & Instruction Stripping

Uploaded certificates, PDFs, and scanned labels are processed through an isolated regex sanitization pipeline:

```python
ADVERSARIAL_INSTRUCTION_PATTERNS = [
    r"(?i)\b(?:ignore|forget|disregard|override)\s+(?:all\s+)?(?:previous|prior|system)\s+instructions\b",
    r"(?i)\b(?:you\s+are\s+now|act\s+as|roleplay\s+as|system\s+prompt)\b",
    r"(?i)\b(?:mark|declare|certify|state)\s+this\s+(?:as\s+)?(?:patentable|compliant|approved|safe)\b",
    r"(?i)\b(?:bypass|skip)\s+(?:all\s+)?(?:checks|evaluations|filters|rules)\b"
]

def sanitize_document_text(raw_text: str) -> SanitizedResult:
    threats_detected = []
    sanitized = raw_text
    for pattern in ADVERSARIAL_INSTRUCTION_PATTERNS:
        matches = re.findall(pattern, sanitized)
        if matches:
            threats_detected.extend(matches)
            sanitized = re.sub(pattern, "[STRIPPED_POTENTIAL_INJECTION]", sanitized)
    return SanitizedResult(
        cleaned_text=sanitized,
        threats_logged=threats_detected,
        is_suspicious=len(threats_detected) > 0
    )
```

---

## 6. Evaluation Framework & Benchmark Runner (Section 12)

The backend includes an automated evaluation runner executing against 30+ gold cases across English, Hindi, and Marathi:
- **Retrieval Recall@K & Precision@K**.
- **Jurisdiction & Classification Accuracy** ($> 98\%$).
- **Unsupported Claim Rate (UCR)** ($< 1.5\%$).
- **Language-Parity Gap**:
  $$|\text{Accuracy}_{\text{Hindi}} - \text{Accuracy}_{\text{English}}| \le 0.03$$
  $$|\text{Accuracy}_{\text{Marathi}} - \text{Accuracy}_{\text{English}}| \le 0.03$$
