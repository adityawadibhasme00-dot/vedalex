"""Tests for the per-ingredient jurisdiction legality cross-checker."""

from typing import cast

import pytest

from app.models.canonical import CanonicalIngredient
from app.services.ingredient_legality import IngredientLegalityChecker as checker

pytestmark = pytest.mark.unit


def make_ingredient(canonical_id="ING-ASHWAGANDHA", **overrides):
    payload = {
        "canonical_id": canonical_id,
        "api_monograph_id": "API-VOL1-008",
        "accepted_botanical_name": "Withania somnifera (L.) Dunal",
        "family": "Solanaceae",
        "fssai_aahara_status": "permitted",
        "us_fda_ndi_status": "old_dietary_ingredient",
        "canada_nhpid_status": "monographed",
    }
    payload.update(overrides)
    return CanonicalIngredient(**payload)


def test_india_permitted_ingredient_passes_schedule_i_check():
    result = checker.check_jurisdiction_legality([make_ingredient()], "India")

    assert result["jurisdiction"] == "India"
    assert result["overall_legality_passed"] is True
    check = result["ingredient_checks"][0]
    assert check["canonical_id"] == "ING-ASHWAGANDHA"
    assert check["botanical_name"] == "Withania somnifera (L.) Dunal"
    assert check["status"] == "PERMITTED (Schedule I Positive List)"
    assert "API-VOL1-008" in check["note"]


def test_india_unlisted_ingredient_is_restricted():
    ingredient = make_ingredient(fssai_aahara_status="restricted")
    result = checker.check_jurisdiction_legality([ingredient], "India")

    assert result["overall_legality_passed"] is False
    check = result["ingredient_checks"][0]
    assert check["status"] == "RESTRICTED"
    assert "Schedule I positive list" in check["note"]


@pytest.mark.parametrize("jurisdiction", ["india", "INDIA", "in"])
def test_india_jurisdiction_aliases_are_accepted(jurisdiction):
    result = checker.check_jurisdiction_legality([make_ingredient()], jurisdiction)

    assert result["overall_legality_passed"] is True
    assert result["ingredient_checks"][0]["status"].startswith("PERMITTED (Schedule I")


def test_us_old_dietary_ingredient_is_grandfathered():
    result = checker.check_jurisdiction_legality([make_ingredient()], "united states")

    assert result["overall_legality_passed"] is True
    check = result["ingredient_checks"][0]
    assert check["status"] == "PERMITTED (Pre-1994 Old Dietary Ingredient)"
    assert "DSHEA" in check["note"]
    assert "no NDI notification" in check["note"]


def test_us_ndi_notification_required_blocks_pass():
    ingredient = make_ingredient(us_fda_ndi_status="ndi_notification_required")
    result = checker.check_jurisdiction_legality([ingredient], "usa")

    assert result["overall_legality_passed"] is False
    check = result["ingredient_checks"][0]
    assert check["status"] == "NDI NOTIFICATION REQUIRED (75-Day Pre-market Filing)"
    assert "21 CFR 190.6" in check["note"]


def test_us_unlisted_ingredient_is_restricted():
    ingredient = make_ingredient(us_fda_ndi_status="restricted")
    result = checker.check_jurisdiction_legality([ingredient], "us")

    assert result["overall_legality_passed"] is False
    assert result["ingredient_checks"][0]["status"] == "RESTRICTED / UNLISTED"


def test_canada_monographed_ingredient_passes():
    result = checker.check_jurisdiction_legality([make_ingredient()], "Canada")

    assert result["overall_legality_passed"] is True
    check = result["ingredient_checks"][0]
    assert check["status"] == "PERMITTED (NHPID Monograph List)"
    assert "NPN" in check["note"]


def test_canada_unmonographed_ingredient_requires_class_iii_evidence():
    ingredient = make_ingredient(canada_nhpid_status="schedule_1")
    result = checker.check_jurisdiction_legality([ingredient], "ca")

    assert result["overall_legality_passed"] is False
    check = result["ingredient_checks"][0]
    assert check["status"] == "CLASS III EVIDENCE REQUIRED"
    assert "clinical literature" in check["note"]


def test_overall_pass_is_false_when_one_ingredient_is_restricted():
    permitted = make_ingredient("ING-ASHWAGANDHA")
    blocked = make_ingredient("ING-NEEM", fssai_aahara_status="restricted")

    result = checker.check_jurisdiction_legality([permitted, blocked], "India")

    assert result["overall_legality_passed"] is False
    statuses = [c["status"] for c in result["ingredient_checks"]]
    assert statuses[0].startswith("PERMITTED")
    assert statuses[1] == "RESTRICTED"


def test_overall_pass_is_false_when_one_canada_ingredient_is_unmonographed():
    permitted = make_ingredient("ING-ASHWAGANDHA")
    blocked = make_ingredient("ING-NEEM", canada_nhpid_status="schedule_1")

    result = checker.check_jurisdiction_legality([permitted, blocked], "Canada")

    assert result["overall_legality_passed"] is False
    assert len(result["ingredient_checks"]) == 2
    assert result["ingredient_checks"][0]["status"].startswith("PERMITTED")
    assert result["ingredient_checks"][1]["status"] == "CLASS III EVIDENCE REQUIRED"


def test_empty_ingredient_list_returns_no_checks():
    result = checker.check_jurisdiction_legality([], "India")

    assert result["ingredient_checks"] == []
    assert result["overall_legality_passed"] is True


@pytest.mark.xfail(
    reason="jurisdiction values outside the three known lists fall through with status PERMITTED and overall_legality_passed=True, so an unvalidated region fails open (ingredient_legality.py:54)",
    strict=False,
)
def test_unknown_jurisdiction_fails_closed():
    ingredient = make_ingredient(fssai_aahara_status="prohibited")
    result = checker.check_jurisdiction_legality([ingredient], "Germany")

    assert result["overall_legality_passed"] is False
    assert not result["ingredient_checks"][0]["status"].startswith("PERMITTED")


@pytest.mark.xfail(
    reason="an FSSAI 'prohibited' botanical is reported as plain RESTRICTED instead of prohibited (ingredient_legality.py:29)",
    strict=False,
)
def test_fssai_prohibited_ingredient_is_reported_as_prohibited():
    ingredient = make_ingredient(fssai_aahara_status="prohibited")
    result = checker.check_jurisdiction_legality([ingredient], "india")

    assert result["ingredient_checks"][0]["status"] == "PROHIBITED"


@pytest.mark.xfail(
    reason="a Health Canada 'prohibited' ingredient is reported as CLASS III EVIDENCE REQUIRED, implying it can be licensed with more data (ingredient_legality.py:50)",
    strict=False,
)
def test_canada_prohibited_ingredient_is_reported_as_prohibited():
    ingredient = make_ingredient(canada_nhpid_status="prohibited")
    result = checker.check_jurisdiction_legality([ingredient], "canada")

    assert result["ingredient_checks"][0]["status"] == "PROHIBITED"


@pytest.mark.xfail(
    reason="jurisdiction is not validated, so a missing value raises AttributeError instead of an input error (ingredient_legality.py:24)",
    strict=False,
)
def test_missing_jurisdiction_raises_validation_error():
    with pytest.raises((TypeError, ValueError)):
        checker.check_jurisdiction_legality([make_ingredient()], cast(str, None))
