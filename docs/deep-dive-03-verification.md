# Deep Dive 3 — The Verification Stack

`backend/app/rag/verification_orchestrator.py` (237) ·
`claim_verifier.py` (143) · `citation_validity_checker.py` (226) ·
`evidence_confidence_scorer.py` (291) · `semantic_entailment.py` (409) ·
`hallucination_guard.py` (365)

## The problem this solves

A language model will produce a fluent, plausible, wrong regulatory answer. It
will cite a section that does not contain the claim. It will state a dosage
limit from a monograph that says something else. In a compliance tool, that is
worse than saying nothing: the user acts on it.

So the generated text is treated as an **untrusted draft** and decomposed into
checkable assertions.

## The pipeline

```
Draft answer
     ↓
1. Claim extraction          → atomic claims
     ↓
2. Citation validity check   → does the cited source exist and support it?
     ↓
3. Claim-level entailment    → claim × source, per pair
     ↓
4. Evidence confidence       → weighted signals per claim
     ↓
5. Confidence gate
   ├── PASS → final answer
   └── FAIL → filter unsupported claims, then regenerate once, else refuse
```

Every draft claim ends in exactly one of: `SUPPORTED`, `UNSUPPORTED`,
`CONTRADICTED`, `PARTIALLY_SUPPORTED`. Claims that cannot be supported are
**removed from the answer**, not merely annotated. An answer with three good
claims and two invented ones becomes three good claims.

## Gate thresholds

```python
_MIN_SUPPORT_RATIO       = 0.50
_MIN_CITATION_VALIDITY   = 0.50
_MIN_EVIDENCE_CONFIDENCE = 0.35
_MAX_CONTRADICTIONS      = 0        # any contradiction fails the gate
_MAX_REGENERATION_ATTEMPTS = 1
```

`_MAX_CONTRADICTIONS = 0` is the strictest line in the system and the most
important. Half-supported is not good enough when the source *contradicts* the
claim — a contradiction is not weak evidence, it is evidence of an error.

One regeneration attempt, then refusal. Repeatedly sampling a model until it
happens to pass a gate is not verification, it is a lottery.

## 1. Claim extraction

`claim_verifier.py` decomposes generated text into atomic, independently
checkable claims. Atomicity is the point: a compound sentence cannot be
entailed or refuted as a unit, so a true half cannot rescue a false half.

`VerificationTable` holds the full claim × source × verdict matrix, and is
returned in the response — the user sees the same evidence the gate used.

## 2. Citation validity

`citation_validity_checker.py` asks a different question from entailment:
*does this source exist, and is it what it claims to be?* It checks that the
cited act/section is present in the corpus, that the authority is real, and
that the passage is not a placeholder.

This catches a distinct failure from step 3. Entailment asks "does this passage
support this claim"; citation validity asks "is this passage real". A model
citing a plausible-looking section number that does not exist fails here even
though no passage contradicts anything.

## 3. Entailment

`semantic_entailment.py` scores each (claim, source) pair. The embeddings for
evidence passages are cached in the shared `SharedCache`, so re-verifying a claim
across requests does not re-embed the corpus.

This is where the numpy/JSON fix in `cache.py` matters. A vector serialised with
`json.dumps(..., default=str)` comes back from Redis as its *repr string*, and
every downstream `float()` on it raises — so a single-replica dev run would pass
while production failed on the first Redis read. The cache now normalises arrays
to lists on write, so both backends return the same shape and cosine similarity
never sees a string.

## 4. Evidence confidence

`evidence_confidence_scorer.py` produces `ConfidenceSignal` items per claim and
an aggregate `EvidenceConfidence`. Signals are deliberately **plural and
weighted** — authority rank, recency, corroboration across independent sources,
retrieval score, entailment strength.

Recency matters because statutes get amended. Corroboration matters because one
source can be wrong and three agreeing independent ones are usually not. A
single binary "is it cited: yes/no" would not express any of that.

## The hallucination guard

`hallucination_guard.py` is a separate, advisory layer with a graded
`HallucinationRisk` enum rather than a pass/fail. It scans for fabricated
citations, invented section numbers, unsupported dosage figures, and
model-pleasing phrasing.

It is deliberately **advisory, not blocking**. The gate is the blocking layer.
Two layers that both veto answers produce a system that refuses everything,
which trains users to disable the checks — the failure mode this whole stack
exists to prevent.

## What reaches the user

`VerificationResult` carries the full audit surface:

```python
original_answer          # what the model said
final_answer             # what survived the gate
verification_table       # claim × source × verdict
citation_report          # which sources are real
evidence_confidence      # signals and aggregate
passed_gate              # bool
gate_reason              # why
regenerated              # bool
regeneration_count
removed_claims           # what was cut
unsupported_claims       # what had no support
```

`gate_reason` and `removed_claims` are the difference between a system that is
"AI you should not trust" and one that is "AI that shows its work". A reviewer
needs to know what was removed, not just that something was.

## Why this is deterministic where it counts

Retrieval, claim extraction, entailment scoring, citation validation and the gate
are all deterministic given the same corpus. The LLM is confined to drafting and
to one regeneration. That means:

- The same passport produces the same verdict.
- A verdict can be reproduced from the audit record.
- Removing the LLM entirely leaves a working, if plainer, compliance tool.

That is the property that makes this defensible in front of counsel rather than
merely impressive in a demo.

## Known limits

- Claim extraction is rule/heuristic-based, so a claim phrased unusually may not
  be atomised cleanly and can be under-checked.
- Entailment is semantic, not logical — it can be fooled by a passage that is
  topically right but does not actually assert the claim.
- The gate thresholds are hand-set constants, not tuned against a labelled
  eval set; there is no in-repo harness justifying a different value.
- `HallucinationRisk` is advisory, so a high-risk finding does not by itself
  block an answer.
