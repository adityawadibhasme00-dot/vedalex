from typing import Any

import pytest

from app.services.innolab import triz_data as tz


def test_parameters_table_integrity():
    assert len(tz.TRIZ_PARAMETERS) == 39
    assert [no for no, _, _ in tz.TRIZ_PARAMETERS] == list(range(1, 40))
    assert all(name.strip() and desc.strip() for _, name, desc in tz.TRIZ_PARAMETERS)
    assert len(tz.PARAM_BY_NO) == 39
    assert tz.PARAM_BY_NO[13][0] == "Stability of object's composition"
    assert tz.PARAM_BY_NO[39][0] == "Productivity"


def test_principles_table_integrity():
    assert len(tz.TRIZ_PRINCIPLES) == 40
    assert [no for no, _, _ in tz.TRIZ_PRINCIPLES] == list(range(1, 41))
    assert all(name.strip() and idea.strip() for _, name, idea in tz.TRIZ_PRINCIPLES)
    assert len(tz.PRINCIPLE_BY_NO) == 40
    assert tz.PRINCIPLE_BY_NO[1][0] == "Segmentation"
    assert tz.PRINCIPLE_BY_NO[40][0] == "Composite materials"


def test_param_hints_cover_all_parameters():
    hint_nos = [no for no, _ in tz._PARAM_HINTS]
    assert set(hint_nos) == set(range(1, 40))
    for _, hints in tz._PARAM_HINTS:
        assert hints
        assert all(h == h.lower().strip() and h for h in hints)


def test_principle_applications_cover_all_principles():
    assert set(tz._PRINCIPLE_APPLICATIONS) == set(range(1, 41))
    for card in tz._PRINCIPLE_APPLICATIONS.values():
        assert len(card) == 4
        assert all(isinstance(part, str) and part.strip() for part in card)


def test_ipsakti_fit_table():
    assert set(tz._IPSAKTI_FIT) == set(range(1, 41))
    assert all(0 <= v <= 10 for v in tz._IPSAKTI_FIT.values())


def test_rca_hypotheses_shape():
    assert len(tz.RCA_HYPOTHESES) == 5
    ids = [h["id"] for h in tz.RCA_HYPOTHESES]
    assert ids == [f"rca-{i}" for i in range(1, 6)]
    for hyp in tz.RCA_HYPOTHESES:
        assert set(hyp) == {"id", "title", "detail", "confirm"}
        assert all(hyp[k].strip() for k in ("title", "detail", "confirm"))


def test_load_matrix_returns_tuple_keys_and_int_principles():
    cells = tz.load_matrix()
    assert len(cells) >= 1100
    for key, principles in cells.items():
        assert isinstance(key, tuple) and len(key) == 2
        assert all(isinstance(v, int) for v in key)
        assert all(1 <= v <= 40 for v in principles)
        assert principles


def test_matrix_is_cached_singleton():
    first = tz.matrix()
    second = tz.matrix()
    assert first is second
    assert first == tz.load_matrix()


def test_lookup_cell_matrix_provenance():
    cells = tz.matrix()
    key = next(iter(sorted(cells)))
    out = tz.lookup_cell(key[0], key[1])
    assert out["source"] == "matrix"
    assert out["cell"] == f"{key[0]}→{key[1]}"
    assert out["principles"] == cells[key]


def test_lookup_cell_reverse_provenance():
    cells = tz.matrix()
    forward = next(k for k in sorted(cells) if (k[1], k[0]) not in cells)
    out = tz.lookup_cell(forward[1], forward[0])
    assert out["source"] == "reverse"
    assert out["cell"] == f"{forward[0]}→{forward[1]} (reversed)"
    assert out["principles"] == cells[forward]


def test_lookup_cell_inferred_provenance():
    cells = tz.matrix()
    assert (13, 13) not in cells
    out = tz.lookup_cell(13, 13)
    assert out["source"] == "inferred"
    assert out["cell"] == "13→13"
    assert out["principles"] == [35, 1, 2]
    assert tz.lookup_cell(17, 13)["source"] == "matrix"


def test_lookup_cell_empty_provenance():
    cells = tz.matrix()
    proposals = {(13, 13), (17, 13)}
    empty_pair = None
    for i in range(1, 40):
        for w in range(1, 40):
            if (i, w) in cells or (w, i) in cells or (i, w) in proposals:
                continue
            empty_pair = (i, w)
            break
        if empty_pair:
            break
    assert empty_pair is not None
    out = tz.lookup_cell(empty_pair[0], empty_pair[1])
    assert out["source"] == "empty"
    assert out["principles"] == []
    assert out["cell"] == f"{empty_pair[0]}→{empty_pair[1]}"


def test_frequency_counts_match_matrix():
    assert tz.FREQUENCY == tz._frequency_counts()
    total = sum(len(v) for v in tz.matrix().values())
    assert sum(tz.FREQUENCY.values()) == total
    assert set(tz.FREQUENCY) <= set(range(1, 41))
    assert len(tz.FREQUENCY) >= 35
    assert all(v > 0 for v in tz.FREQUENCY.values())


@pytest.mark.parametrize("no", [1, 35, 40])
def test_principle_application_known_cards(no):
    card = tz.principle_application(no)
    assert card is tz._PRINCIPLE_APPLICATIONS[no]
    assert all(isinstance(part, str) and part.strip() for part in card)


def test_principle_application_fallback():
    card = tz.principle_application(99)
    assert card == tz._APPLICATION_FALLBACK
    assert tz.principle_application(0) == tz._APPLICATION_FALLBACK


@pytest.mark.parametrize(
    "phrase,no,confidence",
    [
        ("extraction rate is too slow", 9, "high"),
        ("stability degrades during storage", 13, "high"),
        ("lightweight tank housing", 2, "high"),
        ("filter area of the moving belt", 5, "high"),
        ("pressures rise inside the vessel", 11, "medium"),
    ],
)
def test_map_parameter_known_phrases(phrase, no, confidence):
    out = tz.map_parameter(phrase)
    assert out["no"] == no
    assert out["name"] == tz.PARAM_BY_NO[no][0]
    assert out["confidence"] == confidence
    assert out["matched_hint"]


def test_map_parameter_empty_inputs():
    values: list[Any] = ["", None, "   "]
    for phrase in values:
        out = tz.map_parameter(phrase)
        assert out == {"no": None, "name": "", "confidence": "low", "matched_hint": ""}


def test_map_parameter_unmatched_phrase_is_low_confidence():
    out = tz.map_parameter("zulu quebec yankee nebula")
    assert out["no"] is None
    assert out["confidence"] == "low"
    assert out["matched_hint"] == ""


def test_brief_context_signal_extraction():
    assert tz.brief_context("Stability and yield fall when temperature rises") == "stability, yield, temperature"
    assert tz.brief_context("shelf life and moisture pickup") == "shelf life, moisture"
    assert tz.brief_context("zzz qqq") == "the stated problem"
    assert tz.brief_context("batch scale-up costs time") == "cost, time, batch, scale"
