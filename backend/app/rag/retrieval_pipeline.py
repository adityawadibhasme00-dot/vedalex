"""
Unified Hybrid Retrieval Pipeline for VEDALEX RAG.

Combines four retrieval strategies with cascading fallback:
  1. Qdrant semantic search (dense vector similarity)
  2. BM25 lexical search (keyword matching via rank_bm25)
  3. Metadata filtering (source, jurisdiction, authority, patent_number)
  4. BGE Reranker (cross-encoder re-scoring)

Pipeline flow:
  Query -> Query Expansion -> Embed -> Qdrant Search (top 20)
       -> BM25 Search (top 20)
       -> Multi-Query Retrieval (parallel)
       -> Merge + Deduplicate
       -> Metadata Filter
       -> Adaptive Rerank (top N -> top K)
       -> Hallucination Check
       -> Confidence Calculation
       -> Return Verified Context

This replaces both faiss_retriever.py and retrieval_engine.py with a single
production-grade module.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Query expansion synonyms for Ayurveda/IP domain
QUERY_EXPANSION_SYNONYMS: dict[str, list[str]] = {
    "ayurvedic": ["ayurveda", "traditional medicine", "herbal"],
    "patent": ["intellectual property", "ip", "invention", "novelty"],
    "formulation": ["composition", "preparation", "dosage form", "medicine"],
    "ingredient": ["herb", "botanical", "api", "active compound"],
    "compliance": ["regulatory", "legal", "guideline", "standard"],
    "fssai": ["food safety", "ayurveda aahara", "nutraceutical"],
    "cdsco": ["drug control", "schedule t", "gmp", "manufacturing"],
    "tkdl": ["traditional knowledge", "prior art", "classical text"],
    "section 3(p)": ["3p", "traditional knowledge exception", "patent exclusion"],
    "abs": ["access benefit sharing", "nba", "biodiversity", "biological diversity"],
    "dshea": ["dietary supplement", "fda", "us market", "structure function"],
    "clinical": ["trial", "study", "efficacy", "safety data"],
    "stability": ["shelf life", "storage", "degradation", "quality"],
    "extraction": ["isolation", "purification", "process", "method"],
    "synergy": ["combination", "potentiation", "enhancing", "complementary"],
    "white space": ["opportunity", "gap", "unclaimed", "blue ocean"],
    "prior art": ["existing patent", "anticipation", "novelty destruction"],
    "fto": ["freedom to operate", "infringement", "clearance", "blocking"],
    "claim": ["assertion", "scope", "coverage", "wording"],
    "label": ["packaging", "marketing", "advertising", "branding"],
    "export": ["international", "cross-border", "market entry", "global"],
    "gmp": ["good manufacturing practice", "quality", "schedule t", "facility"],
    "monograph": ["pharmacopoeia", "standard", "specification", "api"],
    "radar": ["readiness", "score", "assessment", "evaluation"],
    "roadmap": ["journey", "timeline", "path", "steps", "process"],
    "evidence": ["data", "proof", "support", "validation", "verification"],
    "risk": ["hazard", "danger", "threat", "exposure", "vulnerability"],
    "cost": ["fee", "expense", "price", "budget", "investment"],
    "deadline": ["due date", "timeline", "cutoff", "last date"],
    "trademark": ["brand", "mark", "logo", "name", "gi"],
    "copyright": ["author", "literary", "artistic", "ownership"],
    "design": ["appearance", "ornamental", "shape", "configuration"],
    "pct": ["international application", "wipo", "patent cooperation treaty"],
    "madrid": ["trademark international", "brand protection", "wipo"],
    "hague": ["design international", "industrial design", "wipo"],
    "lisbon": ["appellation", "geographical indication", "origin"],
    "nagoya": ["protocol", "genetic resources", "benefit sharing"],
    "treaty": ["convention", "agreement", "protocol", "international"],
    "act": ["law", "statute", "legislation", "regulation"],
    "rule": ["regulation", "guideline", "norm", "standard"],
    "notification": ["gazette", "circular", "order", "amendment"],
    "guideline": ["guidance", "advisory", "recommendation", "direction"],
    "circular": ["notice", "communication", "memorandum", "letter"],
    "order": ["directive", "instruction", "command", "decree"],
    "amendment": ["modification", "change", "revision", "update"],
    "schedule": ["annexure", "appendix", "table", "list"],
    "form": ["format", "template", "proforma", "structure"],
    "fee": ["charge", "cost", "payment", "remittance"],
    "license": ["permit", "authorization", "approval", "consent"],
    "registration": ["enrollment", "record", "filing", "application"],
    "renewal": ["revival", "extension", "continuation", "restoration"],
    "suspension": ["interruption", "pause", "halt", "stoppage"],
    "cancellation": ["revocation", "annulment", "termination", "withdrawal"],
    "appeal": ["review", "revision", "challenge", "petition"],
    "tribunal": ["court", "forum", "authority", "judicial"],
    "high court": ["hc", "judiciary", "appellate", "superior"],
    "supreme court": ["sc", "apex", "highest", "final"],
    "ip india": ["indian patent office", "ipo", "patent office"],
    "wipo": ["world intellectual property", "international bureau"],
    "who": ["world health organization", "health authority"],
    "fda": ["food and drug administration", "us regulator"],
    "health canada": ["canadian health", "nhpr", "natural health"],
    "ayush": ["ministry of ayush", "ayush ministry", "government"],
    "nba": ["national biodiversity authority", "biodiversity board"],
    "biodiversity": ["biological diversity", "bioresource", "genetic"],
    "genetic": ["hereditary", "dna", "gene", "genome"],
    "traditional": ["classical", "ancestral", "heritage", "folk"],
    "knowledge": ["information", "wisdom", "practice", "science"],
    "medicine": ["drug", "remedy", "therapeutic", "healing"],
    "herb": ["plant", "botanical", "herbal", "medicinal"],
    "plant": ["flora", "botanical", "herb", "tree"],
    "root": ["rhizome", "tuber", "bulb", "underground"],
    "leaf": ["foliage", "herb", "green", "blade"],
    "flower": ["bloom", "blossom", "petal", "corolla"],
    "fruit": ["berry", "drupe", "pome", "seed"],
    "seed": ["grain", "kernel", "nut", "pit"],
    "bark": ["rind", "cortex", "outer", "covering"],
    "resin": ["gum", "latex", "sap", "exudate"],
    "oil": ["fat", "lipid", "essence", "extract"],
    "powder": ["dust", "ground", "pulverized", "fine"],
    "tablet": ["pill", "caplet", "lozenge", "troche"],
    "capsule": ["gelcap", "softgel", "hard shell", "container"],
    "syrup": ["elixir", "solution", "suspension", "liquid"],
    "cream": ["ointment", "salve", "balm", "emollient"],
    "gel": ["jelly", "colloidal", "semisolid", "transparent"],
    "paste": ["ointment", "cream", "salve", "topical"],
    "decoction": ["kwatha", "kashayam", "boiled", "extraction"],
    "infusion": ["tea", "tisane", "steeped", "hot water"],
    "tincture": ["extract", "alcohol", "concentrated", "solution"],
    "distillate": ["volatile", "essential", "aromatic", "steam"],
    "fermented": ["asava", "arishta", "wine", "brewed"],
    "medicated": ["treated", "enriched", "fortified", "enhanced"],
    "ghee": ["clarified butter", "ghrita", "fat", "lipid"],
    "honey": ["madhu", "sweet", "nectar", "viscous"],
    "jaggery": ["gur", "unrefined", "cane", "sweet"],
    "sugar": ["sweetener", "sucrose", "cane", "refined"],
    "salt": ["sodium", "mineral", "rock", "sea"],
    "ash": ["bhasma", "calcined", "oxide", "residue"],
    "calcined": ["incinerated", "burned", "heated", "oxidized"],
    "purified": ["shodhana", "detoxified", "cleaned", "refined"],
    "processed": ["prepared", "treated", "manufactured", "refined"],
    "standardized": ["normalized", "controlled", "consistent", "uniform"],
    "quality": ["grade", "purity", "standard", "specification"],
    "safety": ["toxicity", "adverse", "side effect", "risk"],
    "efficacy": ["effectiveness", "potency", "activity", "performance"],
    "stability": ["shelf life", "degradation", "storage", "preservation"],
    "bioavailability": ["absorption", "uptake", "utilization", "delivery"],
    "pharmacokinetics": ["adme", "absorption", "distribution", "metabolism"],
    "pharmacodynamics": ["mechanism", "action", "effect", "response"],
    "clinical trial": ["study", "research", "experiment", "investigation"],
    "preclinical": ["animal", "in vitro", "lab", "experimental"],
    "toxicology": ["safety", "poison", "hazard", "risk"],
    "adverse event": ["side effect", "reaction", "complication", "harm"],
    "contraindication": ["warning", "precaution", "avoid", "prohibition"],
    "interaction": ["interference", "conflict", "reaction", "effect"],
    "dosage": ["dose", "amount", "quantity", "regimen"],
    "administration": ["delivery", "route", "method", "application"],
    "indication": ["use", "purpose", "condition", "disease"],
    "therapeutic": ["healing", "curative", "treatment", "remedy"],
    "diagnostic": ["detection", "identification", "screening", "test"],
    "prophylactic": ["preventive", "protective", "prophylaxis", "avoidance"],
    "palliative": ["supportive", "comfort", "relief", "symptomatic"],
    "adjuvant": ["auxiliary", "supportive", "complementary", "additional"],
    "synergistic": ["complementary", "enhancing", "potentiating", "combined"],
    "antagonistic": ["opposing", "counteracting", "interfering", "conflicting"],
    "bioactive": ["active", "pharmacological", "therapeutic", "functional"],
    "phytochemical": ["plant chemical", "natural compound", "botanical active"],
    "alkaloid": ["nitrogen", "basic", "phytochemical", "active"],
    "flavonoid": ["polyphenol", "antioxidant", "pigment", "bioactive"],
    "terpenoid": ["isoprene", "essential oil", "aromatic", "bioactive"],
    "glycoside": ["sugar", "bound", "conjugate", "bioactive"],
    "saponin": ["foam", "detergent", "hemolytic", "bioactive"],
    "tannin": ["astringent", "polyphenol", "precipitant", "bioactive"],
    "polysaccharide": ["complex sugar", "starch", "fiber", "bioactive"],
    "protein": ["amino acid", "enzyme", "peptide", "macromolecule"],
    "lipid": ["fat", "oil", "sterol", "hydrophobic"],
    "vitamin": ["nutrient", "coenzyme", "essential", "micronutrient"],
    "mineral": ["element", "trace", "inorganic", "electrolyte"],
    "antioxidant": ["free radical", "oxidative", "protective", "scavenger"],
    "anti-inflammatory": ["inflammation", "swelling", "redness", "pain"],
    "antimicrobial": ["antibacterial", "antifungal", "antiviral", "germicide"],
    "analgesic": ["pain", "relief", "soothing", "comfort"],
    "antipyretic": ["fever", "temperature", "cooling", "reducing"],
    "expectorant": ["mucus", "cough", "phlegm", "clearing"],
    "digestive": ["stomach", "intestine", "gut", "assimilation"],
    "carminative": ["gas", "bloating", "flatulence", "relief"],
    "laxative": ["bowel", "constipation", "purgative", "cleansing"],
    "diuretic": ["urine", "kidney", "water", "elimination"],
    "hepatic": ["liver", "hepatoprotective", "bile", "detox"],
    "cardiac": ["heart", "cardiovascular", "circulation", "pulse"],
    "nervous": ["neural", "brain", "nerve", "cognitive"],
    "respiratory": ["lung", "breathing", "airway", "pulmonary"],
    "immune": ["immunity", "defense", "resistance", "protection"],
    "endocrine": ["hormone", "gland", "metabolic", "thyroid"],
    "reproductive": ["fertility", "genital", "sexual", "procreative"],
    "musculoskeletal": ["bone", "muscle", "joint", "skeletal"],
    "integumentary": ["skin", "hair", "nail", "dermal"],
    "urinary": ["kidney", "bladder", "urine", "renal"],
    "lymphatic": ["lymph", "immune", "drainage", "spleen"],
    "sensory": ["sense", "vision", "hearing", "taste"],
    "mental": ["mind", "psychological", "emotional", "cognitive"],
    "sleep": ["insomnia", "rest", "sedation", "calm"],
    "stress": ["anxiety", "tension", "strain", "pressure"],
    "memory": ["cognition", "recall", "learning", "concentration"],
    "focus": ["attention", "concentration", "clarity", "alertness"],
    "energy": ["vitality", "stamina", "vigor", "strength"],
    "fatigue": ["tiredness", "exhaustion", "lethargy", "weakness"],
    "aging": ["senescence", "longevity", "anti-aging", "elderly"],
    "detox": ["cleanse", "purify", "eliminate", "toxin"],
    "rejuvenate": ["rasayana", "renew", "restore", "revitalize"],
    "adaptogen": ["stress", "resistance", "balance", "homeostasis"],
    "rasayana": ["rejuvenation", "longevity", "vitality", "anti-aging"],
    "vajikarana": ["aphrodisiac", "fertility", "sexual", "reproductive"],
    "sthanika": ["local", "topical", "external", "applied"],
    "abhyanga": ["massage", "oil", "rub", "therapeutic"],
    "panchakarma": ["detox", "cleansing", "rejuvenation", "therapy"],
    "shirodhara": ["oil", "forehead", "calm", "relaxation"],
    "nasya": ["nasal", "nose", "head", "sinus"],
    "basti": ["enema", "colon", "cleansing", "vata"],
    "virechana": ["purgation", "cleansing", "pitta", "elimination"],
    "vamana": ["emesis", "cleansing", "kapha", "elimination"],
    "raktamoksha": ["blood", "letting", "detox", "cleansing"],
    "yoga": ["exercise", "posture", "breath", "meditation"],
    "pranayama": ["breath", "respiration", "lung", "energy"],
    "meditation": ["mindfulness", "concentration", "calm", "awareness"],
    "mantra": ["chant", "sound", "vibration", "sacred"],
    "ayurveda": ["ayurvedic", "traditional", "holistic", "dosha"],
    "dosha": ["vata", "pitta", "kapha", "constitution"],
    "vata": ["air", "ether", "movement", "nervous"],
    "pitta": ["fire", "water", "metabolism", "digestive"],
    "kapha": ["earth", "water", "structure", "stability"],
    "prakriti": ["constitution", "nature", "body type", "dosha"],
    "vikriti": ["imbalance", "disorder", "disease", "dosha"],
    "agni": ["digestive fire", "metabolism", "enzyme", "transformation"],
    "ama": ["toxin", "undigested", "waste", "impurity"],
    "ojas": ["vitality", "immunity", "essence", "strength"],
    "srotas": ["channel", "system", "pathway", "circulation"],
    "dhatu": ["tissue", "element", "structure", "support"],
    "mala": ["waste", "excretion", "elimination", "byproduct"],
    "prana": ["life force", "energy", "breath", "vital"],
    "tejas": ["radiance", "fire", "transformation", "clarity"],
    "sattva": ["purity", "harmony", "balance", "clarity"],
    "rajas": ["activity", "movement", "passion", "energy"],
    "tamas": ["inertia", "stability", "darkness", "heaviness"],
}

# BM25 imports (graceful fallback)
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed — keyword search disabled")


class HybridRetriever:
    """
    Production-grade hybrid retrieval engine.
    """

    _instance: Optional["HybridRetriever"] = None
    _bm25_index = None
    _bm25_corpus: list[dict[str, Any]] = []
    _bm25_tokenized: list[list[str]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # BM25 Index Management
    # ------------------------------------------------------------------

    @classmethod
    def build_bm25_index(cls, documents: list[dict[str, Any]]):
        """Build BM25 index from knowledge base documents."""
        if not BM25_AVAILABLE:
            logger.warning("BM25 unavailable — semantic-only mode")
            return

        corpus = []
        for doc in documents:
            content = doc.get("content", "")
            if not content.strip():
                continue
            tokens = re.findall(r'\w+', content.lower())
            corpus.append((tokens, doc))

        if not corpus:
            return

        tokenized = [c[0] for c in corpus]
        cls._bm25_index = BM25Okapi(tokenized)
        cls._bm25_corpus = [c[1] for c in corpus]
        cls._bm25_tokenized = tokenized
        logger.info(f"BM25 index built: {len(corpus)} documents")

    @classmethod
    def bm25_search(
        cls, query: str, top_k: int = 20, domains: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Keyword search using BM25 scoring."""
        if cls._bm25_index is None:
            # Auto-build index from Qdrant if available (or KB files)
            try:
                from app.rag.qdrant_store import QdrantVectorStore
                store = QdrantVectorStore()
                docs = store.get_all_documents(limit=5000)
                if docs:
                    cls.build_bm25_index(docs)
            except Exception:
                try:
                    from app.rag.kb import collect_knowledge_documents
                    docs = collect_knowledge_documents()
                    if docs:
                        cls.build_bm25_index(docs)
                except Exception:
                    logger.warning("Could not auto-build BM25 index")
                    return []

        if cls._bm25_index is None:
            return []

        query_tokens = re.findall(r'\w+', query.lower())
        scores = cls._bm25_index.get_scores(query_tokens)

        if domains:
            domain_set = set(domains)
            scored = [
                (i, float(scores[i]))
                for i in range(len(scores))
                if scores[i] > 0
                and cls._bm25_corpus[i].get("collection") in domain_set
            ]
        else:
            scored = [
                (i, float(scores[i]))
                for i in range(len(scores))
                if scores[i] > 0
            ]
        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[dict[str, Any]] = []
        for idx, score in scored[:top_k]:
            doc = cls._bm25_corpus[idx].copy()
            doc["bm25_score"] = score
            doc["bm25_rank"] = len(results) + 1
            results.append(doc)

        return results

    # ------------------------------------------------------------------
    # Qdrant Search
    # ------------------------------------------------------------------

    @classmethod
    def qdrant_search(
        cls,
        query: str,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
        domains: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search via Qdrant restricted to intent-relevant domains."""
        from app.rag.qdrant_store import QdrantVectorStore
        store = QdrantVectorStore()
        return store.hybrid_search(query, top_k=top_k, filters=filters, domains=domains)

    # ------------------------------------------------------------------
    # BM25 Keyword Search (legacy fallback via retrieval_engine)
    # ------------------------------------------------------------------

    @classmethod
    def statutory_search(
        cls,
        query: str,
        jurisdiction: str | None = None,
        top_k: int = 6,
        min_score: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Search statutory passages via the existing retrieval engine."""
        from app.services.retrieval_engine import HybridRetrievalEngine
        citations = HybridRetrievalEngine.search_passages(
            query, jurisdiction=jurisdiction, top_k=top_k, min_score=min_score
        )
        results = []
        for cit in citations:
            results.append({
                "content": cit.exact_passage[:1200],
                "source": cit.source_url or cit.act_title,
                "category": "statutory",
                "act_title": cit.act_title,
                "section_heading": cit.section_reference,
                "authority": cit.authority,
                "source_url": cit.source_url or "",
                "effective_date": cit.effective_date,
                "authority_level": cit.authority_rank,
                "title": cit.act_title,
            })
        return results

    # ------------------------------------------------------------------
    # Merge + Deduplicate (Reciprocal Rank Fusion)
    # ------------------------------------------------------------------

    RRF_K = 60.0

    @staticmethod
    def _rrf_score(rank: int) -> float:
        """Reciprocal Rank Fusion contribution for a document at 1-based rank."""
        return 1.0 / (HybridRetriever.RRF_K + rank)

    @staticmethod
    def _doc_merge_key(doc: dict[str, Any]) -> str:
        """Stable dedup identity across retrieval strategies."""
        doc_id = doc.get("doc_id") or doc.get("id") or ""
        source = doc.get("source") or ""
        act_title = doc.get("act_title") or ""
        content_snip = (doc.get("content") or "")[:100]
        if act_title:
            return f"stat:{act_title}|{source}|{content_snip[:60]}"
        return f"{doc_id}|{source}|{content_snip}"

    @classmethod
    def _merge_results(
        cls,
        semantic_results: list[dict[str, Any]],
        bm25_results: list[dict[str, Any]],
        statutory_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Fuse all retrieval lists with Reciprocal Rank Fusion, dedupe, and
        normalise per-source scores. Statutory sources keep a small authority
        tiebreak so binding law surfaces first when RRF scores are equal."""
        merged: dict[str, dict[str, Any]] = {}

        for i, doc in enumerate(semantic_results, start=1):
            key = cls._doc_merge_key(doc)
            entry = merged.setdefault(key, {**doc, "retrieval_methods": set()})
            entry.setdefault("semantic_rank", i)
            entry.setdefault("semantic_score", doc.get("score", 0))
            entry["retrieval_methods"].add("semantic")

        for i, doc in enumerate(bm25_results, start=1):
            key = cls._doc_merge_key(doc)
            entry = merged.setdefault(key, {**doc, "retrieval_methods": set()})
            entry.setdefault("bm25_rank", i)
            entry.setdefault("bm25_score", doc.get("bm25_score", 0))
            entry["retrieval_methods"].add("keyword")

        for i, doc in enumerate(statutory_results, start=1):
            key = cls._doc_merge_key(doc)
            entry = merged.setdefault(key, {**doc, "retrieval_methods": set()})
            entry.setdefault("statutory_rank", i)
            entry["retrieval_methods"].add("statutory")

        for entry in merged.values():
            rrf = 0.0
            if "semantic" in entry["retrieval_methods"]:
                rrf += cls._rrf_score(entry["semantic_rank"])
            if "keyword" in entry["retrieval_methods"]:
                rrf += cls._rrf_score(entry["bm25_rank"])
            if "statutory" in entry["retrieval_methods"]:
                rrf += cls._rrf_score(entry["statutory_rank"])

            # Authority/Fusion tiebreak (secondary, keeps statutes on top).
            authority = 1.0 / max(1, int(entry.get("authority_level", 3)))
            is_statutory = 1.0 if "statutory" in entry["retrieval_methods"] else 0.0
            entry["rrf_score"] = round(rrf, 6)
            entry["combined_score"] = round(rrf + authority * 0.05 + is_statutory * 0.03, 6)
            entry["retrieval_method"] = (
                "hybrid" if len(entry["retrieval_methods"]) > 1
                else next(iter(entry["retrieval_methods"]))
            )
            entry["retrieval_methods"] = sorted(entry["retrieval_methods"])

        out = sorted(merged.values(), key=lambda x: x.get("combined_score", 0), reverse=True)
        for i, doc in enumerate(out, start=1):
            doc["final_rank"] = i
        return out

    # ------------------------------------------------------------------
    # Metadata Filtering
    # ------------------------------------------------------------------

    @classmethod
    def _apply_metadata_filters(
        cls,
        documents: list[dict[str, Any]],
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter documents by metadata fields."""
        if not filters:
            return documents

        filtered = []
        for doc in documents:
            match = True
            for key, value in filters.items():
                doc_val = doc.get(key, "")
                if isinstance(value, str) and value.lower() not in str(doc_val).lower():
                    match = False
                    break
                elif isinstance(value, (int, float)):
                    if int(doc_val) != value:
                        match = False
                        break
                elif isinstance(value, list):
                    if str(doc_val) not in value:
                        match = False
                        break
            if match:
                filtered.append(doc)

        return filtered

    # ------------------------------------------------------------------
    # Query Expansion
    # ------------------------------------------------------------------

    @classmethod
    def _expand_query(cls, query: str) -> list[str]:
        """Expand query with domain synonyms for better recall."""
        expanded = [query]
        q_lower = query.lower()
        for term, synonyms in QUERY_EXPANSION_SYNONYMS.items():
            if term in q_lower:
                for syn in synonyms[:3]:
                    expanded.append(query.replace(term, syn, 1) if term in query else f"{query} {syn}")
        return expanded[:5]

    # ------------------------------------------------------------------
    # Multi-Query Retrieval
    # ------------------------------------------------------------------

    @classmethod
    def _multi_query_retrieve(
        cls,
        queries: list[str],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
        domains: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Run retrieval for multiple queries in parallel."""
        semantic_all: list[dict[str, Any]] = []
        bm25_all: list[dict[str, Any]] = []
        statutory_all: list[dict[str, Any]] = []

        def _retrieve(q: str):
            sem = cls.qdrant_search(q, top_k=top_k, filters=filters, domains=domains)
            bm = cls.bm25_search(q, top_k=top_k, domains=domains)
            stat = cls.statutory_search(q, top_k=6)
            return sem, bm, stat

        with ThreadPoolExecutor(max_workers=min(3, len(queries))) as pool:
            futures = {pool.submit(_retrieve, q): q for q in queries}
            for fut in as_completed(futures):
                try:
                    sem, bm, stat = fut.result()
                    semantic_all.extend(sem)
                    bm25_all.extend(bm)
                    statutory_all.extend(stat)
                except Exception as exc:
                    logger.warning("Multi-query retrieval failed for '%s': %s", futures[fut], exc)

        return semantic_all, bm25_all, statutory_all

    # ------------------------------------------------------------------
    # Reranking
    # ------------------------------------------------------------------

    @classmethod
    def _rerank(
        cls,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Rerank documents using cross-encoder with adaptive depth."""
        from app.rag.reranker import Reranker
        if not Reranker.is_available():
            return [
                {**d, "rerank_score": d.get("score", 1.0 / (i + 1)), "original_rank": i}
                for i, d in enumerate(documents[:top_k])
            ]
        reranker = Reranker()
        # Adaptive: rerank more candidates when we have many, fewer when we have few
        adaptive_k = min(len(documents), max(top_k * 2, 10))
        return reranker.rerank(query, documents[:adaptive_k], top_k=top_k)

    # ------------------------------------------------------------------
    # Confidence Calculation
    # ------------------------------------------------------------------

    @classmethod
    def _compute_confidence(
        cls,
        query: str,
        sources: list[dict[str, Any]],
        grounding: dict[str, Any],
    ) -> float:
        """Compute confidence score based on retrieval quality signals."""
        if not sources:
            return 0.05

        coverage = grounding.get("coverage_ratio", 0)
        num_sources = len(sources)

        # Source authority signal
        authority_scores = []
        for s in sources:
            level = int(s.get("authority_level", 3))
            authority_scores.append(1.0 / max(1, level))
        avg_authority = sum(authority_scores) / len(authority_scores) if authority_scores else 0.25

        # Source diversity signal
        categories = set(s.get("category", "") for s in sources)
        diversity = min(1.0, len(categories) / 4.0)

        # Retrieval method signal
        has_statutory = any(s.get("retrieval_method") == "statutory" for s in sources)
        has_hybrid = any(s.get("retrieval_method") == "hybrid" for s in sources)

        # Reranker score signal
        rerank_scores = [s.get("rerank_score", 0.5) for s in sources]
        avg_rerank = sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0.5

        # Composite confidence
        conf = (
            0.10 +                          # base
            coverage * 0.25 +               # grounding
            avg_authority * 0.20 +          # source quality
            diversity * 0.10 +              # source diversity
            min(1.0, num_sources / 5) * 0.10 +  # quantity
            avg_rerank * 0.10 +             # reranker agreement
            (0.05 if has_statutory else 0) +  # statutory bonus
            (0.05 if has_hybrid else 0)       # hybrid bonus
        )

        return round(max(0.05, min(0.97, conf)), 2)

    # ------------------------------------------------------------------
    # Main Retrieve Method
    # ------------------------------------------------------------------

    @classmethod
    def retrieve(
        cls,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        jurisdiction: str | None = None,
        category: str | None = None,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Full hybrid retrieval pipeline with query expansion and multi-query retrieval.

        Args:
            domains: Intent-relevant curated collections to restrict the search
                to. None searches every available collection.

        Returns:
            {
                "sources": [...],           # Final reranked sources
                "confidence": float,        # Confidence score
                "grounding": {...},         # Grounding check details
                "all_candidates": [...],    # Pre-rerank merged results
                "retrieval_stats": {...},   # Timing and count stats
            }
        """
        import time
        start = time.time()

        # Build metadata filters
        effective_filters = filters or {}
        if category:
            effective_filters["category"] = category
        if jurisdiction:
            effective_filters["jurisdiction"] = jurisdiction

        # Step 1: Query expansion for better recall
        expanded_queries = cls._expand_query(query)
        use_multi_query = len(expanded_queries) > 1

        # Step 2: Multi-query retrieval (parallel) or single-query
        if use_multi_query:
            semantic_results, bm25_results, statutory_results = cls._multi_query_retrieve(
                expanded_queries, top_k=20, filters=effective_filters, domains=domains
            )
        else:
            semantic_results = cls.qdrant_search(
                query, top_k=20, filters=effective_filters, domains=domains
            )
            bm25_results = cls.bm25_search(query, top_k=20, domains=domains)
            statutory_results = cls.statutory_search(query, jurisdiction=jurisdiction, top_k=6)

        semantic_time = time.time() - start

        # Step 3: Merge + deduplicate
        merged = cls._merge_results(semantic_results, bm25_results, statutory_results)

        # Step 4: Apply metadata filters (for non-Qdrant results)
        if effective_filters:
            merged = cls._apply_metadata_filters(merged, effective_filters)

        # Step 5: Score normalization
        if merged:
            max_score = max(float(d.get("combined_score", 0)) for d in merged) or 1.0
            for d in merged:
                d["normalized_score"] = round(float(d.get("combined_score", 0)) / max_score, 6)

        # Step 6: Rerank with adaptive depth
        rerank_start = time.time()
        rerank_candidates = merged[:10]
        reranked = cls._rerank(query, rerank_candidates, top_k=top_k)
        rerank_time = time.time() - rerank_start

        # Step 7: Grounding check
        from app.rag.hallucination_guard import build_grounding_check
        grounding = build_grounding_check(query, reranked)

        # Step 8: Confidence
        confidence = cls._compute_confidence(query, reranked, grounding)

        # Step 9: Hallucination validation
        from app.rag.hallucination_guard import should_refuse_answer
        should_refuse, refusal_reason = should_refuse_answer(
            coverage=grounding["coverage_ratio"],
            confidence=confidence,
            num_sources=len(reranked),
        )

        total_time = time.time() - start

        return {
            "sources": reranked,
            "confidence": confidence,
            "grounding": grounding,
            "should_refuse": should_refuse,
            "refusal_reason": refusal_reason,
            "all_candidates": merged[:20],
            "retrieval_stats": {
                "semantic_results": len(semantic_results),
                "bm25_results": len(bm25_results),
                "statutory_results": len(statutory_results),
                "merged_count": len(merged),
                "final_count": len(reranked),
                "domains_filtered": domains,
                "query_expanded": use_multi_query,
                "expanded_queries": len(expanded_queries),
                "semantic_time_ms": round(semantic_time * 1000, 1),
                "rerank_time_ms": round(rerank_time * 1000, 1),
                "total_time_ms": round(total_time * 1000, 1),
                "embedding_provider": _get_embedding_provider(),
                "reranker_available": _is_reranker_available(),
                "qdrant_available": _is_qdrant_available(),
            },
        }

    # ------------------------------------------------------------------
    # Index Management
    # ------------------------------------------------------------------

    @classmethod
    def reindex_all(cls) -> dict[str, Any]:
        """Full reindex: load KB -> embed -> upsert to Qdrant."""
        import time
        start = time.time()

        from app.rag.kb import collect_knowledge_documents
        from app.rag.qdrant_store import QdrantVectorStore

        # Load all documents
        documents = collect_knowledge_documents()
        logger.info(f"Loaded {len(documents)} documents from knowledge base")

        # Build BM25 index
        cls.build_bm25_index(documents)

        # Upsert to Qdrant
        store = QdrantVectorStore()
        upserted = store.upsert_documents(documents)

        elapsed = time.time() - start
        stats = {
            "total_documents": len(documents),
            "upserted_to_qdrant": upserted,
            "bm25_index_size": len(cls._bm25_corpus),
            "elapsed_seconds": round(elapsed, 2),
        }
        logger.info(f"Reindex complete: {stats}")
        return stats

    @classmethod
    def get_status(cls) -> dict[str, Any]:
        """Return current pipeline status."""
        from app.rag.qdrant_store import QdrantVectorStore
        qdrant_stats = QdrantVectorStore().get_collection_stats()

        bm25_size = len(cls._bm25_corpus) if cls._bm25_corpus else 0
        if bm25_size == 0 and qdrant_stats.get("total_points", 0) > 0:
            try:
                store = QdrantVectorStore()
                docs = store.get_all_documents(limit=5000)
                if docs:
                    cls.build_bm25_index(docs)
                    bm25_size = len(cls._bm25_corpus)
            except Exception:
                pass

        return {
            "qdrant": qdrant_stats,
            "bm25": {
                "available": BM25_AVAILABLE,
                "index_size": bm25_size,
            },
            "embedding": {
                "provider": _get_embedding_provider(),
                "dim": _get_embedding_dim(),
            },
            "reranker": {
                "available": _is_reranker_available(),
            },
            "live_web": _get_official_web_status(),
        }


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _get_embedding_provider() -> str:
    try:
        from app.rag.embeddings import EmbeddingEngine
        return EmbeddingEngine.get_provider()
    except Exception:
        return "unknown"


def _get_embedding_dim() -> int:
    try:
        from app.rag.embeddings import EmbeddingEngine
        return EmbeddingEngine.get_dim()
    except Exception:
        return 0


def _is_reranker_available() -> bool:
    try:
        from app.rag.reranker import Reranker
        return Reranker.is_available()
    except Exception:
        return False


def _is_qdrant_available() -> bool:
    try:
        from app.rag.qdrant_store import QdrantVectorStore
        return QdrantVectorStore.is_available()
    except Exception:
        return False


def _get_official_web_status() -> dict[str, Any]:
    try:
        from app.rag.official_web_retriever import get_status
        return get_status()
    except Exception:
        return {"enabled": False, "reason": "unavailable"}


def _warmup_rag_pipeline() -> None:
    """Preload BGE-M3 embeddings and build the BM25 index so the first
    /rag/* request responds without the model-loading penalty."""
    try:
        from app.rag.embeddings import EmbeddingEngine
        engine = EmbeddingEngine()
        warm_text = "VEDALEX IP-SAKTI knowledge base warm-up query"
        engine.embed([warm_text])
        import logging
        logging.getLogger(__name__).info(
            f"RAG warm-up: embeddings ready ({engine.get_provider()}, dim={engine.get_dim()})"
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"RAG warm-up embeddings failed: {e}")

    try:
        _ = HybridRetriever.get_status()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"RAG warm-up status/index failed: {e}")

    # Pre-load the fast entailment embedder in the background thread
    # so its load doesn't compete with the first user request.
    try:
        from app.rag.semantic_entailment import _init_fast_embedder
        _init_fast_embedder()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"RAG warm-up fast embedder failed: {e}")

    # Pre-touch the reranker so its (possibly failed) load attempt happens
    # in the background thread instead of on the first user request.
    try:
        from app.rag.reranker import Reranker
        Reranker.is_available()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"RAG warm-up reranker failed: {e}")
