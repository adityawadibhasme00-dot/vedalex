"""Tests for the rule-pack validator (scripts/validate_rules.py)."""

import os
import sys
import tempfile

import pytest

SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "validate_rules.py"
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

GOOD_PACK = """
rule_pack_id: "TEST-VALID"
jurisdiction: "India"
authority: "Test Authority"
governing_act: "Test Act"
version: "0.0.1"
rules:
  - id: "RULE_TEST_OK"
    name: "Test rule"
    statute_ref: "Section 2"
    rule_version: "1.0.0"
    effective_from: "2022-05-09"
    status: "active"
    risk_level: "low"
    requires_human_review: false
    evidence:
      source_id: "test_source"
      locator: "Section 2"
      authority: "Test Authority"
    conditions:
      - fact_key: "ingredients_conform_to_first_schedule"
        operator: "equals"
        expected_value: true
    consequence:
      category: "Test Category"
      requirements:
        - "Requirement one"
"""


def _write_dir() -> str:
    tmp = tempfile.mkdtemp(prefix="ipsakti_rules_")
    return tmp


def _run(pack_text: str, filename: str = "test_pack.yaml") -> int:

    dirpath = _write_dir()
    with open(os.path.join(dirpath, filename), "w", encoding="utf-8") as fh:
        fh.write(pack_text)
    return _run_dir(dirpath)


def _run_dir(dirpath: str) -> int:
    from scripts.validate_rules import main

    with open(os.devnull, "w") as null:
        saved = sys.stdout
        sys.stdout = null
        try:
            code = main(["--rules-dir", dirpath, "--quiet"])
        finally:
            sys.stdout = saved
    return code


@pytest.fixture(scope="module")
def real_rules_dir():
    return os.path.join(PROJECT_ROOT, "app", "rules")


def test_real_packs_pass_validation(real_rules_dir):
    from scripts.validate_rules import main

    with open(os.devnull, "w") as null:
        saved = sys.stdout
        sys.stdout = null
        try:
            code = main(["--rules-dir", real_rules_dir, "--quiet"])
        finally:
            sys.stdout = saved
    assert code == 0, "real rule packs must be CI-clean"


def test_valid_pack_passes():
    assert _run(GOOD_PACK) == 0


def test_broken_yaml_is_detected():
    assert _run("rule_pack_id: [unclosed", "broken.yaml") == 1


def test_missing_header_is_detected():
    bad = GOOD_PACK.replace('jurisdiction: "India"\n', "")
    assert _run(bad) == 1


def test_unknown_operator_is_detected():
    bad = GOOD_PACK.replace('operator: "equals"', 'operator: "teleports"')
    assert _run(bad) == 1


def test_duplicate_rule_id_is_detected():
    dirpath = _write_dir()
    for fname, body in (("dup_a.yaml", GOOD_PACK), ("dup_b.yaml", GOOD_PACK)):
        with open(os.path.join(dirpath, fname), "w", encoding="utf-8") as fh:
            fh.write(body)
    assert _run_dir(dirpath) == 1


def test_identical_conditions_conflicting_consequence_detected():
    bad = """
rule_pack_id: "TEST-CONFLICT"
jurisdiction: "India"
authority: "Test Authority"
governing_act: "Test Act"
version: "0.0.1"
rules:
  - id: "RULE_CONF_A"
    name: "Conflict A"
    statute_ref: "Section 2"
    rule_version: "1.0.0"
    effective_from: "2022-05-09"
    status: "active"
    risk_level: "low"
    requires_human_review: false
    evidence:
      source_id: "test_source"
      locator: "Section 2"
      authority: "Test Authority"
    conditions:
      - fact_key: "ingredients_conform_to_first_schedule"
        operator: "equals"
        expected_value: true
    consequence:
      category: "Category A"
      requirements: ["Req A"]
  - id: "RULE_CONF_B"
    name: "Conflict B"
    statute_ref: "Section 2"
    rule_version: "1.0.0"
    effective_from: "2022-05-09"
    status: "active"
    risk_level: "low"
    requires_human_review: false
    evidence:
      source_id: "test_source"
      locator: "Section 2"
      authority: "Test Authority"
    conditions:
      - fact_key: "ingredients_conform_to_first_schedule"
        operator: "equals"
        expected_value: true
    consequence:
      category: "Category B"
      requirements: ["Req B"]
"""
    assert _run(bad) == 1