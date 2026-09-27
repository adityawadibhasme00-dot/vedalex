"""G8 - Filing Intelligence: patent watch (A2), deadlines (A3), fees (C2)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.watch_router import router as watch_router
from app.core.database import Base
from app.models.db_models import WatchHit, WatchProfile
from app.services import deadline_service, fee_estimator, watch_service

pytestmark = pytest.mark.unit


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'g8.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(tmp_path):
    from app.core.database import get_db

    engine = create_engine(
        f"sqlite:///{tmp_path/'g8api.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app = FastAPI()
    app.include_router(watch_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield TestClient(app)
    finally:
        session.close()
        engine.dispose()


PATENTS = [
    {
        "patent_no": "IN-2024-000111",
        "title": "Aqueous formulation of Ashwagandha and Turmeric for joint pain relief",
        "abstract": "An aqueous composition comprising Withania somnifera and Curcuma longa "
        "for the treatment of joint pain and arthritis.",
        "source_url": "https://example.test/IN-2024-000111",
    },
    {
        "patent_no": "IN-2024-000222",
        "title": "Drinkable Ashwagandha and Tulsi sleep supplement",
        "abstract": "A drinkable composition of Withania somnifera and Ocimum sanctum "
        "promoting sleep and stress relief.",
        "source_url": "https://example.test/IN-2024-000222",
    },
    {
        "patent_no": "IN-2024-000333",
        "title": "Solar panel mounting bracket",
        "abstract": "An aluminium bracket for mounting photovoltaic modules on rooftops.",
        "source_url": "https://example.test/IN-2024-000333",
    },
]


# ---------------------------------------------------------------------------
# A2 - deterministic overlap floor
# ---------------------------------------------------------------------------

def test_score_overlap_detects_full_match():
    kind, score, shared = watch_service.score_overlap(
        ["Ashwagandha root powder", "Turmeric extract"],
        "joint pain",
        "aqueous formulation of ashwagandha and turmeric for joint pain relief",
    )
    assert kind == "match"
    assert score >= watch_service.MATCH_THRESHOLD
    assert "ashwagandha" in shared and "turmeric" in shared


def test_score_overlap_detects_partial_when_use_differs():
    kind, _score, shared = watch_service.score_overlap(
        ["Ashwagandha root powder"], "joint pain", "drinkable ashwagandha sleep supplement"
    )
    assert kind == "partial"
    assert shared == ["ashwagandha"]


def test_score_overlap_ignores_unrelated_record():
    kind, score, shared = watch_service.score_overlap(
        ["Ashwagandha", "Turmeric"], "joint pain", PATENTS[2]["abstract"]
    )
    assert kind == "no_match"
    assert score == 0.0
    assert shared == []


def test_score_overlap_is_deterministic_across_calls():
    args = (["Ashwagandha", "Turmeric"], "joint pain", PATENTS[0]["abstract"])
    assert watch_service.score_overlap(*args) == watch_service.score_overlap(*args)


def test_score_overlap_handles_empty_profile():
    assert watch_service.score_overlap([], "x", "ashwagandha")[0] == "no_match"


def test_normalize_ingredient_lowercases_and_collapses():
    assert watch_service.normalize_ingredient("  Ashwagandha   Root  ") == "ashwagandha root"


# ---------------------------------------------------------------------------
# A2 - screening + digest
# ---------------------------------------------------------------------------

def test_create_profile_normalizes_ingredients(db):
    profile = watch_service.create_profile(
        db, "u1", "Ashwagandha + Turmeric", ["  Ashwagandha Root ", "TURMERIC"], "joint pain"
    )
    assert profile.ingredients == ["ashwagandha root", "turmeric"]
    assert watch_service.list_profiles(db, "u1")[0].id == profile.id


def test_run_watch_cycle_creates_match_and_partial_only(db):
    watch_service.create_profile(db, "u1", "Joint formula", ["Ashwagandha", "Turmeric"], "joint pain")
    result = watch_service.run_watch_cycle(db, patents=PATENTS)
    assert result["profiles_screened"] == 1
    assert result["patents_considered"] == 3

    hits = db.query(WatchHit).all()
    numbers = {h.patent_no for h in hits}
    assert numbers == {"IN-2024-000111", "IN-2024-000222"}
    match = next(h for h in hits if h.patent_no == "IN-2024-000111")
    assert match.match_kind == "match"
    assert match.urgency == "HIGH"
    assert match.source_url.startswith("https://")
    assert "facilitator" in match.advice.lower()


def test_watch_cycle_is_idempotent_no_duplicate_hits(db):
    watch_service.create_profile(db, "u1", "Joint formula", ["Ashwagandha", "Turmeric"], "joint pain")
    watch_service.run_watch_cycle(db, patents=PATENTS)
    watch_service.run_watch_cycle(db, patents=PATENTS)
    assert db.query(WatchHit).count() == 2


def test_run_watch_cycle_without_patents_only_stamps_timestamp(db):
    profile = watch_service.create_profile(db, "u1", "Joint formula", ["Ashwagandha"], "joint pain")
    result = watch_service.run_watch_cycle(db, patents=None)
    assert result["hits_created"] == 0
    db.refresh(profile)
    assert profile.last_checked_at


def test_watch_cycle_scopes_to_user(db):
    watch_service.create_profile(db, "u1", "A", ["Ashwagandha"], "joint pain")
    watch_service.create_profile(db, "u2", "B", ["Turmeric"], "skin")
    assert watch_service.run_watch_cycle(db, patents=PATENTS, user_id="u2")["profiles_screened"] == 1


def test_run_watch_cycle_writes_audit_entry(db):
    from app.models.db_models import AuditLogEntry

    watch_service.create_profile(db, "u1", "A", ["Ashwagandha"], "joint pain")
    watch_service.run_watch_cycle(db, patents=PATENTS)
    assert db.query(AuditLogEntry).filter(AuditLogEntry.event_type == "watch.cycle").count() == 1


def test_digest_reports_no_match_message_in_hindi_and_english(db):
    watch_service.create_profile(db, "u1", "A", ["Ashwagandha"], "joint pain")
    digest = watch_service.build_digest(db, "u1")
    assert digest["total_alerts"] == 0
    assert "naya patent" in digest["summary_hi"]
    assert "No new patent" in digest["summary_en"]
    assert digest["sections"][0]["alert_count"] == 0


def test_digest_lists_alerts_per_profile(db):
    watch_service.create_profile(db, "u1", "Joint formula", ["Ashwagandha", "Turmeric"], "joint pain")
    watch_service.run_watch_cycle(db, patents=PATENTS)
    digest = watch_service.build_digest(db, "u1")
    assert digest["total_alerts"] == 2
    assert digest["sections"][0]["alerts"][0]["patent_no"].startswith("IN-2024")
    assert "matched your watched" in digest["summary_en"]


def test_delete_profile_removes_only_own_profile(db):
    profile = watch_service.create_profile(db, "u1", "A", ["Ashwagandha"], "joint pain")
    assert watch_service.delete_profile(db, "u2", cast(str, profile.id)) is False
    assert watch_service.delete_profile(db, "u1", cast(str, profile.id)) is True
    assert db.query(WatchProfile).count() == 0


def test_digest_json_is_serialisable(db):
    import json

    watch_service.create_profile(db, "u1", "A", ["Ashwagandha"], "joint pain")
    assert json.loads(watch_service.digest_as_json(watch_service.build_digest(db, "u1")))["profiles"] == 1


def test_prompt_file_is_present_and_forbids_fabrication():
    prompt = watch_service.load_prompt()
    assert "NEVER fabricate" in prompt
    assert "patent_no" in prompt


# ---------------------------------------------------------------------------
# A3 - deadline rules
# ---------------------------------------------------------------------------

def test_patent_renewal_schedule_starts_from_third_year():
    rows = deadline_service.generate_deadlines("patent_renewal", "2020-04-01", "IN2020410001")
    years = [int(r["due_date"][:4]) for r in rows]
    assert years[0] == 2023
    assert years == sorted(years)
    assert all("Patents Rules" in r["statutory_basis"] for r in rows)


def test_trademark_renewal_is_ten_years():
    rows = deadline_service.generate_deadlines("trademark_renewal", "2020-06-15")
    assert rows[0]["due_date"] == "2030-06-15"
    assert "Trade Marks Rules" in rows[0]["statutory_basis"]


def test_gi_renewal_is_ten_years():
    rows = deadline_service.generate_deadlines("gi_renewal", "2019-01-31")
    assert rows[0]["due_date"] == "2029-01-31"


def test_patent_twelfth_year_rule_is_explicit():
    assert "12th" in deadline_service.DEADLINE_RULES["patent_12th_year"]["label"]


def test_abs_milestone_is_single_manual_deadline():
    rows = deadline_service.generate_deadlines("abs_milestone", "2025-05-05", "NBA-APP-1")
    assert len(rows) == 1
    assert rows[0]["due_date"] == "2025-05-05"
    assert "Biological Diversity Act" in rows[0]["statutory_basis"]


def test_unknown_deadline_kind_is_rejected():
    with pytest.raises(ValueError):
        deadline_service.generate_deadlines("banana", "2020-01-01")


def test_invalid_date_is_rejected():
    with pytest.raises(ValueError):
        deadline_service.generate_deadlines("trademark_renewal", "not-a-date")


def test_leap_day_anchor_is_handled():
    rows = deadline_service.generate_deadlines("trademark_renewal", "2020-02-29")
    assert rows[0]["due_date"] == "2030-02-28"


def test_create_deadline_persists_with_rule_reminders(db):
    row = deadline_service.create_deadline(db, "u1", "patent_renewal", "2027-04-01", reference="IN1")
    assert row.status == "pending"
    assert row.reminder_days == deadline_service.DEADLINE_RULES["patent_renewal"]["reminders"]


def test_create_schedule_creates_every_derived_deadline(db):
    rows = deadline_service.create_schedule(db, "u1", "trademark_renewal", "2020-06-15", reference="TM1")
    assert len(rows) == 1
    assert rows[0].reference == "TM1"


def test_upcoming_respects_window_and_ignores_done(db):
    soon = (date.today() + timedelta(days=10)).isoformat()
    far = (date.today() + timedelta(days=400)).isoformat()
    deadline_service.create_deadline(db, "u1", "patent_renewal", soon, title="Soon")
    deadline_service.create_deadline(db, "u1", "patent_renewal", far, title="Far")
    upcoming = deadline_service.upcoming(db, "u1", within_days=90)
    assert [u["title"] for u in upcoming] == ["Soon"]
    assert upcoming[0]["days_left"] <= 10
    assert upcoming[0]["reminders_fired"]

    deadline_service.mark_done(db, "u1", upcoming[0]["id"])
    assert deadline_service.upcoming(db, "u1", within_days=90) == []


def test_mark_done_is_owner_scoped(db):
    row = deadline_service.create_deadline(db, "u1", "patent_renewal", "2030-01-01")
    assert deadline_service.mark_done(db, "u2", cast(str, row.id)) is False
    assert deadline_service.mark_done(db, "u1", cast(str, row.id)) is True


def test_list_deadlines_filters_by_window(db):
    deadline_service.create_deadline(db, "u1", "patent_renewal", "2030-01-01")
    deadline_service.create_deadline(db, "u1", "patent_renewal", "2040-01-01")
    assert len(deadline_service.list_deadlines(db, "u1", within_days=3650)) == 1


def test_rules_catalogue_exposes_statutory_basis():
    kinds = {r["kind"] for r in deadline_service.rules_catalogue()}
    assert {"patent_renewal", "trademark_renewal", "gi_renewal"} <= kinds
    assert all(r["statutory_basis"] for r in deadline_service.rules_catalogue())


def test_reminder_message_is_delivery_ready():
    class Row:
        title = "Patent renewal"
        due_date = "2030-04-01"

    assert "2030-04-01" in deadline_service.reminder_message(Row(), "hi")
    assert "2030-04-01" in deadline_service.reminder_message(Row(), "en")


# ---------------------------------------------------------------------------
# C2 - fee estimator
# ---------------------------------------------------------------------------

def test_fee_routes_expose_official_sources():
    routes = {r["route"]: r for r in fee_estimator.list_routes()}
    assert {"patent", "trademark", "gi", "abs"} <= set(routes)
    assert routes["patent"]["source"].startswith("https://")


def test_startup_gets_twenty_percent_patent_fee():
    large = fee_estimator.estimate("patent", "large_entity")
    startup = fee_estimator.estimate("patent", "startup")
    assert startup["total"] == round(large["total"] * 0.2, 2)
    assert startup["concession_pct"] > 70
    assert startup["concession_saved"] > 0


def test_small_entity_gets_half_fee():
    individual = fee_estimator.estimate("trademark", "individual")
    small = fee_estimator.estimate("trademark", "small_entity")
    assert small["total"] == round(individual["total"] * 0.5, 2)


def test_trademark_scales_with_classes():
    one = fee_estimator.estimate("trademark", "individual", classes=1)
    three = fee_estimator.estimate("trademark", "individual", classes=3)
    assert three["total"] == round(one["total"] * 3, 2)


def test_patent_estimate_can_drop_examination_and_grant():
    full = fee_estimator.estimate("patent", "individual")
    lean = fee_estimator.estimate("patent", "individual", include_examination=False)
    assert lean["total"] < full["total"]
    assert all(i["stage"] not in {"exam", "grant"} for i in lean["line_items"])


def test_every_estimate_carries_source_and_as_of():
    est = fee_estimator.estimate("patent", "startup")
    assert est["source_url"].startswith("https://")
    assert est["as_of"]
    assert "official fee schedule" in est["disclaimer"].lower()


def test_abs_route_is_zero_fee_with_note():
    est = fee_estimator.estimate("abs", "individual")
    assert est["total"] == 0
    assert "negotiated" in est["note"].lower()


def test_unknown_route_or_entity_is_rejected():
    with pytest.raises(ValueError):
        fee_estimator.estimate("crypto", "individual")
    with pytest.raises(ValueError):
        fee_estimator.estimate("patent", "unicorn")


def test_class_count_bounds_are_enforced():
    with pytest.raises(ValueError):
        fee_estimator.estimate("trademark", "individual", classes=0)
    with pytest.raises(ValueError):
        fee_estimator.estimate("trademark", "individual", classes=999)


def test_fee_schedule_json_is_ingestible_knowledge_seed():
    import json
    import os

    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "app", "knowledge", "fee_schedule.json"
    )
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["routes"]["patent"]["items"]
    assert data["entity_classes"]["startup"]["multiplier"] < 1.0


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

def test_fee_routes_endpoint_is_public(client):
    resp = client.get("/api/v1/fees/routes")
    assert resp.status_code == 200
    assert {r["route"] for r in resp.json()["routes"]} >= {"patent", "trademark"}


def test_fee_estimate_endpoint(client):
    resp = client.post(
        "/api/v1/fees/estimate", json={"route": "patent", "entity_class": "startup"}
    )
    assert resp.status_code == 200
    assert resp.json()["entity_class"] == "startup"


def test_fee_estimate_rejects_unknown_route(client):
    assert client.post("/api/v1/fees/estimate", json={"route": "crypto"}).status_code == 422


def test_deadline_rules_endpoint(client):
    resp = client.get("/api/v1/deadlines/rules")
    assert resp.status_code == 200
    assert any(r["kind"] == "patent_renewal" for r in resp.json()["rules"])


def test_digest_endpoint_works_anonymous(client):
    resp = client.get("/api/v1/watch/digest")
    assert resp.status_code == 200
    assert "summary_hi" in resp.json()


def test_filing_routes_exist_in_openapi():
    from app.main import app

    spec = app.openapi()
    for path in (
        "/api/v1/watch/profiles",
        "/api/v1/watch/digest",
        "/api/v1/deadlines",
        "/api/v1/deadlines/schedule",
        "/api/v1/fees/estimate",
    ):
        assert path in spec["paths"], path


def test_watch_run_is_admin_only_in_openapi():
    from app.main import app

    op = app.openapi()["paths"]["/api/v1/watch/run"]["post"]
    assert op.get("security")


def test_watch_cycle_hook_is_disabled_when_env_off():
    import os

    from app.services import ingestion_scheduler as sched

    os.environ["IPSAKTI_WATCH_SCHEDULER"] = "0"
    os.environ["IPSAKTI_INGESTION_SCHEDULER"] = "1"
    try:
        assert sched._watch_enabled() is False
    finally:
        os.environ.pop("IPSAKTI_WATCH_SCHEDULER", None)
        os.environ.pop("IPSAKTI_INGESTION_SCHEDULER", None)


def test_watch_cycle_hook_inherits_ingestion_switch():
    import os

    from app.services import ingestion_scheduler as sched

    os.environ["IPSAKTI_INGESTION_SCHEDULER"] = "0"
    os.environ.pop("IPSAKTI_WATCH_SCHEDULER", None)
    try:
        assert sched._watch_enabled() is False
    finally:
        os.environ.pop("IPSAKTI_INGESTION_SCHEDULER", None)


def test_watch_cycle_hook_is_non_fatal_on_error():
    from app.services import ingestion_scheduler as sched

    assert sched._run_watch_cycle_guarded() is None or isinstance(
        sched._run_watch_cycle_guarded(), dict
    )
