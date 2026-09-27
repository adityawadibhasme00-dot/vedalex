# Deep Dive 1 — The Deterministic Rule Engine

`backend/app/services/rule_engine.py` (547 lines), packs in `backend/app/rules/*.yaml`

## Why it exists

The regulatory question IP-SAKTI answers is not "what does the internet say about
neem?" — it is *"under which legal pathway does this product fall, and what
does the statute require me to do next?"* An LLM cannot answer that reliably,
because the answer depends on a handful of binary facts about **the user's own
product** combined against a fixed statutory text. That is a rule engine.

This is the load-bearing decision of the whole system:

> **Deterministic reviewed rules decide. Retrieval supplies evidence. The LLM
> only explains.**

If the LLM decided the pathway, the same submission would get different answers
on different days, and nobody could audit *why* a product was classified as a
drug. So classification runs here, in Python, against versioned YAML.

## Two rule layers, one interpreter

| Layer | Source | Purpose |
| --- | --- | --- |
| Hand-coded pathways | `_evaluate_india` / `_evaluate_us` / `_evaluate_canada` | Classification + citations |
| Declarative packs | `app/rules/*.yaml` | Condition → obligation, refines the above |
| Dynamic rules | `knowledge/blueprint_rules.json` (Excel "Rules" sheet) | Same interpreter, weaker matching |

`_normalize_rule` (line 33) is the interesting piece. The STEP-4 regulatory
guide uses a `when`/`then` schema; the engine internally uses
`conditions`/`consequence`. The normalizer translates the guide dialect into the
internal one and tags the rule `_schema: when_then`, so **both dialects execute
on the same interpreter** and a rules author can use whichever is clearer.

```yaml
when:  { all: [ {field, operator, value}, ... ] }   #  -> conditions[]
then:  { result: {...}, actions: [...] }             #  -> consequence{}
```

## The facts layer

`_build_facts` (line 124) converts a passport into ~25 booleans and strings. This
is the entire contract between user input and law. A few are substantive
judgements, not passthroughs:

- `process_conforms_to_classical_text` — true only if the process mentions a
  classical term (`bhavana`, `kalka`, `swarasa`, …) **and** does *not* mention a
  modern one (`spray dry`, `nano`, `encapsulat`, `standardized extraction`).
  Section 3(p) turns on classical-vs-novel.
- `is_novel_ratio_or_form` — the logical inverse of the above, cached so the two
  can never disagree.
- `product_name_is_generic` — every title token must be in a generic-term
  set; a distinctive name is itself a registrable asset.
- `has_disease_claim` — drives the food/drug boundary, the single most
  consequential distinction in the system.

Note `synergistic_empirical_data_present` is hard-wired `False`. That is honest,
not lazy: no combination-index assay data exists in the corpus, and pretending
otherwise would be fabricating evidence. The Section 3(p) rule fires precisely
because the system cannot prove synergism.

## Condition evaluation

`_eval_condition` (line 182) supports `equals`, `not equals`, `contains`/`in`,
`gt`, `lt`. Two deliberate design points:

1. **Unknown operators return `False`, not `True`.** A malformed rule fails
   closed. A rule pack typo must not silently activate a requirement.
2. **Numeric comparison is wrapped in `try/except` returning `False`** — a
   missing dosage fact must not crash a passport evaluation.

`_fired_rules` (line 226) filters by jurisdiction first, with an explicit
`us` ↔ `united states` alias bridge, then evaluates. `all` is the default mode;
`any` is opt-in via `_conditions_mode` when the normalizer sees a `when: {any:}`
block.

`_eval_text_condition` (line 211) is the honest escape hatch. Dynamic Excel rules
have free-text conditions like *"ingredient is used in traditional knowledge"*.
Rather than pretend to parse English, it tokenises and requires near-total
overlap against a composite of claims + intended use + resolved ingredients.
It is labelled *best-effort* in the docstring, and it should stay that way — it
is a fallback for rules nobody has formalised yet, and its weakness is visible.

## Merging: rules refine, they do not replace

`_merge_yaml_into` (line 252) is where a fired pack touches the finding:

- `requirements` and `actions` lists are **deduplicated and appended** to
  `next_action_steps`, preserving order.
- Risk escalates by rank, never de-escalates: `risk_ranks = {critical:4, high:3,
  medium:2, low:1}`, and a higher-ranked rule raises the finding's level.
- `requires_human_review` is **sticky** — once any rule sets it, the finding
  keeps it. A human-review flag must not be cleared by a later low-risk rule.
- `applied_rules` records id, version, pack, `effective_from`, `status`,
  `statute_ref` and `evidence` for every rule that fired. **This is the audit
  trail** — it is what makes a finding defensible months later when the statute
  has been amended.

Each pack carries `effective_from` and `rule_version` (e.g. Section 3(p):
`effective_from: 2005-04-04`, `v1.1.0`). Legal requirements have dates. A rule
engine that cannot express "this applied from 2005" cannot be trusted by counsel.

## Bilingual by construction

`explanation_template` carries `en` and `hi` in the same rule, so the obligation
and its plain-language explanation never drift apart across locales. The text is
data, not a template string assembled at runtime — you cannot forget to translate
one branch when both live in the same record.

## What a rule pack must contain

```yaml
rule_pack_id:    "RULE-IN-PATENT-SEC3P"     # stable, auditable
jurisdiction:   "India"                     # gates _fired_rules
authority:       "Indian Patent Office (CGPDTM)"
governing_act:   "The Patents Act, 1970 (Section 3(p))"
version:         "1.1.0"
rules:
  - id, name, statute_ref, rule_version
    effective_from, status
    risk_level, requires_human_review
    evidence: { source_id, locator, authority }   # where to verify
    explanation_template: { en, hi }
    conditions: [ { fact_key, operator, expected_value } ]
    consequence: { category, requirements[], alternative_ip[] }
```

`evidence.source_id` is not decoration — it is the join key that lets the
verification layer challenge the rule, and `alternative_ip` is what turns a bare
"blocked" into "here are your non-patentable escape routes".

## How to add a rule

1. Add the YAML pack under `app/rules/`. Nothing else changes — packs are globbed.
2. Every `fact_key` must already exist in `_build_facts`. A `fact_key` that does
   not exist resolves to `None`, and `None == True` is `False`, so the rule
   silently never fires. This is the main authoring trap.
3. Bump `version` and set `effective_from`. Both end up in `applied_rules`.
4. `tests/test_rule_engine.py` and `test_rule_validator.py` cover evaluation and
   pack validity.

## Known limits

- `synergistic_empirical_data_present` is always `False`; Section 3(p) therefore
  fires on any traditional-knowledge ingredient. Correct, but conservative.
- Facts are keyword matches on lowercase text. "Ashwagandha root extract
  spray-dried" correctly reads as novel process; "spray dried by a third party"
  would not.
- `_eval_text_condition` is fuzzy by construction. Rules it drives should be
  promoted to `conditions` form.
- Packs load once per process (`_yaml_packs_cache`) — correct for a web replica,
  but a pack edit needs a restart.
