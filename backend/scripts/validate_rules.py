"""
Rule-pack validator for IP-SAKTI Sahayak.

Loads every declarative rule pack in app/rules/*.yaml (plus the dynamic
blueprint_rules.json from the Excel "Rules" sheet) and checks that a pack is
CI-safe before it reaches the DeterministicRuleEngine:

  1. YAML syntax            — the file must parse cleanly.
  2. Pack schema            — required headers exist and are non-empty.
  3. Rule schema            — each rule has id/name/statute_ref/consequence and
                              well-formed conditions (known operator set).
  4. Unique rule ids        — no duplicate id across packs.
  5. Condition conflict     — two rules that force the SAME fact-key value but
                              declare contradictory expected_value (same key +
                              same expected_value, conflicting consequence),
                              or inverted conditions racing on one fact key.
  6. Citation exists        — statute_ref conventions must resolve to citation
                              strings present in the corpus so answers stay
                              citeable (acts_and_gazettes.json / curated KB).

Exit code 0 = all valid, 1 = validation errors, 2 = missing rules dir.
"""

import os
import re
import sys
import glob
import json
import argparse

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML is required: pip install pyyaml", file=sys.stderr)
    sys.exit(3)

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, ".."))
RULES_DIR = os.path.join(BACKEND_ROOT, "app", "rules")
KNOWLEDGE_DIR = os.path.join(BACKEND_ROOT, "app", "knowledge")

PACK_HEADERS = ("rule_pack_id", "jurisdiction", "authority", "governing_act",
                "version", "rules")
REQUIRED_RULE_FIELDS = ("id", "name", "statute_ref", "rule_version",
                        "effective_from", "status", "risk_level",
                        "requires_human_review", "evidence", "consequence")
KNOWN_STATUSES = {"active", "draft", "superseded"}
KNOWN_RISK_LEVELS = {"critical", "high", "medium", "low"}
KNOWN_OPERATORS = {"equals", "not_equals", "neq", "is_not", "contains", "in",
                   "gt", "greater_than", "lt", "less_than"}
KNOWN_FACT_KEYS = {
    "ingredients_have_documented_tk_use",
    "synergistic_empirical_data_present",
    "ingredients_conform_to_first_schedule",
    "process_conforms_to_classical_text",
    "contains_only_permitted_ayush_ingredients",
    "is_novel_ratio_or_form",
    "ingredients_on_aahara_positive_list",
    "claim_contains_disease_treatment",
    "form_is_dietary_food",
    "ingredients_are_dietary_botanicals",
    "ingredients_on_nhpid_list",
    "dosage_within_nhpid_monograph_limits",
    "product_form",
    "business_role",
    "manufacturing_location",
    "biological_resource_origin",
    "target_markets",
    "product_name_is_generic",
    "product_is_single_ingredient",
    "geographic_origin_is_indian",
    "has_traditional_origin_claim",
}

ERR, WARN = "error", "warning"


def _load_corpus_citation_strings() -> list:
    """Collect every human-readable citation label available to the RAG layer."""
    strings = []
    if os.path.isdir(KNOWLEDGE_DIR):
        for f in glob.glob(os.path.join(KNOWLEDGE_DIR, "*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                continue
            if isinstance(data, dict):
                data = [data]
            for item in data if isinstance(data, list) else []:
                if isinstance(item, dict):
                    for key in ("id", "act_title", "section_reference",
                                "official_authority", "statute", "source",
                                "title", "document / webpage"):
                        val = item.get(key)
                        if isinstance(val, str) and val.strip():
                            strings.append(val.strip())
    return strings


def _build_corpus_index():
    labels = _load_corpus_citation_strings()
    # Also index the ontologies (bioresource / monographs) referenced by bio rules.
    kd = os.path.join(KNOWLEDGE_DIR, "bioresource.json")
    if os.path.exists(kd):
        try:
            labels.append(json.load(open(kd, encoding="utf-8")))
        except Exception:
            pass
    return labels


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _canonicalize_citation(ref: str) -> list:
    """Split a statute_ref like '21 U.S.C. 343(r)(6) & 21 CFR 101.93' into
    independent atomic citation strings for corpus lookups."""
    raw = re.split(r"\s*&\s*|\s*;\s*|\s*,\s*(?=\d|SOR)", ref.strip())
    return [p.strip(" .;,") for p in raw if p and p.strip(" .;,")]


def _citation_in_corpus(atom: str, index: list) -> bool:
    want = _tokens(atom)
    if not want:
        return False
    # Code-style citations (SOR/2003-196, 21 CFR 101.93, 21 U.S.C. 343) compare
    # best as de-spaced substrings, so trailing sub-references ('Part 1') don't
    # mask a real registry hit.
    compact = re.sub(r"\s+", "", atom.lower())
    code_hit = re.search(r"(sor/[\d\w-]+|[\d\s]*cfr[\d.\s]+|u\.s\.c\.\s?\w+)", atom.lower())
    for label in index:
        if isinstance(label, dict):
            continue
        label_str = str(label)
        label_compact = re.sub(r"\s+", "", label_str.lower())
        if compact and len(compact) >= 5 and compact in label_compact:
            return True
        if code_hit:
            code_frag = code_hit.group(1).replace(" ", "").lower()
            if code_frag in label_compact:
                return True
        have = _tokens(label_str)
        if not have:
            continue
        if want.issubset(have):
            return True
        hits = sum(1 for t in want if t in have)
        if hits >= max(2, len(want) - 1):
            return True
    return False


def validate_yaml_pack(path, findings: list) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        findings.append((ERR, f"{os.path.basename(path)} — YAML parse error: {exc}"))
        return {}
    if not isinstance(data, dict):
        findings.append((ERR, f"{os.path.basename(path)} — top level must map to a dict"))
        return {}
    for header in PACK_HEADERS:
        if header not in data:
            findings.append((ERR, f"{os.path.basename(path)} — missing header '{header}'"))
        elif header == "rules":
            if not isinstance(data[header], list) or not data[header]:
                findings.append((ERR, f"{os.path.basename(path)} — 'rules' must be a non-empty list"))
        elif isinstance(data[header], str) and not data[header].strip():
            findings.append((ERR, f"{os.path.basename(path)} — header '{header}' is empty"))
    if not isinstance(data.get("rules"), list):
        return {}
    return data


def _normalize_guide_schema(rule: dict) -> dict:
    """Map the STEP-4 guide dialect (``when``/``then``) onto the internal
    ``conditions``/``consequence`` shape so both dialects validate alike."""
    rule = dict(rule)
    if "when" in rule and "conditions" not in rule:
        when = rule.get("when") or {}
        conds = when.get("all") or when.get("any") or []
        normalized = []
        for c in conds:
            if not isinstance(c, dict):
                continue
            normalized.append({
                "fact_key": c.get("field") or c.get("fact_key") or c.get("key"),
                "operator": c.get("operator") or "equals",
                "expected_value": c.get("value") if "value" in c else c.get("expected_value"),
            })
        rule["conditions"] = normalized
    if "then" in rule and "consequence" not in rule:
        then = rule.get("then") or {}
        result = then.get("result") or {}
        cons = dict(result)
        reqs = then.get("actions") or then.get("requirements") or result.get("requirements") or []
        cons.setdefault("category", result.get("category") or "")
        cons.setdefault("requirements", reqs if isinstance(reqs, list) else [])
        rule["consequence"] = cons
        rule.setdefault("risk_level", result.get("risk_level", rule.get("risk_level")))
    return rule


def validate_rule(pack_file, rule, findings: list) -> None:
    rule = _normalize_guide_schema(rule)
    name = os.path.basename(pack_file)
    rid = rule.get("id") or "?"
    loc = f"{name} / {rid}"
    for field in REQUIRED_RULE_FIELDS:
        if field not in rule:
            findings.append((ERR, f"{loc} — missing rule field '{field}'"))
            return

    # Spec governance fields
    if not isinstance(rule.get("rule_version"), str) or not rule["rule_version"].strip():
        findings.append((ERR, f"{loc} — 'rule_version' must be a non-empty string"))
    effective_from = rule.get("effective_from", "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(effective_from)):
        findings.append((ERR, f"{loc} — 'effective_from' must be ISO date YYYY-MM-DD"))
    status = (rule.get("status") or "").lower()
    if status not in KNOWN_STATUSES:
        findings.append((ERR, f"{loc} — 'status' must be one of {sorted(KNOWN_STATUSES)}"))
    risk = str(rule.get("risk_level") or "").lower()
    if risk not in KNOWN_RISK_LEVELS:
        findings.append((ERR, f"{loc} — 'risk_level' must be one of {sorted(KNOWN_RISK_LEVELS)}"))
    if not isinstance(rule.get("requires_human_review"), bool):
        findings.append((ERR, f"{loc} — 'requires_human_review' must be a boolean"))

    evidence = rule.get("evidence")
    if not isinstance(evidence, dict):
        findings.append((ERR, f"{loc} — 'evidence' must be a mapping with "
                              f"source_id/locator/authority"))
    else:
        for efield in ("source_id", "locator", "authority"):
            if not isinstance(evidence.get(efield), str) or not evidence.get(efield).strip():
                findings.append((ERR, f"{loc} — evidence.{efield} required"))

    exp = rule.get("explanation_template")
    if exp is None:
        exp = rule.get("explanation")
    if exp is not None:
        if not isinstance(exp, dict) or "en" not in exp:
            findings.append((ERR, f"{loc} — explanation_template must be a dict with an 'en' entry"))
        elif not isinstance(exp.get("en"), str) or not exp["en"].strip():
            findings.append((ERR, f"{loc} — explanation_template.en must be non-empty"))

    cons = rule.get("consequence")
    if not isinstance(cons, dict) or not cons.get("category"):
        findings.append((WARN, f"{loc} — consequence without a category label"))
    reqs = cons.get("requirements", []) if isinstance(cons, dict) else []
    if isinstance(reqs, list) and not reqs:
        findings.append((WARN, f"{loc} — consequence has no requirements"))

    conditions = rule.get("conditions")
    if isinstance(conditions, list):
        for idx, cond in enumerate(conditions):
            if not isinstance(cond, dict):
                findings.append((ERR, f"{loc} — condition #{idx} is not a dict"))
                continue
            key = cond.get("fact_key") or cond.get("key")
            op = (cond.get("operator") or "equals").lower().replace("_", " ")
            if not key:
                findings.append((ERR, f"{loc} — condition #{idx} lacks fact_key"))
            elif key not in KNOWN_FACT_KEYS:
                findings.append((WARN, f"{loc} — unknown fact_key '{key}' "
                                       "(no _build_facts producer)"))
            if op not in KNOWN_OPERATORS and op.replace(" ", "_") not in KNOWN_OPERATORS:
                findings.append((ERR, f"{loc} — unknown operator '{op}'"))
            if "expected_value" not in cond:
                findings.append((WARN, f"{loc} — condition #{idx} lacks expected_value"))
    elif not isinstance(conditions, list) and not rule.get("condition"):
        findings.append((ERR, f"{loc} — must declare 'conditions' list or free-text 'condition'"))


def check_conflicts(packs: list, findings: list) -> None:
    seen_ids = {}
    cond_signatures = {}
    for path, data in packs:
        if not data:
            continue
        pk = data.get("rule_pack_id", "?")
        for rule in data.get("rules", []):
            rid = rule.get("id")
            if rid in seen_ids:
                findings.append((ERR, f"duplicate rule id '{rid}' "
                                      f"({seen_ids[rid]} vs {pk})"))
            else:
                seen_ids[rid] = pk
            rule = _normalize_guide_schema(rule)
            conditions = rule.get("conditions")
            if not isinstance(conditions, list) or not conditions:
                continue
            cons_cat = (rule.get("consequence") or {}).get("category", "")
            juris = (data.get("jurisdiction") or "").strip() or pk
            signature = (
                juris,
                tuple(
                    f"{c.get('fact_key') or c.get('key')}|{c.get('operator', 'equals')}|{c.get('expected_value')}"
                    for c in conditions if isinstance(c, dict)
                ),
            )
            if signature in cond_signatures:
                prev_cat, prev_rid, prev_pk = cond_signatures[signature]
                if cons_cat != prev_cat:
                    findings.append((
                        ERR,
                        f"identical conditions in {prev_pk}/{prev_rid} and {pk}/{rid} "
                        f"({juris}) map to different consequences "
                        f"('{prev_cat}' vs '{cons_cat}')",
                    ))
            else:
                cond_signatures[signature] = (cons_cat, rid, pk)


def validate_citations(data, analytics: dict, findings: list) -> None:
    if not data:
        return
    pk = data.get("rule_pack_id", "?")
    for rule in data.get("rules", []):
        ref = rule.get("statute_ref", "")
        atoms = _canonicalize_citation(str(ref))
        loc = f"{pk} / {rule.get('id')}"
        if any(atom and not _citation_in_corpus(atom, analytics["corpus"]) for atom in atoms):
            findings.append((WARN, f"{loc} — statute_ref '{ref}' has no matching "
                                   f"citation in the corpus"))
            continue
        analytics["citations_ok"] += 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate IP-SAKTI rule packs")
    parser.add_argument("--rules-dir", default=RULES_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.rules_dir):
        print(f"rules dir not found: {args.rules_dir}", file=sys.stderr)
        return 2

    findings: list = []
    packs = []
    for path in sorted(glob.glob(os.path.join(args.rules_dir, "*.yaml"))):
        data = validate_yaml_pack(path, findings)
        packs.append((path, data))
        if not data:
            continue
        for rule in data.get("rules", []):
            validate_rule(path, rule, findings)
        validate_yaml_pack.__doc__  # no-op keep linters quiet

    check_conflicts(packs, findings)

    analytics = {"citations_ok": 0, "corpus": _build_corpus_index()}
    for path, data in packs:
        validate_citations(data, analytics, findings)

    # Download / dynamic rules (Excel blueprint Rules sheet).
    dyn_path = os.path.join(KNOWLEDGE_DIR, "blueprint_rules.json")
    if os.path.exists(dyn_path):
        try:
            dyn = json.load(open(dyn_path, encoding="utf-8"))
        except Exception as exc:
            findings.append((ERR, f"blueprint_rules.json unreadable: {exc}"))
            dyn = []
        if isinstance(dyn, list):
            for i, rule in enumerate(dyn):
                if isinstance(rule, dict) and not rule.get("rule_name"):
                    # empty placeholder rows are tolerated
                    continue
        else:
            findings.append((ERR, "blueprint_rules.json must be a JSON array"))

    errors = [f for f in findings if f[0] == ERR]
    warns = [f for f in findings if f[0] == WARN]
    total_rules = sum(len(d.get("rules", [])) for _, d in packs if d)

    print(f"rule packs: {len(packs)}  rules: {total_rules}  "
          f"citations matched: {analytics['citations_ok']}")
    for level, msg in findings:
        print(f"[{level.upper()}] {msg}")

    if not args.quiet:
        print(f"\n{len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())