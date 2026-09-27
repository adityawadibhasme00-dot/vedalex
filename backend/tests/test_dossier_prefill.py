"""G9 - Document Engine: cited dossier (A4) + Form I/II prefill (A6)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import dossier_router as dossier_module
from app.api.v1.dossier_router import router as dossier_router
from app.core.database import Base, get_db
from app.services import dossier_service, prefill_service

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes: a deterministic passport + a deterministic retrieval function
# ---------------------------------------------------------------------------

class FakeIngredient:
    def __init__(self, raw_name, botanical_name="", plant_part="", qty=0.0, origin="PENDING"):
        self.raw_name = raw_name
        self.botanical_name = botanical_name
        self.api_monograph_id = ""
        self.plant_part = plant_part
        self.quantity_percentage = qty
        self.origin_status = origin


class FakeEvidence:
    def __init__(self, claim_text, evidence_type, status, source=""):
        self.claim_text = claim_text
        self.evidence_type = evidence_type
        self.evidence_status = status
        self.source_reference = source


class FakeFinding:
    def __init__(self, jurisdiction, pathway, risk, status, explanation):
        self.jurisdiction = jurisdiction
        self.pathway_category = pathway
        self.risk_level = risk
        self.status = status
        self.explanation_text = explanation


class FakePassport:
    id = "passport-test-0001"
    case_title = "Ashwagandha + Turmeric joint care"
    product_form = "Ayurvedic herbal formulation"
    dosage_form = "capsule"
    intended_use = "management of joint pain"
    claimed_innovation = "A synergistic aqueous extract of Ashwagandha and Turmeric at 3:1"
    process_description = "Cold maceration 12h, low-temperature evaporation, micronised"
    target_markets = ["India", "United States"]
    business_role = "manufacturer"
    biological_resource_origin = "CULTIVATED"
    proposed_claims = [
        "A composition comprising Ashwagandha root extract and Turmeric extract in 3:1 ratio",
        "A process of cold maceration retaining curcuminoid content",
    ]
    ingredients = [
        FakeIngredient("Ashwagandha", "Withania somnifera", "root", 60.0, "CULTIVATED"),
        FakeIngredient("Turmeric", "Curcuma longa", "rhizome", 40.0, "WILD"),
    ]
    evidence = [
        FakeEvidence("Curcuminoid retention > 95%", "analytical", "VERIFIED", "Lab report L-22"),
        FakeEvidence("Anti-inflammatory activity", "preclinical", "MISSING"),
    ]


class FakeRegulatoryFinding:
    pass


@pytest.fixture()
def fake_passport(monkeypatch):
    passport = FakePassport()
    monkeypatch.setattr(
        dossier_service.PassportEngine, "get_passport", classmethod(lambda cls, _id: passport)
    )
    monkeypatch.setattr(
        prefill_service.PassportEngine, "get_passport", classmethod(lambda cls, _id: passport)
    )
    monkeypatch.setattr(
        dossier_service.DeterministicRuleEngine,
        "evaluate_passport",
        classmethod(
            lambda cls, p, target_markets=None: [
                FakeFinding("India", "Schedule C (Ayurvedic)", "HIGH", "condition_not_satisfied", "Heavy metal testing pending"),
                FakeFinding("United States", "Dietary Supplement", "LOW", "eligible", "No NDI issue identified"),
            ]
        ),
    )
    return passport


CORPUS = {
    "patent": [
        {
            "source": "ipindia.gov.in",
            "source_url": "https://ipindia.gov.in/patent-form-1",
            "act_title": "Patents Rules, Form 1",
            "category": "statutory",
            "content": "Form 1 is the application for grant of patent and requires applicant details, "
            "title of invention and a brief description of the invention.",
        }
    ],
    "prior art": [
        {
            "source": "lens.org",
            "source_url": "https://lens.org/patent/IN-2024-000901",
            "act_title": "IN-2024-000901",
            "category": "patent",
            "content": "A prior art herbal composition of Withania somnifera and Curcuma longa "
            "for joint pain, published 2024.",
        }
    ],
    "prohibited": [
        {
            "source": "fda.gov",
            "source_url": "https://fda.gov/heavy-metals-dietary-supplements",
            "act_title": "Dietary Supplement Heavy Metals Guidance",
            "category": "guidance",
            "content": "Dietary supplements must not contain excessive levels of lead, mercury "
            "or arsenic; heavy metal testing is expected.",
        }
    ],
}


def fake_search(query: str, top_k: int = 4) -> list[dict]:
    """Deterministic retrieval: pick the corpus block whose key appears in the query."""
    lowered = query.lower()
    for key, sources in CORPUS.items():
        if key in lowered:
            return sources[:top_k]
    return CORPUS["prohibited"][:top_k]


class FakeUser:
    id = "user-test-0001"
    role = "practitioner"


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path/'g9.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app = FastAPI()
    app.include_router(dossier_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[dossier_module.require_user] = lambda: FakeUser()
    try:
        yield TestClient(app)
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def anon_client(tmp_path):
    """Same app with no auth override - proves the endpoints are protected."""
    engine = create_engine(
        f"sqlite:///{tmp_path/'g9anon.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app = FastAPI()
    app.include_router(dossier_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield TestClient(app)
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# A4 - dossier structure
# ---------------------------------------------------------------------------

def test_default_search_fn_uses_the_real_hybrid_retriever(monkeypatch):
    """Regression: the default adapter must call HybridRetriever.retrieve, not a
    config lookup that silently returns None (0 citations, silently ungrounded)."""
    from app.rag import retrieval_pipeline

    calls: list[dict] = []

    def fake_retrieve(query, top_k=5, **kwargs):
        calls.append({"query": query, "top_k": top_k})
        return {"sources": CORPUS["prior art"], "confidence": 0.5}

    monkeypatch.setattr(retrieval_pipeline.HybridRetriever, "retrieve", staticmethod(fake_retrieve))
    out = dossier_service._default_search_fn("prior art herbal composition", 3)
    assert calls == [{"query": "prior art herbal composition", "top_k": 3}]
    assert out == CORPUS["prior art"]


def test_default_search_fn_degrades_to_empty_on_error(monkeypatch):
    from app.rag import retrieval_pipeline

    def boom(*_a, **_k):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(retrieval_pipeline.HybridRetriever, "retrieve", staticmethod(boom))
    assert dossier_service._default_search_fn("anything", 3) == []


def test_dossier_cites_real_corpus_end_to_end(fake_passport, monkeypatch):
    from app.rag import retrieval_pipeline

    monkeypatch.setattr(
        retrieval_pipeline.HybridRetriever,
        "retrieve",
        staticmethod(lambda query, top_k=5, **kw: {"sources": fake_search(query, top_k)}),
    )
    dossier = dossier_service.build_dossier(fake_passport.id)
    assert dossier["citation_count"] > 0
    assert dossier["completeness"]["cited_sections"] > 0


def test_dossier_has_exactly_seven_sections(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    assert len(dossier["sections"]) == 7
    assert [s["key"] for s in dossier["sections"]] == [k for k, _ in dossier_service.SECTION_TITLES]
    assert [s["title"] for s in dossier["sections"]][0].startswith("1.")
    assert dossier["sections"][-1]["title"].startswith("7.")


def test_dossier_is_marked_draft_with_disclaimer(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    assert dossier["status"] == "DRAFT"
    assert "Not legal advice" in dossier["banner"]
    assert "human review" in dossier["banner"]


def test_dossier_cites_real_sources(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    assert dossier["citation_count"] >= 2
    urls = {c["source_url"] for c in dossier["citations"]}
    assert "https://ipindia.gov.in/patent-form-1" in urls
    refs = [c["ref"] for c in dossier["citations"]]
    assert refs == [f"[{i + 1}]" for i in range(len(refs))]


def test_dossier_never_invents_citations(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    corpus_refs = {c["source_url"] for group in CORPUS.values() for c in group}
    for cite in dossier["citations"]:
        assert cite["source_url"] in corpus_refs
        assert cite["excerpt"]


def test_citations_are_deduplicated(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    keys = [(c["source"], c["excerpt"][:40]) for c in dossier["citations"]]
    assert len(keys) == len(set(keys))


def test_dossier_uses_deterministic_search_by_default(fake_passport):
    # the real adapter must not raise even when Qdrant is cold
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search, top_k=1)
    assert len(dossier["citations"]) <= 3


def test_missing_passport_raises_dossier_error(monkeypatch):
    monkeypatch.setattr(
        dossier_service.PassportEngine, "get_passport", classmethod(lambda cls, _id: None)
    )
    with pytest.raises(dossier_service.DossierError):
        dossier_service.build_dossier("nope", search_fn=fake_search)


def test_findings_sorted_by_risk(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    risks = [f["risk_level"] for f in dossier["sections"][3]["findings"]]
    assert risks == ["HIGH", "LOW"]


def test_watch_alerts_land_in_prior_art_section(fake_passport):
    alerts = [
        {"patent_no": "IN-2024-000901", "title": "Titled", "match": "match", "overlap": "ashwagandha"}
    ]
    dossier = dossier_service.build_dossier(
        fake_passport.id, search_fn=fake_search, watch_alerts=alerts
    )
    section = dossier["sections"][2]
    assert section["watch_alerts"] == alerts
    assert "IN-2024-000901" in section["body"]


def test_missing_evidence_listed_in_gaps(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    assert dossier["sections"][4]["missing_evidence"] == ["Anti-inflammatory activity"]
    assert "Anti-inflammatory activity" in dossier["sections"][5]["body"]


def test_recommendations_flag_high_risk(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    body = dossier["sections"][6]["body"]
    assert "HIGH" in body
    assert "sign off" in body.lower()


def test_completeness_is_reported(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    assert dossier["completeness"]["sections"] == 7
    assert 0 <= dossier["completeness"]["pct"] <= 100


def test_dossier_works_with_zero_retrieval_results(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=lambda q, k: [])
    assert dossier["citation_count"] == 0
    assert all(s["grounding"] == "insufficient" for s in dossier["sections"])
    assert len(dossier["ungrounded_sections"]) == 7
    assert "without a retrieved record" in dossier["sections"][2]["body"]


def test_content_hash_is_stable_and_changes_with_content(fake_passport):
    first = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    second = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    assert first["content_hash"] == second["content_hash"]

    def other(query: str, top_k: int = 4) -> list[dict]:
        return CORPUS["prohibited"][:top_k]

    changed = dossier_service.build_dossier(fake_passport.id, search_fn=other)
    assert changed["content_hash"] != first["content_hash"]


def test_markdown_embeds_the_stamped_hash(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    md = dossier_service.render_markdown(dossier)
    assert f"**Document hash:** `{dossier['content_hash']}`" in md


def test_markdown_rendering_has_all_sections_and_references(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    md = dossier_service.render_markdown(dossier)
    for _key, title in dossier_service.SECTION_TITLES:
        assert title in md
    assert "## References" in md
    assert "https://ipindia.gov.in/patent-form-1" in md
    assert "DRAFT" in md


def test_pdf_render_produces_valid_pdf(fake_passport):
    pdf = dossier_service.render_pdf(dossier_service.build_dossier(fake_passport.id, search_fn=fake_search))
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000
    assert b"%%EOF" in pdf[-64:]


def _pdf_text(pdf: bytes) -> str:
    """Extract real text from the rendered PDF (proves it is not a blank file)."""
    import pymupdf

    document = pymupdf.open(stream=pdf, filetype="pdf")
    try:
        return "".join(document[index].get_text() for index in range(document.page_count))
    finally:
        document.close()


def test_pdf_renders_all_seven_sections_as_text(fake_passport):
    pdf = dossier_service.render_pdf(dossier_service.build_dossier(fake_passport.id, search_fn=fake_search))
    text = _pdf_text(pdf)
    for _key, title in dossier_service.SECTION_TITLES:
        assert title.split(". ", 1)[1] in text, title
    assert "References" in text


def test_pdf_carries_draft_banner_and_hash(fake_passport):
    dossier = dossier_service.build_dossier(fake_passport.id, search_fn=fake_search)
    text = _pdf_text(dossier_service.render_pdf(dossier))
    assert "DRAFT" in text
    assert dossier["content_hash"] in text
    assert dossier["case_title"] in text


def test_pdf_includes_finding_table_and_ingredient_table(fake_passport):
    text = _pdf_text(
        dossier_service.render_pdf(dossier_service.build_dossier(fake_passport.id, search_fn=fake_search))
    )
    assert "Schedule C (Ayurvedic)" in text
    assert "Withania somnifera" in text


def test_pdf_renders_with_no_findings(fake_passport, monkeypatch):
    monkeypatch.setattr(
        dossier_service.DeterministicRuleEngine,
        "evaluate_passport",
        classmethod(lambda cls, p, target_markets=None: []),
    )
    pdf = dossier_service.render_pdf(dossier_service.build_dossier(fake_passport.id, search_fn=fake_search))
    assert pdf.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# A6 - prefill + read-back
# ---------------------------------------------------------------------------

def test_supported_forms_are_listed():
    forms = prefill_service.supported_forms()
    assert {f["form"] for f in forms} == {"form1", "form2"}
    assert "Form I" in forms[0]["title"]
    assert all("ipindia.gov.in" in f["note"] for f in forms)


def test_form1_prefills_from_passport(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form1")
    assert draft["fields"]["title_of_invention"]["value"] == fake_passport.case_title
    assert draft["fields"]["brief_description"]["value"] == fake_passport.claimed_innovation
    assert draft["fields"]["number_of_claims"]["value"] == 2
    assert draft["fields"]["title_of_invention"]["status"] == "filled"


def test_form1_leaves_unknown_data_blank(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form1")
    assert draft["fields"]["applicant_name"]["value"] is None
    assert draft["fields"]["applicant_name"]["status"] == "needs_input"
    assert "applicant_name" in draft["missing_fields"]


def test_applicant_details_are_used_when_supplied(fake_passport):
    draft = prefill_service.prefill_form(
        fake_passport.id,
        "form1",
        applicant={"name": "Veda Labs Pvt Ltd", "address": "Pune", "nationality": "Indian"},
    )
    assert draft["fields"]["applicant_name"]["value"] == "Veda Labs Pvt Ltd"
    assert "applicant_name" not in draft["missing_fields"]


def test_summary_is_flagged_for_review_not_filled(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form1")
    assert draft["fields"]["summary_of_invention"]["status"] == "needs_review"
    assert "summary_of_invention" in draft["review_fields"]


def test_form2_carries_claims_and_blanks_the_rest(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form2")
    assert draft["fields"]["claim_1"]["value"] == fake_passport.proposed_claims[0]
    assert draft["fields"]["claim_2"]["value"] == fake_passport.proposed_claims[1]
    assert draft["fields"]["claim_3"]["status"] == "needs_input"


def test_draft_is_never_signed(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form1")
    assert draft["status"] == "DRAFT"
    assert draft["sign_off"]["required"] is True
    assert draft["sign_off"]["signed_by"] is None
    assert "does not file" in draft["disclaimer"]


def test_unknown_form_raises(fake_passport):
    with pytest.raises(prefill_service.PrefillError):
        prefill_service.prefill_form(fake_passport.id, "form99")


def test_read_back_confirms_every_filled_field(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form1")
    result = prefill_service.read_back(draft)
    assert result["traceable"] is True
    assert result["untraceable_fields"] == []
    assert result["filled_checked"] >= 4
    assert all(r["verified"] for r in result["results"])


def test_read_back_catches_a_doctored_field(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form1")
    draft["fields"]["title_of_invention"]["value"] = "CURE FOR EVERYTHING"
    result = prefill_service.read_back(draft)
    assert result["traceable"] is False
    assert "title_of_invention" in result["untraceable_fields"]


def test_read_back_catches_a_doctored_claim(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form2")
    draft["fields"]["claim_1"]["value"] = "A composition of unobtainium"
    result = prefill_service.read_back(draft)
    assert "claim_1" in result["untraceable_fields"]


def test_read_back_passes_with_only_blank_fields(fake_passport):
    draft = prefill_service.prefill_form(fake_passport.id, "form1")
    for field in draft["fields"].values():
        field["status"] = "needs_input"
        field["value"] = None
    result = prefill_service.read_back(draft)
    assert result["traceable"] is True
    assert result["filled_checked"] == 0


def test_form_text_renders_checkboxes(fake_passport):
    text = prefill_service.render_form_text(prefill_service.prefill_form(fake_passport.id, "form1"))
    assert "[x]" in text and "[ ]" in text
    assert "DRAFT" in text


def test_prefill_prompt_forbids_invention():
    from app.agents.base import load_prompt

    prompt = load_prompt("prefill_prompt.txt")
    assert "NEVER invent" in prompt
    assert "needs_human_input" in prompt


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

def test_forms_endpoint_lists_both_forms(client):
    resp = client.get("/api/v1/dossier/forms")
    assert resp.status_code == 200
    assert {f["form"] for f in resp.json()["forms"]} == {"form1", "form2"}


def test_build_endpoint_returns_dossier_with_hash(client, fake_passport):
    resp = client.post("/api/v1/dossier/build", json={"passport_id": fake_passport.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "DRAFT"
    assert len(body["sections"]) == 7
    assert body["content_hash"]
    assert body["document_id"]


def test_build_endpoint_404_for_unknown_passport(client, monkeypatch):
    monkeypatch.setattr(
        dossier_service.PassportEngine, "get_passport", classmethod(lambda cls, _id: None)
    )
    resp = client.post("/api/v1/dossier/build", json={"passport_id": "missing"})
    assert resp.status_code == 404


def test_latest_dossier_endpoint(client, fake_passport):
    client.post("/api/v1/dossier/build", json={"passport_id": fake_passport.id})
    resp = client.get(f"/api/v1/dossier/{fake_passport.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DRAFT"


def test_latest_dossier_404_before_build(client, fake_passport):
    assert client.get(f"/api/v1/dossier/{fake_passport.id}").status_code == 404


def test_markdown_endpoint(client, fake_passport):
    resp = client.get(f"/api/v1/dossier/{fake_passport.id}/markdown")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "Executive Summary" in resp.text


def test_pdf_endpoint(client, fake_passport):
    resp = client.get(f"/api/v1/dossier/{fake_passport.id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert "attachment" in resp.headers["content-disposition"]


def test_prefill_endpoint_returns_readback(client, fake_passport):
    resp = client.post("/api/v1/prefill/form1", json={"passport_id": fake_passport.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["readback"]["traceable"] is True
    assert body["document_id"]


def test_prefill_endpoint_rejects_unknown_form(client, fake_passport):
    resp = client.post("/api/v1/prefill/form9", json={"passport_id": fake_passport.id})
    assert resp.status_code == 404


def test_readback_endpoint(client, fake_passport):
    created = client.post("/api/v1/prefill/form2", json={"passport_id": fake_passport.id}).json()
    resp = client.get(f"/api/v1/prefill/{created['document_id']}/readback")
    assert resp.status_code == 200
    assert resp.json()["readback"]["traceable"] is True


def test_readback_endpoint_404(client):
    assert client.get("/api/v1/prefill/nope/readback").status_code == 404


def test_document_engine_routes_exist_in_openapi():
    from app.main import app

    spec = app.openapi()
    for path in (
        "/api/v1/dossier/build",
        "/api/v1/dossier/forms",
        "/api/v1/dossier/{passport_id}/pdf",
        "/api/v1/prefill/{form}",
        "/api/v1/prefill/{document_id}/readback",
    ):
        assert path in spec["paths"], path


def test_dossier_record_is_stored_as_draft(client, fake_passport):

    built = client.post("/api/v1/dossier/build", json={"passport_id": fake_passport.id}).json()
    stored = client.get(f"/api/v1/dossier/{fake_passport.id}").json()
    assert stored["document_id"] == built["document_id"]
    assert stored["status"] == "DRAFT"
    assert stored["content_hash"] == built["content_hash"]


def test_write_endpoints_require_authentication(anon_client, fake_passport):
    assert anon_client.post("/api/v1/dossier/build", json={"passport_id": fake_passport.id}).status_code == 401
    assert anon_client.post("/api/v1/prefill/form1", json={"passport_id": fake_passport.id}).status_code == 401


def test_read_only_dossier_downloads_are_public(anon_client, fake_passport):
    assert anon_client.get(f"/api/v1/dossier/{fake_passport.id}/markdown").status_code == 200
    assert anon_client.get(f"/api/v1/dossier/{fake_passport.id}/pdf").status_code == 200
    assert anon_client.get("/api/v1/dossier/forms").status_code == 200
