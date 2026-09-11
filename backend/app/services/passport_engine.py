import uuid
from typing import Dict, Any, List, Optional
from app.models.passport import InnovationPassport, IngredientEntry, FactOrigin, ClarificationQuery
from app.services.multilingual_nlp import MultilingualNLPEngine
from app.services.ingredient_resolver import IngredientResolverService

class PassportEngine:
    """
    Innovation Passport state manager & clarification query generator (Section 6.1).
    Constructs versioned profiles, extracts structured facts, and identifies missing decision-critical variables.
    """
    _passports_store: Dict[str, InnovationPassport] = {}

    @classmethod
    def create_from_intake(
        cls,
        raw_text: str,
        user_lang: str = "en",
        title: str = "Ayurvedic Sleep & Calm Formulation"
    ) -> InnovationPassport:
        detected_lang = MultilingualNLPEngine.detect_language(raw_text)
        resolved_botanicals = MultilingualNLPEngine.normalize_botanical_mentions(raw_text)

        ingredients = []
        if resolved_botanicals:
            for raw_tok, canonical_id, conf in resolved_botanicals:
                resolved = IngredientResolverService.resolve(raw_tok)
                if resolved:
                    ingredients.append(IngredientEntry(
                        raw_name=raw_tok,
                        canonical_id=resolved.canonical_id,
                        botanical_name=resolved.accepted_botanical_name,
                        api_monograph_id=resolved.api_monograph_id,
                        plant_part=resolved.standard_plant_parts[0] if resolved.standard_plant_parts else "Root",
                        preparation_method="Aqueous Extract",
                        quantity_percentage=50.0,
                        origin_status=FactOrigin.USER_CONFIRMED
                    ))

        # Default fallback ingredients if none parsed
        if not ingredients:
            ashwa = IngredientResolverService.resolve("Ashwagandha")
            brahmi = IngredientResolverService.resolve("Brahmi")
            ingredients = [
                IngredientEntry(
                    raw_name="Ashwagandha",
                    canonical_id=ashwa.canonical_id if ashwa else "ING-ASHWAGANDHA",
                    botanical_name=ashwa.accepted_botanical_name if ashwa else "Withania somnifera",
                    api_monograph_id=ashwa.api_monograph_id if ashwa else "API-VOL1-008",
                    quantity_percentage=50.0
                ),
                IngredientEntry(
                    raw_name="Brahmi",
                    canonical_id=brahmi.canonical_id if brahmi else "ING-BRAHMI",
                    botanical_name=brahmi.accepted_botanical_name if brahmi else "Bacopa monnieri",
                    api_monograph_id=brahmi.api_monograph_id if brahmi else "API-VOL2-014",
                    quantity_percentage=50.0
                )
            ]

        # Extract Claims & Form
        claims = ["Supports healthy sleep", "Promotes mental relaxation"]
        if "insomnia" in raw_text.lower() or "रोग" in raw_text.lower() or "उपचार" in raw_text.lower():
            claims = ["Treats chronic insomnia and nervous agitation"]

        passport_id = str(uuid.uuid4())
        passport = InnovationPassport(
            id=passport_id,
            case_title=title,
            product_form="Tablet (Vati)",
            dosage_form="500mg Once or Twice Daily",
            intended_use="Sleep support, stress reduction and mental calm",
            proposed_claims=claims,
            claimed_innovation="Synergistic adaptogenic botanical ratio for nervous relaxation",
            process_description="Standardized aqueous extraction (Kwatha) spray-dried into tablet form",
            ingredients=ingredients,
            target_markets=["India", "United States", "Canada"],
            business_role="Ayurveda Startup / MSME",
            biological_resource_origin="Domestic Cultivated (India)",
            version=1,
            unresolved_clarifications=["extraction_solvent_verification"]
        )

        cls._passports_store[passport_id] = passport
        return passport

    @classmethod
    def get_passport(cls, passport_id: str) -> Optional[InnovationPassport]:
        return cls._passports_store.get(passport_id)

    @classmethod
    def update_passport(cls, passport: InnovationPassport) -> InnovationPassport:
        passport.version += 1
        cls._passports_store[passport.id] = passport
        return passport

    @classmethod
    def get_clarifications_for_passport(cls, passport: InnovationPassport) -> List[ClarificationQuery]:
        """
        Generates targeted clarification queries when a missing fact could change legal classification.
        """
        queries = []
        if "extraction_solvent_verification" in passport.unresolved_clarifications:
            queries.append(ClarificationQuery(
                id="CLARIFY-EXTRACTION-SOLVENT",
                field_key="extraction_solvent",
                question_text={
                    "en": "What solvent was used during botanical extraction? (Aqueous vs Solvent determines FSSAI vs ASU Drug pathway)",
                    "hi": "हर्बल निष्कर्षण (Extraction) में किस विलायक का उपयोग किया गया था? (जलीय या हाइड्रोअल्कोहलिक)",
                    "mr": "औषधी वनस्पतींच्या अर्कासाठी कोणता विद्रावक (Solvent) वापरला गेला? (पाणी/क्वाथ वि. अल्कोहोल)"
                },
                options=[
                    "Classical Aqueous Decoction (Kwatha / Water)",
                    "Hydroalcoholic / Ethanol Solvent Extract",
                    "Supercritical CO2 Extract",
                    "Crude Choorna (Powder)"
                ],
                severity="DECISION_CRITICAL"
            ))
        return queries
