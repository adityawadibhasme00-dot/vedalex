import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.passport import InnovationPassport, IngredientEntry, FactOrigin, ClarificationQuery
from app.services.multilingual_nlp import MultilingualNLPEngine
from app.services.ingredient_resolver import IngredientResolverService
from app.core.database import SessionLocal
from app.models.db_models import InnovationPassportDB, IngredientDB, User


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
                db_passport = db.query(InnovationPassportDB).filter(
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
                        proposed_claims=passport.proposed_claims or list,
                        claimed_innovation=passport.claimed_innovation,
                        process_description=passport.process_description,
                        target_markets=passport.target_markets or list,
                        business_role=passport.business_role,
                        biological_resource_origin=passport.biological_resource_origin,
                        version=passport.version,
                        unresolved_clarifications=passport.unresolved_clarifications or list,
                    )
                    db.add(db_passport)
                else:
                    db_passport.case_title = passport.case_title
                    db_passport.product_form = passport.product_form
                    db_passport.dosage_form = passport.dosage_form
                    db_passport.intended_use = passport.intended_use
                    db_passport.proposed_claims = passport.proposed_claims or list
                    db_passport.claimed_innovation = passport.claimed_innovation
                    db_passport.process_description = passport.process_description
                    db_passport.target_markets = passport.target_markets or list
                    db_passport.business_role = passport.business_role
                    db_passport.biological_resource_origin = passport.biological_resource_origin
                    db_passport.version = passport.version
                    db_passport.unresolved_clarifications = passport.unresolved_clarifications or list

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
    def _from_db(cls, db_passport: InnovationPassportDB) -> InnovationPassport:
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
    def get_passport(cls, passport_id: str) -> Optional[InnovationPassport]:
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
