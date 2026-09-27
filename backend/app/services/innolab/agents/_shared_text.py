"""Text-analysis primitives shared by more than one Innovation-Lab agent.

These were extracted from the 8k-line ``agent_executors`` when it was split by
domain.  They are shared because the agents genuinely interoperate: novelty and
TDOC both need atomic-feature extraction and the same claim/ref classifiers,
and FTO, drafting and disclosure all parse ratios and process steps the same
way.  Re-implementing them per agent is how two agents end up disagreeing about
what the same text means.
"""

from __future__ import annotations

import re
from typing import Any, cast

from app.services.innolab._shared import (
    _PURPOSE,
    _SOLVENT,
    _source_kind,
    _text,
)

__all__ = [
    "_BENEFIT_AS_COMPONENT",
    "_CORRUPT_CROSSWORD",
    "_DEVICE_TERM",
    "_DOSAGE_FORM",
    "_HAS_PROCESS_VERB",
    "_HYDROALCOHOLIC",
    "_LCA_GUIDANCE_HINTS",
    "_LCA_TOKEN_RE",
    "_LSM_FORMULA_RE",
    "_NC_STOP",
    "_PAT_PUBNO",
    "_STOPWORDS",
    "_UNDEFINED_AMOUNT",
    "_UNSUPPORTED_SYNERGY",
    "_VAGUE_PROCESS",
    "_atomic_novelty_features",
    "_basis_text",
    "_citation_kind",
    "_claim_elements",
    "_detected_ratio",
    "_draft_block_reasons",
    "_feature_disclosure",
    "_first_sentence",
    "_gcd_ratio",
    "_ingredient_benefit_split",
    "_keyword_phrases",
    "_overlap_similarity",
    "_parameter_flag",
    "_parse_invention",
    "_process_steps",
    "_short_name",
    "_solvent_word",
    "_split_claims_txt",
    "_tdoc_ref_kind",
    "_tokens",
    "_value_markers",
]


def _basis_text(inputs: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = inputs.get(key)
        if isinstance(value, list):
            joined = ", ".join(str(v) for v in value if str(v).strip())
            if joined:
                return joined
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "with", "that", "this", "you",
    "your", "any", "into", "from", "than", "then", "such", "what", "are",
    "using", "used", "which", "when", "might", "will", "have", "has", "been",
}


def _keyword_phrases(text: str, limit: int = 8) -> list[str]:
    """Deterministic keyword/noun-phrase extraction — no LLM required."""
    import re as _re
    texts = _re.split(r"[;,.|\n\r]+", text or "")
    phrases: list[str] = []
    for chunk in texts:
        chunk = chunk.strip()
        if not chunk or len(chunk) < 3:
            continue
        words = _re.split(r"\s+", chunk.lower())
        if len(words) == 1:
            toks = [_re.sub(r"[^a-z0-9_-]+", "", w) for w in words]
            word = toks[0] if toks else ""
            if word and word not in _STOPWORDS and 3 <= len(word) <= 28 and word not in phrases:
                phrases.append(word)
        else:
            meaningful = [w for w in words if _re.sub(r"[^a-z0-9_-]+", "", w) not in _STOPWORDS]
            if meaningful:
                phrase = " ".join(meaningful)[:60]
                if phrase not in phrases:
                    phrases.append(phrase)
        if len(phrases) >= limit:
            break
    return phrases


_NC_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "that",
    "this", "is", "are", "as", "by", "from", "at", "be", "comprising", "including",
    "wherein", "which", "into", "over", "under", "per", "than", "then", "such", "any", "said", "not", "please", "your",
}


def _tokens(text: str) -> set:
    raw = re.findall(r"[a-z][a-z0-9\-']{1,}", (text or "").lower())
    return {t for t in raw if t not in _NC_STOP and len(t) > 1}


def _overlap_similarity(query: str, passage: str) -> int:
    """Token-overlap similarity 0-100 — measures semantic/topic vocabulary overlap,
    NOT novelty. Always interpreted alongside feature coverage."""
    qt = _tokens(query)
    if not qt:
        return 0
    pt = _tokens(passage)
    hit = len(qt & pt)
    return int(round(hit / len(qt) * 100)) if qt else 0


def _parameter_flag(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.I)
    return m.group(0).strip() if m else None


_DOSAGE_FORM = re.compile(
    r"\b(capsules?|tablets?|liquid(?: formulation)?|oral drops?|nasal spray|spray|"
    r"syrup|ointment|gummies|powder(?: for reconstitution)?|dropper bottle|gargle|mouthwash)\b",
    re.I,
)


_HYDROALCOHOLIC = re.compile(
    r"hydro-?alcoho|aqueous[- ]alcoho|ethanol[- ]water|water[- ]ethanol|alcohol[- ]water",
    re.I,
)


_DEVICE_TERM = re.compile(
    r"\b(nasal spray|spray pump|metered(?:-dose)? pump|dropper|vial|bottle|pouch|sachet|"
    r"dropper bottle|nebuliz|inhaler|pump|nozzle)\b",
    re.I,
)


_HAS_PROCESS_VERB = re.compile(
    r"\b(extract|extraction|heat|stir|mix|blend|filter|filtrat|dry|drying|concentrat|"
    r"percolat|maceration|decoction|infusion|grind|grinding|add|combine|distil|squeeze|"
    r"press|wash|precipitat|lyophiliz|spray[- ]drying|steriliz|pasteuriz|fill|seal|"
    r"pack|agitat|reflux|soak|soaking|soxhlet|derivat)\b",
    re.I,
)


def _atomic_novelty_features(inputs: dict[str, Any], resolved: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Split an invention disclosure into atomic, claim-comparable features (F1…Fn).
    A phrase such as 'hydroalcoholic Ashwagandha-Brahmi extract with controlled
    solvent' becomes multiple independent features, so the comparison is meaningful."""
    texts = []
    for k in ("problem_text", "document_text", "disclosure_text", "formulation_text", "process_desc"):
        v = _text(inputs, k)
        if v:
            texts.append(v)
    blob = " ".join(texts)
    low = blob.lower()
    bot_names = [r.get("botanical_name") or r.get("raw_name", "") for r in resolved if r.get("raw_name")]
    features: list[dict[str, str]] = []

    def _feat(text: str, ftype: str, role: str, essentiality: str = "Essential",
              measurability: str = "Measurable") -> None:
        features.append({
            "feature": text,
            "type": ftype,
            "role": role,
            "essentiality": essentiality,
            "measurability": measurability,
        })

    for r in resolved:
        display = r.get("botanical_name") or r.get("raw_name", "")
        if not display:
            continue
        if r.get("resolved"):
            _feat(f"A formulation or process involving {display} (accepted botanical identity).",
                  "Composition", "Active ingredient component")
        else:
            _feat(f"A formulation or process involving {display} — botanical identity to be confirmed.",
                  "Composition", "Active ingredient component", essentiality="Preferred",
                  measurability="Partially measurable")

    if len(bot_names) >= 2:
        _feat(f"A combined extract comprising {' and '.join(bot_names[:3])}.", "Composition",
              "Ingredient combination")

    if _SOLVENT.search(blob):
        kind = ("a hydroalcoholic (aqueous-alcohol) solvent system"
                if _HYDROALCOHOLIC.search(low)
                else "a defined solvent system (exact solvent to be stated)")
        _feat(f"Extraction carrier: {kind}.", "Process", "Solvent system")
        ratio = _detected_ratio(blob, bot_names)
        if ratio:
            _feat(f"Controlled solvent ratio: {ratio}.", "Parameter", "Solvent ratio")
        else:
            _feat("Controlled solvent ratio — numerical value not provided (underdefined).",
                  "Parameter", "Solvent ratio", essentiality="Preferred", measurability="Vague")

    steps = _process_steps(_text(inputs, "process_desc") or blob)
    process_defined = bool(steps and (_HAS_PROCESS_VERB.search(" ".join(steps)) or len(steps) >= 2))
    if process_defined:
        _feat("Process sequence: " + "; ".join(steps[:4]) + ".", "Sequence", "Process steps")
    else:
        _feat("Manufacturing / extraction process steps — not described (provide sequence, temperatures, times).",
              "Sequence", "Process steps", essentiality="Preferred", measurability="Vague")

    temp_m = re.search(r"(\d+(?:[–\-]\s*\d+)?)\s*(?:°|degrees?\s*)?c\b", low, re.I)
    if temp_m:
        _feat(f"Defined extraction temperature window: {temp_m.group(1).strip()}°C.", "Parameter", "Temperature")
    else:
        _feat("Extraction temperature window — value not provided.", "Parameter", "Temperature",
              essentiality="Preferred", measurability="Vague")

    time = _parameter_flag(r"\b(\d+(?:\.\d+)?)\s*(h|hr|hours?|min|mins?|minutes?|days?)\b", low)
    if time:
        _feat(f"Extraction / processing time: {time}.", "Parameter", "Time")
    else:
        _feat("Extraction time window — value not provided.", "Parameter", "Time",
              essentiality="Preferred", measurability="Vague")

    markers = _value_markers(blob)
    if markers:
        _feat("Active-marker standardization: " + ", ".join(markers[:3]) + ".",
              "Parameter", "Marker standardization")
    else:
        _feat("Active-marker range or standardization threshold — not provided.", "Parameter",
              "Marker standardization", essentiality="Preferred", measurability="Vague")

    effect = _PURPOSE.search(low)
    if effect:
        _feat(f"Demonstrated technical effect: {effect.group(0).strip()} (evidence threshold to be defined).",
              "Use", "Technical effect")
    else:
        _feat("Technical effect / intended use — value not provided.", "Use", "Technical effect",
              essentiality="Preferred", measurability="Partially measurable")

    form = _parameter_flag(_DOSAGE_FORM.pattern, low)
    if form:
        _feat(f"Final dosage form: {form}.", "Composition", "Dosage form")
    else:
        _feat("Final dosage form — value not provided.", "Composition", "Dosage form",
              essentiality="Preferred", measurability="Partially measurable")

    return features[:12]


def _feature_disclosure(feature_text: str, passage: str) -> tuple:
    """Deterministic disclosure level for one feature against one reference passage.

    Uses the seven-level taxonomy: Explicitly / Inherently / Partially / Broadly
    disclosed, Suggested only, Not disclosed, Unclear. Never labels a feature
    'novel' from a failed search — that is reported as 'Not found in the corpus'."""
    if not passage or not passage.strip():
        return "Unclear", "No passage available in the searched corpus to decide."
    if "not provided" in feature_text or "underdefined" in feature_text:
        return ("Not disclosed",
                "The feature is underdefined by the inventor — the parameter value must be supplied before a comparison is meaningful.")
    qt = _tokens(feature_text)
    if not qt:
        return "Not disclosed", "Not found in the searched corpus."
    plow = passage.lower()
    present = [t for t in qt if t in plow]
    ratio = len(present) / len(qt)
    if ratio >= 0.85:
        level, basis = "Explicitly disclosed", f"{len(present)}/{len(qt)} feature terms appear in the passage."
    elif ratio >= 0.55:
        level, basis = ("Broadly disclosed",
                        f"{len(present)}/{len(qt)} feature terms present; the exact claimed detail or range is not specifically stated.")
    elif ratio >= 0.30:
        level, basis = ("Partially disclosed",
                        f"{len(present)}/{len(qt)} feature terms present; one or more elements of the feature are missing.")
    elif ratio > 0:
        level, basis = ("Suggested only",
                        f"Only {len(present)}/{len(qt)} feature terms present — mentioned as an option or category, not as the disclosed combination.")
    else:
        level, basis = "Not disclosed", "No feature term appears in the passage — not found in the searched corpus."
    return level, basis


_PAT_PUBNO = re.compile(r"((?:WO|EP|US|IN|CN|JP|DE|GB|FR|CA|AU|KR|TW)\s?[\dA-Z/]+\d[\dA-Z/]*)")


def _tdoc_ref_kind(c: dict[str, Any]) -> str:
    blob = f"{c.get('act_title') or ''} {c.get('authority') or ''}"
    low = blob.lower()
    if any(w in low for w in ("fda", "fssai", "ayush", "cdsco", "efsa", "who", "health canada", "drugs and cosmetics")):
        return "Regulatory / safety context"
    if any(w in low for w in ("traditional knowledge", "nakt", "ayurveda", "charaka", "sushruta", "bhavaprakash", "tkdl")):
        return "Traditional knowledge"
    if any(w in low for w in ("tdoc", "contribution", "3gpp", "etsi", "meeting", "change request", "agenda")):
        return "TDoc / contribution record"
    if any(w in low for w in ("industry patent", "patent", "uspto", "epo", "wipo", "inpass")):
        return "Patent prior art"
    return "Scientific / technical"


_BENEFIT_AS_COMPONENT = re.compile(
    r"\bcognitive\s+support\b|\bgeneral\s+wellness\b|\bbrain\s+(?:function|support)\b|\bstress\s+support\b",
    re.I,
)


_CORRUPT_CROSSWORD = re.compile(r"[A-Za-z]+[Hh]owever|[Hh]owever[A-Za-z]+", re.I)


_UNDEFINED_AMOUNT = re.compile(r"\beffective\s+amounts?\b", re.I)


_UNSUPPORTED_SYNERGY = re.compile(r"\b(?:synergistic\s+proportions?|synergistically?)\b", re.I)


_VAGUE_PROCESS = re.compile(r"\b(?:under\s+)?controlled\s+conditions\b", re.I)


def _ingredient_benefit_split(inv: dict[str, Any], resolved: list[dict[str, Any]], inputs: dict[str, Any]) -> dict[str, Any]:
    """Separate actual ingredients from benefit/effect terms and unresolved candidates,
    so claims never treat effects as components."""
    blob = " ".join(filter(None, [inv.get("problem", ""), inv.get("use", ""),
                                  _text(inputs, "process_desc", "formulation_text"),
                                  _text(inputs, "intended_use", "claimed_innovation")]))
    low = blob.lower()
    benefits: list[str] = []
    for b in ("cognitive support", "general wellness", "brain function", "brain support",
              "stress support", "supporting stress", "effective amounts", "synergistic proportions"):
        if b in low and b not in benefits:
            benefits.append(b)
    resolved_names = [r.get("botanical_name") or r.get("raw_name") for r in resolved if r.get("resolved")]
    unresolved_raw = [r.get("raw_name") for r in resolved if not r.get("resolved") and r.get("raw_name")]
    return {
        "ingredients": resolved_names[:8] or inv["ingredients"][:8],
        "unresolved_candidates": unresolved_raw[:8] or ["none"],
        "benefit_terms": benefits or ["none detected"],
        "confirmed": inv["ingredients"],
    }


def _draft_block_reasons(inv: dict[str, Any], inputs: dict[str, Any]) -> list[dict[str, str]]:
    """Block drafting when the disclosure contains corrupted or undefined technical terms.
    These blockers are the gate between parsing and claim structuring — an inventor must
    confirm before any claim is drafted. Returns an empty list when drafting may proceed."""
    blob = " ".join(filter(None, [inv.get("problem", ""), inv.get("use", ""),
                                  _text(inputs, "process_desc", "formulation_text", "claim_text"),
                                  _text(inputs, "intended_use", "claimed_innovation")]))
    reasons: list[dict[str, str]] = []

    def _add(code: str, title: str, why: str) -> None:
        if not any(r["code"] == code for r in reasons):
            reasons.append({"code": code, "title": title, "detail": why})

    ben = _BENEFIT_AS_COMPONENT.search(blob)
    if ben:
        _add("block-benefit", "Benefit language used as a component",
             f"'{ben.group(0)}' appears where a defined ingredient should be. Effect terms cannot be "
             f"drafted as claim components — the inventor must confirm which terms are ingredients and "
             f"which are effects before drafting.")

    for m in _CORRUPT_CROSSWORD.finditer(blob):
        _add("block-corrupt", "Corrupted / miscopied text",
             f"Adjacent words run together ('{m.group(0)}') — likely a copy error from the original notes. "
             f"Resolve the corrupted text with the inventor before structural drafting.")

    eff = _UNDEFINED_AMOUNT.search(blob)
    if eff:
        _add("block-undefined-amount", "Undefined quantity ('effective amounts')",
             "'effective amounts' is not a defined range. Claims require a concrete concentration, weight "
             f"ratio or dosage range, which is absent from the disclosure ({eff.group(0)}).")

    syn = _UNSUPPORTED_SYNERGY.search(blob)
    if syn:
        _add("block-synergy", "Unsupported synergistic proportions",
             f"'{syn.group(0)}' without comparative experimental data, an additive-model basis and a "
             f"statistical method. Synergy cannot be asserted in a claim without that support.")

    ctrl = _VAGUE_PROCESS.search(blob)
    if ctrl:
        _add("block-process", "Vague process conditions",
             f"'{ctrl.group(0)}' — the process parameters (solvent system, temperature, time, ratio, "
             f"scale) are not specified. Name them before the method claim is drafted.")

    solvent = _solvent_word(inv.get("solvent", ""))
    if re.search(r"\bsolvent\b", blob, re.I) and (not solvent or solvent == "solvent"):
        _add("block-solvent", "Solvent named without identity",
             "The description refers to 'solvent' without naming the system (e.g., hydroalcoholic, ethanol, "
             "water, aqueous extract). Name the solvent system before drafting process claims.")

    if re.search(r"\bsupporting\s+stress\b|\bstress\s+relief\b", blob, re.I):
        _add("block-stress", "Undefined stress-support effect",
             "'supporting stress' is a vague effect term — confirm what is measured (cortisol, perceived "
             "stress score, etc.) and keep it out of claim language until an effect definition exists.")

    return reasons


def _short_name(name: str) -> str:
    return re.split(r"\s*\(", name)[0].strip() or name


def _first_sentence(text: str) -> str:
    parts = re.split(r"[\.\n]", (text or "").strip())
    sent = parts[0].strip() if parts and parts[0].strip() else "An Ayurvedic botanical composition"
    return sent


def _process_steps(text: str) -> list[str]:
    """Split a process description into ordered, claim-ready steps."""
    text = (text or "").strip()
    if not text:
        return []
    steps = [s.strip(" .;,\t") for s in re.split(r"\d+[\.\):]\s*|\n+|;", text) if s.strip(" .;,\t")]
    if len(steps) <= 1:
        steps = [
            s.strip(" .;,\t")
            for s in re.split(
                r",\s+(?=(?:mix|combine|add|heat|stir|percolat|filter|dry|standard|clarif|extract|grind|blend|fill|compress|pack))",
                text,
                flags=re.I,
            )
            if s.strip(" .;,\t")
        ]
    return [s for s in steps if len(s) > 2][:8]


def _value_markers(text: str) -> list[str]:
    """Extract quantitative characterising parameters, e.g. '5% withanolides' ('40% ethanol' is a solvent, not a marker)."""
    stopwords = {"for", "of", "and", "to", "at", "with", "in", "by", "from", "the", "a", "an", "or", "per", "on"}
    out: list[str] = []
    for m in re.finditer(
        r"\b(\d+(?:[.,]\d+)?(?:[–\-]\s*\d+)?\s*%)\s*([A-Za-z][A-Za-z]*)(?:\s+([A-Za-z][A-Za-z]*))?",
        text or "",
    ):
        word1 = m.group(2)
        word2 = m.group(3)
        words = [w for w in (word1, word2) if w and w.lower() not in stopwords]
        val = f"{m.group(1).strip()} {(' '.join(words))}" if words else m.group(1).strip()
        if val and val not in out:
            out.append(val)
    return out[:6]


def _solvent_word(solvent: str) -> str:
    return re.sub(r"[\d.\-–%\s]+", "", solvent or "").strip().lower()


def _gcd_ratio(a: float, b: float) -> float:
    import math
    scale = 1.0
    while (a * scale) % 1 or (b * scale) % 1:
        scale *= 10
        if scale > 1e6:
            break
    ia, ib = int(round(a * scale)), int(round(b * scale))
    return math.gcd(ia, ib) or 1


def _detected_ratio(text: str, names: list[str]) -> str | None:
    """Detect a quantitative ratio of the first two ingredients from 'a:b' or per-ingredient amounts."""
    text = text or ""
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\b", text)
    if m:
        return f"about {m.group(1)}:{m.group(2)}"
    amounts: list[float] = []
    for name in names[:2]:
        short = _short_name(name)[:20]
        am = re.search(r"([\d.]+)\s*(?:mg|g|kg|%)\s*" + re.escape(short), text, re.I)
        if not am:
            am = re.search(re.escape(short) + r"[^.,;]*?([\d.]+)\s*(?:mg|g|kg|%)", text, re.I)
        if am:
            amounts.append(float(am.group(1)))
    if len(amounts) == 2 and amounts[0] > 0 and amounts[1] > 0:
        g = _gcd_ratio(amounts[0], amounts[1])
        return f"about {int(amounts[0] / g)}:{int(amounts[1] / g)}"
    return None


def _parse_invention(inputs: dict[str, Any], resolved: list[dict[str, Any]]) -> dict[str, Any]:
    """Eureka step 1 — parse the invention description into structured drafting elements."""
    problem = (
        _text(inputs, "problem_text", "invention_description", "formulation_text")
        or _basis_text(inputs, "disclosure_text", "document_text")
        or "An Ayurvedic botanical composition"
    )
    ingredients = [_short_name(cast(str, r.get("botanical_name") or r.get("raw_name"))) for r in resolved if r.get("raw_name")]
    names = ingredients[:4] or ["an Ayurvedic botanical"]
    process = _text(inputs, "process_desc", "process")
    steps = _process_steps(process)
    solvent_m = _SOLVENT.search(f"{process} {problem}")
    solvent = solvent_m.group(0).capitalize() if solvent_m else ""
    markers = _value_markers(f"{process} {problem}")
    marker_solvent = next(
        (m for m in markers if any(k in m.lower() for k in ("ethanol", "alcohol", "glycerol", "water", "maceration"))),
        "",
    )
    if marker_solvent:
        solvent = marker_solvent[0].upper() + marker_solvent[1:]
    solvent_words: set = set()
    if _solvent_word(solvent):
        solvent_words.add(_solvent_word(solvent))
    if solvent and solvent_words:
        markers = [m for m in markers if not any(w in m.lower() for w in solvent_words)]
    dosage_form = _text(inputs, "dosage_form") or "an Ayurvedic dosage form"
    use = _text(inputs, "intended_use") or _text(inputs, "claimed_innovation")
    if not use:
        pu = _PURPOSE.search(problem)
        use = pu.group(0) if pu else "nutritional or wellness application"
    title = _first_sentence(problem)
    if len(title) > 110:
        title = title[:110].rsplit(" ", 1)[0] + "..."
    if not re.search(r"(composition|formulation|method|process|preparation|extract)", title, re.I):
        title = f"A composition and method for preparing the same comprising {' and '.join(names[:2])}"
    return {
        "problem": problem,
        "title": title,
        "ingredients": names,
        "steps": steps,
        "solvent": solvent,
        "dosage_form": dosage_form,
        "use": use,
        "markers": markers,
        "ratio": _detected_ratio(f"{_text(inputs, 'formulation_text')} {problem}", names),
    }


def _citation_kind(c: dict[str, Any]) -> str:
    t = ((c.get("act_title") or "") + " " + (c.get("authority") or "")).lower()
    if "patent" in t:
        return "Patent prior-art"
    if re.search(r"traditional|ayurveda|charaka|susruta|tkdl|monograph", t):
        return "Traditional-knowledge material"
    sk = _source_kind(c.get("authority") or "")
    if sk.startswith("Regulatory corpus"):
        return "Regulatory material"
    if sk.startswith("Scientific literature"):
        return "Non-patent / technical (literature)"
    return "Non-patent / technical"


def _split_claims_txt(text: str) -> list[tuple]:
    claims = re.findall(r"(?:^|\n)\s*(\d+)\s*[.)\]]\s+(.*?)(?=\n\s*\d+\s*[.)\]]|\Z)", text or "", re.S)
    if not claims:
        cleaned = (text or "").strip()
        return [("1", cleaned)] if cleaned else []
    return [(num, body.strip()) for num, body in claims]


def _claim_elements(body: str) -> list[str]:
    parts = re.split(r";\s*|\.\s+", body)
    els: list[str] = []
    for p in parts:
        p = re.sub(r"^\s*(?:[a-e][).]?\s*|\d+\s*[.)]?\s*)", "", p).strip(" .;,").strip()
        if p and len(p) > 3 and not re.fullmatch(r"[A-Za-z]+", p):
            els.append(p[:110])
    return els[:12]


_LCA_TOKEN_RE = re.compile(r"[A-Z][A-Za-z0-9'’/\-]+(?:[ \-][A-Za-z0-9][A-Za-z0-9'’/\-]*)?")


_LCA_GUIDANCE_HINTS = re.compile(
    r"(guideline|guidance|examination|landscape|checklist|policy|handbook|monograph|procedure\s+for|"
    r"act[,\.]?\s+|regulations?|directive|dshea|federal\s+food|biodiversity|access\s+and\s+benefit|"
    r"traditional\s+knowledge|ayurvedic\s+pharmacopoeia|pharmacopoeia)",
    re.I,
)


_LSM_FORMULA_RE = re.compile(r"\bC\d+(?:H\d+)?(?:[NOSPClI][a-z]?\d*)+\b")
