from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.confidence import ConfidenceBand
from app.models.db_models import User, generate_uuid
from app.models.innolab_models import InnolabProjectDB, InnolabRunDB, InnolabRunStepDB
from app.models.intelligence import (
    ABSBenefitSharing,
    ABSComplianceResponse,
    BioResourcePlant,
    CITESSchedule,
    ClaimSafetyAnalysisResponse,
    ClaimSafetyResult,
    ClaimSafetySignal,
    ClassifierEvidence,
    EvidenceLadderCell,
    EvidenceQualityIntelligenceResponse,
    ExportGap,
    ExportReadinessResponse,
    GeoOrigin,
    IngredientIntelligence,
    InnovationGraphIngredient,
    InnovationKnowledgeGraphResponse,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    MarketReadinessItem,
    MisleadingAdRisk,
    PathwayScore,
    ProductClassifierResponse,
    QualityParameter,
    RuleValidationCheck,
    SelectedInnovationInfo,
    TerminologyMapResponse,
)
from app.models.passport import (
    ClarificationQuery,
    FactItem,
    FactOrigin,
    IngredientEntry,
    InnovationPassport,
)
from app.models.regulatory import (
    AssessmentResponse,
    RegulatoryFinding,
    RuleConditionState,
    StatutoryCitation,
)
from tests.factories import UserFactory

FACT_ORIGIN_VALUES = frozenset(
    {"user_confirmed", "document_extracted", "inferred", "unknown"}
)
RULE_CONDITION_VALUES = frozenset(
    {"condition_satisfied", "condition_not_satisfied", "insufficient_information"}
)
CONFIDENCE_BAND_VALUES = frozenset({"HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE"})


def _build_model(model, **kwargs):
    return model(**kwargs)


def _citation(**overrides) -> StatutoryCitation:
    payload: dict[str, Any] = {
        "act_title": "Food Safety and Standards Act, 2006",
        "section_reference": "3(1)(m)",
        "authority": "FSSAI",
        "effective_date": "2022-06-12",
        "exact_passage": "A food business operator shall comply with the general requirements.",
        "source_url": "https://example.test/fssai/act",
        "authority_rank": 1,
    }
    payload.update(overrides)
    return StatutoryCitation(**payload)


def _finding(**overrides) -> RegulatoryFinding:
    payload: dict[str, Any] = {
        "jurisdiction": "India",
        "pathway_category": "Ayurveda Aahara (FSSAI 2022)",
        "status": RuleConditionState.SATISFIED,
        "confidence": ConfidenceBand.HIGH,
        "conditions_evaluated": ["claim_is_non_therapeutic"],
        "supporting_citations": [_citation()],
        "missing_facts": [],
        "next_action_steps": ["Attach FSSAI registration copy"],
        "coverage_limitations": "State licensing rules were not evaluated.",
        "assumptions_made": ["applicant holds a valid FSSAI registration"],
        "explanation_text": "All evaluated conditions are satisfied.",
        "risk_level": "low",
        "requires_human_review": False,
        "applied_rules": [{"rule_id": "fssai_aahara_01", "outcome": "satisfied"}],
    }
    payload.update(overrides)
    return RegulatoryFinding(**payload)


def _passport_instance() -> InnovationPassport:
    return InnovationPassport(
        case_title="Ashwagandha Tablet",
        product_form="Tablet",
        proposed_claims=["supports general wellness"],
        ingredients=[
            IngredientEntry(
                raw_name="Ashwagandha",
                botanical_name="Withania somnifera",
                quantity_percentage=42.5,
            )
        ],
        target_markets=["India", "United States"],
        unresolved_clarifications=["Confirm extract ratio"],
    )


def _claim_safety_response() -> ClaimSafetyAnalysisResponse:
    return ClaimSafetyAnalysisResponse(
        passport_id="passport-1",
        overall_verdict="WARNING",
        overall_color="yellow",
        claims=[
            ClaimSafetyResult(
                claim_text="supports general wellness",
                claim_category="wellness",
                evidence_alignment="partial",
                risk_level="WARNING",
                risk_color="yellow",
                regulation="FSSAI Codex",
                note="Keep the claim non-therapeutic.",
            )
        ],
        safety_signals=[
            ClaimSafetySignal(
                ingredient="Ashwagandha",
                botanical_name="Withania somnifera",
                signal="may cause sedation",
                severity="MEDIUM",
                evidence_source="API monograph",
                precaution="Avoid with sedatives.",
            )
        ],
        misleading_ad_risk=MisleadingAdRisk(
            flagged_phrases=["cures"],
            act_citation="DRUGS AND MAGIC REMEDIES ACT 1954",
            action="Remove the cure claim",
        ),
        summary="One claim needs rewording.",
        disclaimer="Informational only.",
    )


def _classifier_response() -> ProductClassifierResponse:
    return ProductClassifierResponse(
        passport_id="passport-1",
        product_name="Ashwagandha Tablet",
        likely_pathway="ayurveda_aahara",
        pathway_category="ayurveda_aahara",
        pathway_confidence="HIGH",
        alternative_pathways=[PathwayScore(pathway="proprietary_ayurveda", score=40)],
        evidence=[
            ClassifierEvidence(
                collection="regulations",
                title="FSSAI Aahara",
                passage="Ayurveda Aahara means food prepared as per Ayurvedic principles.",
                source="FSSAI",
            )
        ],
        rule_validation=[
            RuleValidationCheck(
                rule="section_3p",
                status="SATISFIED",
                verdict="Compliant",
                reason="No therapeutic claim present.",
                source="Patents Act 1970",
            )
        ],
        disclaimer="Classification support only.",
    )


def _bio_resource_plant() -> BioResourcePlant:
    return BioResourcePlant(
        canonical_id="ing-ashwagandha",
        botanical_name="Withania somnifera",
        family="Solanaceae",
        plant_parts=["Root"],
        english_names=["Winter Cherry"],
        geography=[GeoOrigin(state="Rajasthan", status="verified", note="Cultivated", source="survey")],
        evidence_support_pct=70,
        cites=CITESSchedule(
            latin_name="Withania somnifera",
            appendix="",
            impact="Not listed.",
            permit_requirement="None",
        ),
    )


def _export_readiness() -> ExportReadinessResponse:
    return ExportReadinessResponse(
        passport_id="passport-1",
        markets=[
            MarketReadinessItem(
                market="United States",
                flag="US",
                overall_status="partial",
                readiness_pct=60,
                gaps=[
                    ExportGap(
                        area="Labelling",
                        requirement="Supplement Facts panel",
                        status="partial",
                        action="Add panel",
                        source="FDA 21 CFR 101",
                    )
                ],
            )
        ],
        summary="Two gaps remain.",
        next_actions=["Add Supplement Facts panel"],
        disclaimer="Readiness estimate only.",
    )


def _evidence_quality() -> EvidenceQualityIntelligenceResponse:
    return EvidenceQualityIntelligenceResponse(
        passport_id="passport-1",
        ingredients=[
            IngredientIntelligence(
                canonical_id="ing-ashwagandha",
                botanical_name="Withania somnifera",
                api_monograph_id="ashwagandha-mono",
                evidence_ladder=[
                    EvidenceLadderCell(
                        level="traditional_use",
                        level_label="Traditional use",
                        support_status="documented",
                        support_pct=80,
                        note="Classical texts reference it.",
                    )
                ],
                evidence_support_pct=80,
                quality_readiness_pct=55,
                quality_gaps=["HPLC fingerprint"],
            )
        ],
        overall_evidence_support_pct=80,
        overall_quality_readiness_pct=55,
        disclaimer="Evidence summary only.",
    )


def _abs_response() -> ABSComplianceResponse:
    return ABSComplianceResponse(
        status="compliance_required",
        user_type="manufacturer",
        turnover_inr=40000000.0,
        commercial_use=True,
        benefit_sharing=ABSBenefitSharing(
            applicable=True, rate_pct=0.2, amount_inr=80000.0, basis="0.2% of turnover"
        ),
        obligations=[],
        required_approvals=["NBA prior intimation"],
        disclaimer="Not legal advice.",
    )


def _innovation_graph_response() -> InnovationKnowledgeGraphResponse:
    return InnovationKnowledgeGraphResponse(
        selected_innovation=SelectedInnovationInfo(
            title="Ashwagandha Tablet",
            kind="Single Herb",
            ingredients=[InnovationGraphIngredient(raw_name="Ashwagandha", monographed=True)],
        ),
        nodes=[
            KnowledgeGraphNode(id="n1", label="Ashwagandha", category="ingredient"),
            KnowledgeGraphNode(id="n2", label="Withania somnifera", category="botanical"),
        ],
        edges=[KnowledgeGraphEdge(**{"from": "n1"}, to="n2", label="canonical_for")],
        collections_used=["biodiversity"],
        disclaimer="Graph preview only.",
    )


def _terminology_response() -> TerminologyMapResponse:
    return TerminologyMapResponse(
        query="ashwagandha",
        matched=True,
        matched_via="synonym",
        canonical_id="ing-ashwagandha",
        botanical_name="Withania somnifera",
        family="Solanaceae",
        names={"en": ["Ashwagandha"], "hi": ["अश्वगंधा"]},
        transliterations=["aśvagandhā"],
        nearest_possible=["Ashwagandha"],
        source="glossary",
    )


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _build_model(FactItem), id="FactItem-missing-value"),
        pytest.param(lambda: _build_model(IngredientEntry), id="IngredientEntry-missing-raw_name"),
        pytest.param(
            lambda: _build_model(ClarificationQuery, id="cq-1", field_key="target_markets"),
            id="ClarificationQuery-missing-question_text-options",
        ),
        pytest.param(
            lambda: _build_model(StatutoryCitation, act_title="Food Safety and Standards Act, 2006"),
            id="StatutoryCitation-missing-four-fields",
        ),
        pytest.param(
            lambda: _build_model(
                RegulatoryFinding,
                jurisdiction="India",
                pathway_category="Ayurveda Aahara (FSSAI 2022)",
                status=RuleConditionState.SATISFIED,
                confidence=ConfidenceBand.HIGH,
                conditions_evaluated=[],
            ),
            id="RegulatoryFinding-missing-coverage_limitations",
        ),
        pytest.param(lambda: _build_model(ClaimSafetySignal, ingredient="x"), id="ClaimSafetySignal-missing-fields"),
        pytest.param(lambda: _build_model(ClaimSafetyResult, claim_text="x"), id="ClaimSafetyResult-missing-fields"),
        pytest.param(lambda: _build_model(MisleadingAdRisk), id="MisleadingAdRisk-missing-fields"),
        pytest.param(lambda: _build_model(GeoOrigin, state="Rajasthan"), id="GeoOrigin-missing-fields"),
        pytest.param(
            lambda: _build_model(QualityParameter, param_name="moisture"),
            id="QualityParameter-missing-fields",
        ),
        pytest.param(
            lambda: _build_model(EvidenceQualityIntelligenceResponse, passport_id="passport-1"),
            id="EvidenceQualityIntelligenceResponse-missing-disclaimer",
        ),
        pytest.param(
            lambda: _build_model(ABSComplianceResponse, status="exempt"),
            id="ABSComplianceResponse-missing-benefit_sharing",
        ),
        pytest.param(
            lambda: _build_model(KnowledgeGraphEdge, to="n2", label="canonical_for"),
            id="KnowledgeGraphEdge-missing-from",
        ),
        pytest.param(
            lambda: _build_model(BioResourcePlant),
            id="BioResourcePlant-missing-canonical_id-botanical_name",
        ),
    ],
)
def test_required_fields_reject_missing_input(build) -> None:
    with pytest.raises(ValidationError):
        build()


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _build_model(InnovationPassport, proposed_claims="wellness"), id="proposed_claims-str-not-list"),
        pytest.param(lambda: _build_model(InnovationPassport, version=3.7), id="version-float-not-int"),
        pytest.param(lambda: _build_model(FactItem, confidence="high"), id="confidence-str-not-float"),
        pytest.param(
            lambda: _build_model(ClarificationQuery, id="cq-1", field_key="k", question_text="q", options=["o"]),
            id="question_text-str-not-dict",
        ),
        pytest.param(
            lambda: _build_model(ClarificationQuery, id="cq-1", field_key="k", question_text={"en": "q"}, options="India"),
            id="options-str-not-list",
        ),
        pytest.param(
            lambda: _build_model(
                AssessmentResponse,
                assessment_id="a-1",
                passport_id="p-1",
                timestamp="2026-09-06T19:00:00Z",
                language="en",
                findings="none",
            ),
            id="findings-str-not-list",
        ),
        pytest.param(
            lambda: _build_model(
                RegulatoryFinding,
                jurisdiction="India",
                pathway_category="x",
                status="banana",
                confidence=ConfidenceBand.HIGH,
                conditions_evaluated=[],
                coverage_limitations="",
            ),
            id="status-not-rule-condition-state",
        ),
        pytest.param(
            lambda: _build_model(
                RegulatoryFinding,
                jurisdiction="India",
                pathway_category="x",
                status=RuleConditionState.SATISFIED,
                confidence="CERTAIN",
                conditions_evaluated=[],
                coverage_limitations="",
            ),
            id="confidence-not-confidence-band",
        ),
    ],
)
def test_invalid_types_are_rejected(build) -> None:
    with pytest.raises(ValidationError):
        build()


def test_extra_fields_are_dropped_by_default() -> None:
    passport = _build_model(InnovationPassport, unexpected_key="value", another_key=5)
    assert passport.model_extra is None
    assert "unexpected_key" not in passport.model_dump()
    assert "unexpected_key" not in passport.model_fields_set


def test_extra_fields_are_dropped_on_nested_models() -> None:
    citation = _citation(extra_citation_key="value")
    assert citation.model_extra is None
    assert "extra_citation_key" not in citation.model_dump()


def test_extra_fields_are_dropped_on_alias_model() -> None:
    edge = _build_model(KnowledgeGraphEdge, **{"from": "n1"}, to="n2", label="canonical_for", stray="x")
    assert edge.model_extra is None
    assert "stray" not in edge.model_dump()
    assert "stray" not in edge.model_dump(by_alias=True)


ROUND_TRIP_CASES = [
    pytest.param(InnovationPassport, _passport_instance(), id="passport"),
    pytest.param(FactItem, FactItem(value={"marker": 1}, origin=FactOrigin.INFERRED, confidence=0.4), id="factitem-dict-value"),
    pytest.param(
        FactItem,
        FactItem(value=datetime(2026, 9, 6, 19, 0, 0, tzinfo=UTC), origin=FactOrigin.DOCUMENT_EXTRACTED),
        id="factitem-datetime-value",
    ),
    pytest.param(IngredientEntry, IngredientEntry(raw_name="Brahmi", quantity_percentage=12.5), id="ingredient-entry"),
    pytest.param(
        ClarificationQuery,
        ClarificationQuery(
            id="cq-1",
            field_key="target_markets",
            question_text={"en": "Which markets?", "hi": "कौन से बाजार?"},
            options=["India", "United States"],
            severity="ADVISORY",
        ),
        id="clarification-query",
    ),
    pytest.param(StatutoryCitation, _citation(), id="statutory-citation"),
    pytest.param(RegulatoryFinding, _finding(), id="regulatory-finding"),
    pytest.param(
        AssessmentResponse,
        AssessmentResponse(
            assessment_id="as-1",
            passport_id="p-1",
            timestamp="2026-09-06T19:00:00Z",
            language="en",
            findings=[_finding()],
            coverage_meter_score=82,
            unsupported_claim_rate=0.25,
        ),
        id="assessment-response",
    ),
    pytest.param(
        ClaimSafetySignal,
        ClaimSafetySignal(
            ingredient="Ashwagandha",
            botanical_name="Withania somnifera",
            signal="sedation",
            severity="HIGH",
            evidence_source="monograph",
            precaution="Avoid with sedatives.",
        ),
        id="claim-safety-signal",
    ),
    pytest.param(
        ClaimSafetyResult,
        ClaimSafetyResult(
            claim_text="supports general wellness",
            claim_category="wellness",
            evidence_alignment="partial",
            risk_level="WARNING",
            risk_color="yellow",
            regulation="FSSAI Codex",
            note="Reword the claim.",
        ),
        id="claim-safety-result",
    ),
    pytest.param(ClaimSafetyAnalysisResponse, _claim_safety_response(), id="claim-safety-analysis"),
    pytest.param(ProductClassifierResponse, _classifier_response(), id="product-classifier"),
    pytest.param(ABSComplianceResponse, _abs_response(), id="abs-compliance"),
    pytest.param(
        BioResourcePlant,
        _bio_resource_plant(),
        id="bio-resource-plant",
    ),
    pytest.param(ExportReadinessResponse, _export_readiness(), id="export-readiness"),
    pytest.param(EvidenceQualityIntelligenceResponse, _evidence_quality(), id="evidence-quality"),
    pytest.param(InnovationKnowledgeGraphResponse, _innovation_graph_response(), id="innovation-graph"),
    pytest.param(TerminologyMapResponse, _terminology_response(), id="terminology-map"),
    pytest.param(
        KnowledgeGraphEdge,
        KnowledgeGraphEdge(**{"from": "n1"}, to="n2", label="canonical_for"),
        id="knowledge-graph-edge",
    ),
]


@pytest.mark.parametrize("model,instance", ROUND_TRIP_CASES)
def test_schema_round_trip(model, instance) -> None:
    assert model.model_validate(instance.model_dump()) == instance


def test_schema_round_trip_by_alias() -> None:
    edge = KnowledgeGraphEdge(**{"from": "n1"}, to="n2", label="canonical_for")
    assert KnowledgeGraphEdge.model_validate(edge.model_dump(by_alias=True)) == edge


def test_innovation_passport_defaults_are_not_shared_between_instances() -> None:
    first = InnovationPassport()
    first.target_markets.append("Germany")
    second = InnovationPassport()
    assert second.target_markets == ["India", "United States", "Canada"]
    assert first.proposed_claims is not second.proposed_claims


def test_fact_origin_allowed_values() -> None:
    assert {member.value for member in FactOrigin} == FACT_ORIGIN_VALUES


def test_rule_condition_state_allowed_values() -> None:
    assert {member.value for member in RuleConditionState} == RULE_CONDITION_VALUES


def test_confidence_band_allowed_values() -> None:
    assert {member.value for member in ConfidenceBand} == CONFIDENCE_BAND_VALUES


@pytest.mark.parametrize("raw_value", sorted({"", "USER_CONFIRMED", "confirmed", "user-confirmed"}))
def test_fact_origin_rejects_out_of_domain_values(raw_value) -> None:
    with pytest.raises(ValidationError):
        FactItem(value="v", origin=raw_value)


@pytest.mark.parametrize("raw_value", sorted(RULE_CONDITION_VALUES))
def test_regulatory_finding_accepts_every_rule_condition_state(raw_value) -> None:
    assert _finding(status=raw_value).status.value == raw_value


@pytest.mark.parametrize("raw_value", ["satisfied", "CONDITION_SATISFIED", ""])
def test_regulatory_finding_rejects_unknown_status(raw_value) -> None:
    with pytest.raises(ValidationError):
        _finding(status=raw_value)


@pytest.mark.parametrize("raw_value", sorted(CONFIDENCE_BAND_VALUES))
def test_regulatory_finding_accepts_every_confidence_band(raw_value) -> None:
    assert _finding(confidence=raw_value).confidence.value == raw_value


@pytest.mark.parametrize("raw_value", ["high", "CERTAIN", ""])
def test_regulatory_finding_rejects_unknown_confidence_band(raw_value) -> None:
    with pytest.raises(ValidationError):
        _finding(confidence=raw_value)


def test_iso_timestamps_are_preserved_on_round_trip() -> None:
    response = AssessmentResponse(
        assessment_id="as-1",
        passport_id="p-1",
        timestamp="2026-09-06T19:00:00Z",
        language="en",
        findings=[_finding()],
    )
    assert response.timestamp == "2026-09-06T19:00:00Z"
    assert AssessmentResponse.model_validate(response.model_dump()).timestamp == "2026-09-06T19:00:00Z"


def test_passport_timestamp_defaults_are_iso_8601_strings() -> None:
    passport = InnovationPassport()
    assert passport.created_at == "2026-09-06T19:00:00Z"
    assert passport.updated_at == "2026-09-06T19:00:00Z"
    parsed = datetime.fromisoformat(passport.created_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.year == 2026


def test_statutory_citation_effective_date_is_iso_string() -> None:
    citation = _citation(effective_date="2022-06-12")
    assert citation.effective_date == "2022-06-12"
    assert datetime.strptime(citation.effective_date, "%Y-%m-%d").year == 2022


def test_fact_item_value_holds_datetime_and_round_trips() -> None:
    moment = datetime(2026, 9, 6, 19, 0, 0, tzinfo=UTC)
    item = FactItem(value=moment, origin=FactOrigin.INFERRED, confidence=0.55)
    assert item.value == moment
    assert FactItem.model_validate(item.model_dump()) == item


@pytest.mark.xfail(
    reason="ClarificationQuery.severity accepts any string although DECISION_CRITICAL|ADVISORY is documented: app/models/passport.py:55",
    strict=False,
)
def test_clarification_severity_is_validated() -> None:
    with pytest.raises(ValidationError):
        ClarificationQuery(
            id="cq-1",
            field_key="target_markets",
            question_text={"en": "Which market?"},
            options=["India"],
            severity="banana",
        )


@pytest.mark.xfail(
    reason="IngredientEntry.quantity_percentage coerces bool True to 1.0 instead of rejecting it: app/models/passport.py:25",
    strict=False,
)
def test_ingredient_percentage_rejects_bool() -> None:
    with pytest.raises(ValidationError):
        IngredientEntry(raw_name="Ashwagandha", quantity_percentage=True)


@pytest.mark.xfail(
    reason="IngredientEntry.quantity_percentage accepts 500.0 with no 0-100 constraint: app/models/passport.py:25",
    strict=False,
)
def test_ingredient_percentage_range_is_enforced() -> None:
    with pytest.raises(ValidationError):
        IngredientEntry(raw_name="Ashwagandha", quantity_percentage=500.0)


@pytest.mark.xfail(
    reason="RegulatoryFinding.risk_level accepts any string although critical|high|medium|low is documented: app/models/regulatory.py:32",
    strict=False,
)
def test_regulatory_finding_risk_level_is_validated() -> None:
    with pytest.raises(ValidationError):
        _finding(risk_level="catastrophic")


@pytest.mark.xfail(
    reason="AssessmentResponse.timestamp is typed str and rejects datetime instances: app/models/regulatory.py:38",
    strict=False,
)
def test_assessment_timestamp_accepts_datetime_instance() -> None:
    _build_model(
        AssessmentResponse,
        assessment_id="as-1",
        passport_id="p-1",
        timestamp=datetime(2026, 9, 6, 19, 0, 0, tzinfo=UTC),
        language="en",
        findings=[_finding()],
    )


@pytest.mark.xfail(
    reason="AssessmentResponse.unsupported_claim_rate accepts 1.5 with no 0.0-1.0 constraint: app/models/regulatory.py:43",
    strict=False,
)
def test_unsupported_claim_rate_range_is_enforced() -> None:
    with pytest.raises(ValidationError):
        AssessmentResponse(
            assessment_id="as-1",
            passport_id="p-1",
            timestamp="2026-09-06T19:00:00Z",
            language="en",
            findings=[_finding()],
            unsupported_claim_rate=1.5,
        )


@pytest.mark.xfail(
    reason="ClaimSafetySignal.severity accepts any string although HIGH|MEDIUM|LOW is documented: app/models/intelligence.py:10",
    strict=False,
)
def test_claim_safety_signal_severity_is_validated() -> None:
    with pytest.raises(ValidationError):
        ClaimSafetySignal(
            ingredient="Ashwagandha",
            botanical_name="Withania somnifera",
            signal="sedation",
            severity="banana",
            evidence_source="monograph",
            precaution="Avoid with sedatives.",
        )


@pytest.mark.xfail(
    reason="ProductClassifierResponse.pathway_confidence accepts any string although HIGH|MEDIUM|LOW is documented: app/models/intelligence.py:168",
    strict=False,
)
def test_classifier_pathway_confidence_is_validated() -> None:
    with pytest.raises(ValidationError):
        ProductClassifierResponse(
            likely_pathway="ayurveda_aahara",
            pathway_category="ayurveda_aahara",
            pathway_confidence="banana",
            disclaimer="d",
        )


@pytest.mark.xfail(
    reason="TerminologyMapResponse.matched_via accepts any string although exact|synonym|fuzzy|none is documented: app/models/intelligence.py:298",
    strict=False,
)
def test_terminology_matched_via_is_validated() -> None:
    with pytest.raises(ValidationError):
        TerminologyMapResponse(query="ashwagandha", matched=True, matched_via="banana")


def test_user_required_columns_are_nullable_false() -> None:
    columns = User.__table__.c
    assert columns.name.nullable is False
    assert columns.email.nullable is False
    assert columns.hashed_password.nullable is False
    assert columns.email.unique is True


def test_user_timestamp_columns_are_timezone_aware() -> None:
    columns = User.__table__.c
    assert columns.created_at.type.timezone is True
    assert columns.updated_at.type.timezone is True
    assert columns.created_at.server_default is not None


def test_generate_uuid_returns_unique_uuid4_strings() -> None:
    first = generate_uuid()
    second = generate_uuid()
    assert first != second
    parsed = UUID(first)
    assert parsed.version == 4
    assert str(parsed) == first


def test_user_factory_builds_populated_user() -> None:
    user = UserFactory()
    assert user.name
    assert str(user.email).endswith("@example.test")
    assert user.role == "researcher"
    assert user.institution
    assert user.is_active is True


def test_innolab_project_columns_declare_constraints() -> None:
    columns = InnolabProjectDB.__table__.c
    names = {column.name for column in InnolabProjectDB.__table__.columns}
    assert columns.slug.unique is True
    assert columns.owner_id.nullable is False
    assert columns.status.nullable is False
    assert columns.status.default.arg == "draft"
    assert "metadata_json" in names
    assert "metadata" not in names


def test_innolab_run_columns_declare_defaults() -> None:
    columns = InnolabRunDB.__table__.c
    assert columns.status.default.arg == "pending"
    assert columns.run_type.nullable is False
    assert columns.started_at.nullable is True
    assert columns.completed_at.nullable is True


def test_innolab_run_step_columns_declare_defaults() -> None:
    columns = InnolabRunStepDB.__table__.c
    assert columns.seq.nullable is False
    assert columns.status.default.arg == "pending"
    assert columns.agent_slug.nullable is False


@pytest.mark.xfail(
    reason="User() accepts missing name/email/hashed_password at construction instead of enforcing nullable=False columns: app/models/db_models.py:15",
    strict=False,
)
def test_user_construction_requires_columns() -> None:
    user = User()
    assert user.name is not None
    assert user.email is not None
    assert user.hashed_password is not None


@pytest.mark.xfail(
    reason="InnolabProjectDB Column(default=...) values are not applied at construction so status is None until flush: app/models/innolab_models.py:27",
    strict=False,
)
def test_innolab_project_construction_applies_defaults() -> None:
    project = InnolabProjectDB(name="Alpha", slug="alpha", owner_id="user-1")
    assert project.status == "draft"
    assert project.created_at is not None


@pytest.mark.xfail(
    reason="InnolabProjectDB.created_at column drops timezone while db_models uses DateTime(timezone=True): app/models/innolab_models.py:30",
    strict=False,
)
def test_innolab_created_at_is_timezone_aware() -> None:
    assert InnolabProjectDB.__table__.c.created_at.type.timezone is True
