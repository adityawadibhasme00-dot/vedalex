"""Path tests for language detection and localized UI text in multilingual_nlp."""

import pytest

from app.services.multilingual_nlp import MultilingualNLPEngine as engine

pytestmark = pytest.mark.unit

LANGUAGE_SAMPLES = [
    ("marathi-hint", "हळद आणि तुळस", "mr"),
    ("hindi-hint", "हल्दी और तुलसी", "hi"),
    ("sanskrit-hint", "निम्ब कषायम्", "sa"),
    ("marathi-marker", "योग आहे साठी", "mr"),
    ("devanagari-default", "कुछ हिंदी पाठ", "hi"),
    ("tamil", "தமிழ் மூலிகை", "ta"),
    ("telugu", "తెలుగు మొక్క", "te"),
    ("kannada", "ಕನ್ನಡ ಸಸ್ಯ", "kn"),
    ("bengali", "বাংলা গাছ", "bn"),
    ("gujarati", "ગુજરાતી છોડ", "gu"),
    ("malayalam", "മലയാളം ചെടി", "ml"),
    ("latin", "plain english text", "en"),
    ("empty", "", "en"),
]

LANG_SCRIPT_RANGES = {
    "hi": (0x0900, 0x097F),
    "mr": (0x0900, 0x097F),
    "sa": (0x0900, 0x097F),
    "ta": (0x0B80, 0x0BFF),
    "te": (0x0C00, 0x0C7F),
    "kn": (0x0C80, 0x0CFF),
    "bn": (0x0980, 0x09FF),
    "gu": (0x0A80, 0x0AFF),
    "ml": (0x0D00, 0x0D7F),
}


@pytest.mark.parametrize(
    "text,expected",
    [(text, expected) for _, text, expected in LANGUAGE_SAMPLES],
    ids=[sample_id for sample_id, _, _ in LANGUAGE_SAMPLES],
)
def test_detect_language_identifies_supported_scripts(text, expected):
    assert engine.detect_language(text) == expected


def test_detect_language_defaults_unmarked_devanagari_to_hindi():
    assert engine.detect_language("नमस्ते और आभार") == "hi"


@pytest.mark.xfail(
    reason="Hindi hints are substring-matched before the Sanskrit hints, so Sanskrit 'गुग्गुलु' is read as Hindi 'गुग्गुल' and the sa branch is skipped (multilingual_nlp.py:47)",
    strict=False,
)
def test_detect_language_distinguishes_sanskrit_from_hindi():
    assert engine.detect_language("निम्ब गुग्गुलु") == "sa"


def test_characterization_detect_language_uses_first_matching_script():
    assert engine.detect_language("தமிழ் हिन्दी") == "hi"
    assert engine.detect_language("தமிழ் తెలుగు") == "ta"


@pytest.mark.parametrize("key", ["why_view_title", "what_if_title"])
@pytest.mark.parametrize(
    "lang", ["en", "hi", "mr", "ta", "te", "kn", "bn", "gu", "ml", "sa"]
)
def test_localized_ui_text_returns_translation_for_every_language(key, lang):
    text = engine.get_localized_ui_text(key, lang)

    assert text
    assert text != key
    if lang == "en":
        assert text.isascii()
    else:
        assert text != engine.get_localized_ui_text(key, "en")
        low, high = LANG_SCRIPT_RANGES[lang]
        assert any(low <= ord(char) <= high for char in text)


def test_localized_ui_text_falls_back_to_english_for_unknown_language():
    assert engine.get_localized_ui_text("why_view_title", "pa") == (
        engine.get_localized_ui_text("why_view_title", "en")
    )


def test_localized_ui_text_returns_key_for_unknown_key():
    assert engine.get_localized_ui_text("no_such_key", "hi") == "no_such_key"
    assert engine.get_localized_ui_text("", "en") == ""


def test_normalize_botanical_mentions_maps_aliases_across_scripts():
    english = engine.normalize_botanical_mentions("Ashwagandha and Brahmi extract")
    assert ("Ashwagandha", "ING-ASHWAGANDHA", 0.95) in english
    assert ("Brahmi", "ING-BRAHMI", 0.95) in english

    hindi = engine.normalize_botanical_mentions("तुलसी और नीम का सेवन")
    assert ("तुलसी", "ING-TULSI", 0.95) in hindi
    assert ("नीम", "ING-NEEM", 0.95) in hindi

    assert engine.normalize_botanical_mentions("zinc oxide") == []


def test_normalize_botanical_mentions_preserves_original_casing():
    results = engine.normalize_botanical_mentions("ASHWAGANDHA extract")

    assert results == [("ASHWAGANDHA", "ING-ASHWAGANDHA", 0.95)]


def test_normalize_botanical_mentions_skips_empty_aliases(monkeypatch):
    monkeypatch.setattr(
        engine,
        "_synonyms_data",
        {"ING-NETTLE": {"english": ["", "Nettle Leaf"], "hindi": []}},
    )

    assert engine.normalize_botanical_mentions("Nettle Leaf tea") == [
        ("Nettle Leaf", "ING-NETTLE", 0.95)
    ]
    assert engine.normalize_botanical_mentions("nothing matched here") == []


@pytest.mark.xfail(
    reason="language codes are matched case-sensitively, so 'HI' silently falls back to the English string instead of the Hindi one (multilingual_nlp.py:129)",
    strict=False,
)
def test_localized_ui_text_accepts_uppercase_language_code():
    assert engine.get_localized_ui_text("why_view_title", "HI") == (
        engine.get_localized_ui_text("why_view_title", "hi")
    )
