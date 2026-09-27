import factory

from app.models.db_models import User


class UserFactory(factory.Factory):
    class Meta:
        model = User

    name = factory.Faker("name")
    email = factory.LazyAttribute(lambda sequence: f"test-user-{sequence}@example.test")
    role = "researcher"
    institution = factory.Faker("company")
    is_active = True
    hashed_password: str


class PassportPayloadFactory(factory.Factory):
    class Meta:
        model = dict

    raw_text = (
        "Ashwagandha and Brahmi aqueous extract capsule for a traditional wellness use, "
        "target markets India and the United States, no therapeutic claim"
    )
    user_lang = "en"
    case_title = "Ashwagandha Test Formulation"
    product_type = "Herbal Supplement"
    category = "botanical formulation"
    target_markets = ["India", "United States"]
    extraction_method = "Aqueous extraction"
    solvent = "Water"
    temperature = "80 C"
    time = "4 hours"
    processing_steps = "Filter, concentrate, spray dry"
    proposed_claims = ["supports general wellness"]


class RagDocumentFactory(factory.Factory):
    class Meta:
        model = dict

    document_id = factory.Sequence(lambda sequence: f"test-doc-{sequence}")
    text = "Synthetic statutory text for deterministic retrieval tests."
    title = "Synthetic Legal Source"
    source = "test-corpus"
    category = "regulations"
    authority = "test-authority"
    jurisdiction = "India"
    year = 2026
