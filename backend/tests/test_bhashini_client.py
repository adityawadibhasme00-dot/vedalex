import os
from unittest.mock import patch

from app.services.bhashini_client import BhashiniClient


def test_mask_unmask_roundtrip():
    q = "Can I patent turmeric? Section 3(p) of the Patents Act applies, Rule 14(2) of the Biological Diversity Rules 2024 and TKDL and NBA clearance needed."
    masked, terms = BhashiniClient.mask_legal_terms(q)
    assert "Section 3(p)" not in masked
    assert "TKDL" not in masked
    restored = BhashiniClient.unmask_legal_terms(masked, terms)
    assert restored == q


def test_mask_preserves_legal_acronyms():
    masked, terms = BhashiniClient.mask_legal_terms("FSSAI and CDSCO and TKDL approvals under First Schedule")
    assert all(t in ("FSSAI", "CDSCO", "TKDL", "First Schedule") for t in terms)
    assert "FSSAI" not in masked and "TKDL" not in masked


def test_disabled_when_no_key():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("IPSAKTI_BHASHINI_API_KEY", None)
        os.environ.pop("IPSAKTI_BHASHINI_USER_ID", None)
        assert BhashiniClient.is_enabled() is False
        assert BhashiniClient.translate_query_to_english("नमस्ते", "hi") is None
        assert BhashiniClient.translate_answer_to_lang("Hello", "hi") is None


def test_noop_same_language():
    assert BhashiniClient.translate("hello", "en", "en") is None


def test_status_shape():
    s = BhashiniClient.status()
    assert s["enabled"] in (True, False)
    assert "provider" in s