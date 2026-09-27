import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.db_models import IngredientDB, InnovationPassportDB, User
from app.models.passport import ClarificationQuery, FactOrigin, IngredientEntry, InnovationPassport
from app.services.ingredient_resolver import IngredientResolverService
from app.services.multilingual_nlp import MultilingualNLPEngine

_ANONYMOUS_USER_EMAIL = "anonymous@ipsakti.in"


def _get_or_create_anonymous_user(db: Session) -> User:
    user = db.query(User).filter(User.email == _ANONYMOUS_USER_EMAIL).first()
    if not user:
        user = User(
            name="Anonymous",
            email=_ANONYMOUS_USER_EMAIL,
            hashed_password="*",
            role="researcher",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


class PassportEngine:
    """
    Innovation Passport state manager & clarification query generator (Section 6.1).
    Constructs versioned profiles, extracts structured facts, and identifies missing decision-critical variables.
    Passports are persisted to the database (Postgres / SQLite fallback) so data survives restarts;
    the in-memory store is only a read-through cache.
    """
    _passports_store: dict[str, InnovationPassport] = {}

    @classmethod
    def create_from_intake(
        cls,
        raw_text: str,
        user_lang: str = "en",
        title: str = "Ayurvedic Botanical Formulation",
        intake: dict[str, Any] | None = None,
    ) -> InnovationPassport:
        intake = intake or {}
        product_type = intake.get("product_type") or "Ayurvedic Medicine"
        category = intake.get("category")
        target_markets = intake.get("target_markets")
        extraction_method = intake.get("extraction_method")
        solvent = intake.get("solvent")
        temperature = intake.get("temperature")
        time_ = intake.get("time")
        processing_steps = intake.get("processing_steps")
        proposed_claims = intake.get("proposed_claims")

        _FORM_MAPPING = {
            "Nutraceutical": ("Capsule", "500 mg Capsule, Once Daily"),
            "Ayurvedic Medicine": ("Tablet (Vati)", "500mg Once or Twice Daily"),
            "Cosmetic": ("Topical Cream", "Apply as needed"),
            "Food Supplement": ("Powder / Sachet", "1 Sachet (10 g) with meals"),
            "Herbal Supplement": ("Capsule", "500 mg Capsule, Once Daily"),
        }
        product_form, dosage_form = _FORM_MAPPING.get(
            product_type, ("Capsule", "500 mg Capsule, Once Daily")
        )

        ingredient_prep = "Aqueous Extract" + ((" - " + solvent) if solvent else "")

        MultilingualNLPEngine.detect_language(raw_text)
        resolved_botanicals = MultilingualNLPEngine.normalize_botanical_mentions(raw_text)

        ingredients = []
        if resolved_botanicals:
            for raw_tok, _canonical_id, _conf in resolved_botanicals:
                resolved = IngredientResolverService.resolve(raw_tok)
                if resolved:
                    ingredients.append(IngredientEntry(
                        raw_name=raw_tok,
                        canonical_id=resolved.canonical_id,
                        botanical_name=resolved.accepted_botanical_name,
                        api_monograph_id=resolved.api_monograph_id,
                        plant_part=resolved.standard_plant_parts[0] if resolved.standard_plant_parts else "Root",
                        preparation_method=ingredient_prep,
                        quantity_percentage=50.0,
                        origin_status=FactOrigin.USER_CONFIRMED
                    ))

        # No botanicals parsed — never fabricate a default ingredient set.
        # Ingredients stay empty so downstream engines treat the formulation
        # as unspecified until the user confirms botanicals, and a
        # DECISION_CRITICAL clarification is raised below. This keeps the
        # copilot herb-agnostic instead of assuming Ashwagandha/Brahmi.

        # Claims come only from the applicant's intake (or an explicit
        # therapeutic-phrasing cue in the raw text). No canned claim defaults.
        claims: list[str] = []
        if proposed_claims:
            claims = [c for c in proposed_claims if c]
        elif any(marker in raw_text.lower() for marker in (
            "treat", "cure", "insomnia", "रोग", "उपचार", "चिकित्सा",
        )):
            claims = [raw_text.strip()[:200]]

        # Build the process description from the intake so the typed/selected
        # values (e.g. "Ethanol 90% + Water 10%", "official", an official link)
        # are persisted into the passport and visible in exports/classification.
        if extraction_method:
            process_parts = [extraction_method]
        else:
            process_parts = ["Standardized aqueous extraction (Kwatha)"]
        if solvent:
            process_parts.append("using " + solvent)
        if temperature:
            process_parts.append("at " + temperature)
        if time_:
            process_parts.append("for " + time_)
        process_parts.append("spray-dried into " + product_form.lower() + " form")
        process_description = " ".join(process_parts)
        if processing_steps:
            process_description += ". Steps: " + processing_steps
        if category:
            process_description = "Category: " + category + " | " + process_description

        if target_markets:
            markets = [m for m in target_markets if m]
        else:
            markets = ["India", "United States", "Canada"]

        passport_id = str(uuid.uuid4())
        unresolved: list[str] = []
        if not solvent:
            unresolved.append("extraction_solvent_verification")
        if not ingredients:
            unresolved.append("ingredients_unspecified")

        passport = InnovationPassport(
            id=passport_id,
            case_title=title,
            product_form=product_form,
            dosage_form=dosage_form,
            intended_use=claims[0] if claims else "",
            proposed_claims=claims,
            claimed_innovation=f"{product_form} formulation of the botanicals described by the applicant",
            process_description=process_description,
            ingredients=ingredients,
            target_markets=markets,
            business_role="Ayurveda Startup / MSME",
            biological_resource_origin="Domestic Cultivated (India)",
            version=1,
            unresolved_clarifications=unresolved
        )

        cls._save_to_db(passport)
        cls._passports_store[passport_id] = passport
        return passport

    @classmethod
    def _save_to_db(cls, passport: InnovationPassport) -> None:
        """Write-through persistence so passports survive server restarts."""
        try:
            db = SessionLocal()
            try:
                user = _get_or_create_anonymous_user(db)
                db_passport: Any = db.query(InnovationPassportDB).filter(
                    InnovationPassportDB.id == passport.id
                ).first()
                if not db_passport:
                    db_passport = InnovationPassportDB(
                        id=passport.id,
                        user_id=user.id,
                        case_title=passport.case_title,
                        product_form=passport.product_form,
                        dosage_form=passport.dosage_form,
                        intended_use=passport.intended_use,
                        proposed_claims=passport.proposed_claims or [],
                        claimed_innovation=passport.claimed_innovation,
                        process_description=passport.process_description,
                        target_markets=passport.target_markets or [],
                        business_role=passport.business_role,
                        biological_resource_origin=passport.biological_resource_origin,
                        version=passport.version,
                        unresolved_clarifications=passport.unresolved_clarifications or [],
                    )
                    db.add(db_passport)
                else:
                    db_passport.case_title = passport.case_title
                    db_passport.product_form = passport.product_form
                    db_passport.dosage_form = passport.dosage_form
                    db_passport.intended_use = passport.intended_use
                    db_passport.proposed_claims = passport.proposed_claims or []
                    db_passport.claimed_innovation = passport.claimed_innovation
                    db_passport.process_description = passport.process_description
                    db_passport.target_markets = passport.target_markets or []
                    db_passport.business_role = passport.business_role
                    db_passport.biological_resource_origin = passport.biological_resource_origin
                    db_passport.version = passport.version
                    db_passport.unresolved_clarifications = passport.unresolved_clarifications or []

                db.flush()

                for ing in list(db_passport.ingredients):
                    db.delete(ing)
                db.flush()

                for ing in passport.ingredients:
                    db.add(IngredientDB(
                        passport_id=passport.id,
                        raw_name=ing.raw_name,
                        canonical_id=ing.canonical_id,
                        botanical_name=ing.botanical_name,
                        api_monograph_id=ing.api_monograph_id,
                        plant_part=ing.plant_part,
                        preparation_method=ing.preparation_method,
                        quantity_percentage=ing.quantity_percentage,
                        origin_status=ing.origin_status.value if hasattr(ing.origin_status, "value") else ing.origin_status,
                    ))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"Passport DB persistence skipped: {e}")

    @classmethod
    def _from_db(cls, db_passport: Any) -> InnovationPassport:
        ingredients = [
            IngredientEntry(
                raw_name=ing.raw_name,
                canonical_id=ing.canonical_id,
                botanical_name=ing.botanical_name,
                api_monograph_id=ing.api_monograph_id,
                plant_part=ing.plant_part or "Root",
                preparation_method=ing.preparation_method or "Aqueous Extract",
                quantity_percentage=ing.quantity_percentage or 0.0,
                origin_status=FactOrigin(ing.origin_status) if ing.origin_status else FactOrigin.USER_CONFIRMED,
            )
            for ing in db_passport.ingredients or []
        ]
        return InnovationPassport(
            id=db_passport.id,
            case_title=db_passport.case_title,
            product_form=db_passport.product_form or "Tablet",
            dosage_form=db_passport.dosage_form or "500mg Twice Daily",
            intended_use=db_passport.intended_use or "",
            proposed_claims=db_passport.proposed_claims or [],
            claimed_innovation=db_passport.claimed_innovation or "",
            process_description=db_passport.process_description or "",
            ingredients=ingredients,
            target_markets=db_passport.target_markets or [],
            business_role=db_passport.business_role or "",
            biological_resource_origin=db_passport.biological_resource_origin or "",
            version=db_passport.version or 1,
            unresolved_clarifications=db_passport.unresolved_clarifications or [],
        )

    @classmethod
    def get_passport(cls, passport_id: str) -> InnovationPassport | None:
        cached = cls._passports_store.get(passport_id)
        if cached is not None:
            return cached
        try:
            db = SessionLocal()
            try:
                db_passport = db.query(InnovationPassportDB).filter(
                    InnovationPassportDB.id == passport_id
                ).first()
                if db_passport:
                    passport = cls._from_db(db_passport)
                    cls._passports_store[passport_id] = passport
                    return passport
            finally:
                db.close()
        except Exception as e:
            print(f"Passport DB read skipped: {e}")
        return None

    @classmethod
    def update_passport(cls, passport: InnovationPassport) -> InnovationPassport:
        passport.version += 1
        cls._save_to_db(passport)
        cls._passports_store[passport.id] = passport
        return passport

    @classmethod
    def get_clarifications_for_passport(cls, passport: InnovationPassport) -> list[ClarificationQuery]:
        """
        Generates targeted clarification queries when a missing fact could change legal classification.
        """
        queries = []
        if "ingredients_unspecified" in passport.unresolved_clarifications:
            queries.append(ClarificationQuery(
                id="CLARIFY-INGREDIENTS",
                field_key="ingredients",
                question_text={
                    "en": "No botanical ingredients were detected in your description. Which herbs/ingredients does your formulation contain? (common name or botanical binomial)",
                    "hi": "आपके विवरण में कोई वनस्पति घटक नहीं मिला। आपके फॉर्मूलेशन में कौन से जड़ी-बूटियाँ/घटक हैं? (सामान्य नाम या वानस्पतिक नाम)",
                    "mr": "तुमच्या वर्णनात कोणतेही वनस्पती घटक आढळले नाहीत. तुमच्या फॉर्म्युलेशनमध्ये कोणत्या औषधी वनस्पती/घटकांचा समावेश आहे?"
                },
                options=[
                    "I will provide botanical names",
                    "Single-ingredient formulation",
                    "Multi-ingredient formulation"
                ],
                severity="DECISION_CRITICAL"
            ))
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
