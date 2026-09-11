import hashlib
import json
import os
from typing import Optional, Dict, List, Tuple, Any
from app.models.canonical import CanonicalIngredient, FormulationFingerprint
from app.services.multilingual_nlp import MultilingualNLPEngine

class IngredientResolverService:
    """
    Canonical botanical ingredient resolution & formulation fingerprinting engine (Section 7.2.1).
    Maps vernacular, Sanskrit, and trade names to standard Ayurvedic Pharmacopoeia of India (API) monographs.
    """
    _monographs: Dict[str, Dict] = {}

    @classmethod
    def load_data(cls):
        if not cls._monographs:
            monograph_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "api_monographs.json")
            if os.path.exists(monograph_path):
                with open(monograph_path, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
                    cls._monographs = {item["canonical_id"]: item for item in raw_list}

    @classmethod
    def resolve(cls, raw_name: str) -> Optional[CanonicalIngredient]:
        cls.load_data()
        normalized_matches = MultilingualNLPEngine.normalize_botanical_mentions(raw_name)

        if normalized_matches:
            canonical_id = normalized_matches[0][1]
            if canonical_id in cls._monographs:
                mono = cls._monographs[canonical_id]
                return CanonicalIngredient(
                    canonical_id=canonical_id,
                    api_monograph_id=mono["api_monograph_id"],
                    accepted_botanical_name=mono["botanical_name"],
                    family=mono["family"],
                    standard_plant_parts=mono["standard_plant_parts"],
                    classical_therapeutic_uses=mono["classical_therapeutic_uses"],
                    fssai_aahara_status=mono.get("fssai_aahara_status", "permitted"),
                    us_fda_ndi_status=mono.get("us_fda_ndi_status", "old_dietary_ingredient"),
                    canada_nhpid_status=mono.get("canada_nhpid_status", "monographed"),
                    resolution_confidence=0.98
                )

        # Direct search by standard English key
        raw_key = "ING-" + raw_name.upper().strip()
        if raw_key in cls._monographs:
            mono = cls._monographs[raw_key]
            return CanonicalIngredient(
                canonical_id=raw_key,
                api_monograph_id=mono["api_monograph_id"],
                accepted_botanical_name=mono["botanical_name"],
                family=mono["family"],
                standard_plant_parts=mono["standard_plant_parts"],
                classical_therapeutic_uses=mono["classical_therapeutic_uses"],
                fssai_aahara_status=mono.get("fssai_aahara_status", "permitted"),
                us_fda_ndi_status=mono.get("us_fda_ndi_status", "old_dietary_ingredient"),
                canada_nhpid_status=mono.get("canada_nhpid_status", "monographed"),
                resolution_confidence=0.95
            )

        return None

    @classmethod
    def generate_formulation_fingerprint(
        cls,
        ingredients: List[Dict[str, Any]],
        process_desc: str
    ) -> FormulationFingerprint:
        """
        Constructs a deterministic formulation fingerprint hash based on canonical ingredients,
        quantitative ratios, and process signatures.
        """
        canonical_ids = []
        ratios = {}

        for ing in ingredients:
            c_id = ing.get("canonical_id") or "UNKNOWN"
            canonical_ids.append(c_id)
            ratios[c_id] = float(ing.get("quantity_percentage", 0.0))

        canonical_ids.sort()
        signature_tokens = [f"{k}:{ratios.get(k, 0.0):.1f}" for k in canonical_ids]
        raw_sig = "|".join(signature_tokens) + f"|process:{process_desc.lower().strip()}"
        fingerprint_hash = hashlib.sha256(raw_sig.encode()).hexdigest()[:16]

        return FormulationFingerprint(
            fingerprint_hash=fingerprint_hash,
            canonical_ingredient_ids=canonical_ids,
            ratios=ratios,
            process_signature=process_desc
        )
