# IP-SAKTI Sahayak — Technical Specifications & Engineering Deep Dive

> **Theme**: *"IP-SAKTI Sahayak — A multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes."*

---

## 1. Technology Stack Summary

| Layer | Selected Technology | Technical Rationale & Specification |
| :--- | :--- | :--- |
| **Frontend Framework** | Next.js 14 / React 18 + TypeScript | Server/Client components, reactive DAG rendering, streaming responses, type safety |
| **Frontend Styling** | Modern CSS + Tailwind CSS | Glassmorphic design system, responsive grids, dark/light theme, accessible high-contrast chips |
| **Backend Framework** | FastAPI (Python 3.11) + Pydantic v2 | High-throughput asynchronous I/O, strict JSON schema validation, native Python AI ecosystem |
| **Data & Persistence** | PostgreSQL / Structured Relational | Pydantic relational schemas for passports, versioned rules, citations, and evaluation logs |
| **Lexical Retrieval** | BM25 / PostgreSQL Full-Text | Exact section matches, botanical binomials, legal statute identifiers |
| **Dense Retrieval** | Multilingual Embeddings + pgvector | Semantic match across English and Indic regional languages (Hindi, Marathi, Tamil, etc.) |
| **Rule Engine** | YAML Versioned Rule Packs + AST Evaluator | Auditable, deterministic, zero-hallucination condition evaluation (Satisfied / Not / Insufficient) |
| **Security & Privacy** | Sandboxed Regex Sanitizer + DPDP Logger | Strips prompt injections from uploads; logs consent records and data localization boundaries |
| **Package Management** | `npm` (Frontend), `pip` (Backend) | Clean dependency isolation; zero client-side secret exposure |

---

## 2. Performance SLOs & Cost/Latency Budgets (Section 7.2.3)

To ensure the system meets production standards, concrete numeric latency and token budgets are enforced:

```
+-------------------------------------------------------------------------------+
|                            PRODUCTION SLO BUDGETS                             |
+------------------------------------+------------------------------------------+
| Metric                             | Production Target                        |
+------------------------------------+------------------------------------------+
| p95 Latency (Cached Public Corpus) | < 12 seconds                             |
| p95 Latency (Fresh 3-Country RAG)  | < 45 seconds                             |
| p50 Assessment Latency             | < 4.5 seconds                            |
| Max Token Ceiling (Extraction)     | 1,200 tokens                             |
| Max Token Ceiling (Retrieval Rank) | 2,500 tokens                             |
| Max Token Ceiling (Explanation)    | 1,800 tokens                             |
| Target Cache-Hit Rate (Public RAG) | >= 85%                                   |
| Private Formulation Caching        | STRICTLY 0% (Never entered shared cache) |
+------------------------------------+------------------------------------------+
```

### Tiered Model Routing Architecture:
- **Tier 1 (Fast / Deterministic)**: Python regex + YAML rule engine for classification, canonical botanical resolution, and condition evaluation ($0$ token cost, $<10$ ms latency).
- **Tier 2 (Structured Extraction & Sanitization)**: Lightweight LLM adapter / typed regex parser for OCR document ingestion ($<500$ ms).
- **Tier 3 (Grounded Explanation Generation)**: Reasoning LLM with strict passage grounding to synthesize human-readable multilingual explanations with inline statutory citations.

---

## 3. Core Data Schemas

### 3.1 Innovation Passport Model
```python
class FactOrigin(str, Enum):
    USER_CONFIRMED = "user_confirmed"
    DOCUMENT_EXTRACTED = "document_extracted"
    INFERRED = "inferred"
    UNKNOWN = "unknown"

class IngredientFact(BaseModel):
    common_name: str
    botanical_name: Optional[str] = None
    api_monograph_id: Optional[str] = None
    plant_part: str
    preparation_method: str  # e.g., "Aqueous extract", "Hydroalcoholic", "Svarasa"
    quantity_percentage: float
    source_country: str = "India"
    origin_status: FactOrigin = FactOrigin.USER_CONFIRMED

class InnovationPassport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_title: str
    product_form: str  # Tablet, Vati, Kwatha, Taila, Capsule, Powder
    dosage_form: str
    intended_use: str
    proposed_claims: List[str]
    claimed_innovation: str  # Novel synergistic ratio, modified process, new indication
    process_description: str
    ingredients: List[IngredientFact]
    manufacturing_location: str = "India"
    target_markets: List[str] = ["India", "United States", "Canada"]
    business_role: str = "Manufacturer"  # Innovator, Startup, MSME, Researcher
    biological_resource_origin: str = "Domestic (India)"
    existing_ip_status: str = "None"
    version: int = 1
    unresolved_clarifications: List[str] = []
```

### 3.2 Finding & Citation Provenance Model
```python
class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class RuleConditionState(str, Enum):
    SATISFIED = "condition_satisfied"
    NOT_SATISFIED = "condition_not_satisfied"
    INSUFFICIENT_INFO = "insufficient_information"

class StatutoryCitation(BaseModel):
    act_title: str          # e.g., "Drugs & Cosmetics Act, 1940 & Rules 1945"
    section_reference: str  # e.g., "Rule 158-B / Schedule T"
    authority: str          # "Ministry of AYUSH", "FSSAI", "US FDA", "Health Canada"
    effective_date: str     # "1945-12-21 (amended 2022)"
    exact_passage: str      # Exact gazette excerpt
    source_url: Optional[str] = None
    authority_rank: int     # 1 = Gazette/Act, 2 = Regulatory Agency, 3 = Guidelines

class RegulatoryFinding(BaseModel):
    jurisdiction: str       # "India", "United States", "Canada"
    pathway_category: str   # "Ayurveda Aahara", "ASU Classical", "DSHEA Supplement", "NHP"
    status: RuleConditionState
    confidence: ConfidenceBand
    conditions_evaluated: List[str]
    supporting_citations: List[StatutoryCitation]
    missing_facts: List[str]
    next_action_steps: List[str]
    coverage_limitations: str
    assumptions_made: List[str]
```

---

## 4. Deterministic Rule Packs & Logic Invariants

### 4.1 India Regulatory Pathway Partitioning
- **ASU Classical Drug**: Composition strictly conforms to texts listed in the First Schedule of Drugs & Cosmetics Act, 1940.
- **ASU Proprietary Medicine**: Contains ingredients mentioned in classical texts but formulated in innovative combinations/dosage forms; requires Rule 158-B safety/efficacy documentation.
- **Ayurveda Aahara (FSSAI 2022)**: Food items prepared in accordance with Ayurvedic texts for dietary use; prohibited from making disease treatment or cure claims.

### 4.2 US FDA DSHEA Pathway Partitioning
- **Dietary Supplement (21 CFR 101.93)**: Permitted structure/function claims (e.g., *"Helps maintain restful sleep"*); mandatory FDA disclaimer; mandatory 30-day post-market notification.
- **Unapproved New Drug (21 U.S.C. 321(g))**: Triggered if claim states *"Treats, cures, prevents, or mitigates disease"* (e.g., *"Treats insomnia"*); requires Investigational New Drug (IND) and NDA approval.

### 4.3 Health Canada Natural Health Products (NHPR)
- **Natural Health Product (Class I/II/III NPN)**: Requires Natural Product Number (NPN); distinct Product Licensing from Site Licensing (foreign site annex required for imports).

---

## 5. Adversarial Input Sandboxing & Defense (Section 7.1.2)

1. **Extraction Sandbox**: Text extracted from uploaded certificates, PDFs, and lab reports passes through a strict Pydantic parsing layer.
2. **Regex Instruction Stripping**: Strips patterns matching:
   - `/(?:ignore|forget|override)\s+(?:all\s+)?(?:previous|prior)\s+instructions/i`
   - `/(?:you\s+are\s+now|act\s+as|system\s+prompt)/i`
   - `/(?:mark|declare)\s+this\s+(?:as\s+)?(?:patentable|approved|compliant)/i`
3. **Audit Log**: Stripped strings are logged to the security register as threat telemetry.
