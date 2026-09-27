"""Tests for the India Code (eCourtsIndia) statute API client and harvester."""

from unittest.mock import patch

from app.services import indiacode_client as ic
from app.services.indiacode_harvester import register_section_passages


def test_tracked_acts_cover_main_ip_statutes():
    ids = {a["id"] for a in ic.INDIA_CODE_ACTS}
    assert "patents-act" in ids
    assert "biological-diversity-act-2002" in ids
    assert "trade-marks-act" in ids
    assert "copyright-act" in ids
    assert "designs-act-2000" in ids
    assert "geographical-indications-goods-registration-protection-act-1999" in ids
    assert "drugs-cosmetics-act-1940" in ids
    assert "protection-plant-varieties-farmers-rights-act-2001" in ids


def test_statute_document_matches_extraction_schema():
    d = ic.statute_document(
        {"authority": "Legislative Department", "jurisdiction": "India",
         "act_name": "patents_act_1970"},
        {"act": {"id": "patents-act", "short_title": "The Patents Act, 1970"},
         "section": {"number": "3", "heading": "What are not inventions",
                     "text": "The following are not inventions... (p) traditional knowledge"}},
        "3",
    )
    assert d["source"] == "india_code"
    assert d["document_type"] == "statute"
    assert d["document_id"] == "patents-act_section_3"
    assert d["locator"]["section"] == "3"
    assert d["locator"]["act_id"] == "patents-act"
    assert d["source_url"].endswith("/patents-act/section/3/")
    assert len(d["checksum"]) == 64
    assert d["review_status"] == "auto_ingested"


def test_section_number_preserves_alphanumeric_form():
    d = ic.statute_document(
        {"authority": "A", "jurisdiction": "India", "act_name": "bns"},
        {"act": {"id": "bns", "short_title": "BNS"},
         "section": {"number": "124A", "heading": "", "text": "text"}},
        "124A",
    )
    assert d["document_id"] == "bns_section_124a"


@patch("app.services.indiacode_client._http_get")
def test_resolve_act_short_circuits_on_id(mock_get):
    mock_get.return_value = {"id": "patents-act", "section_count": 179}
    result = ic.resolve_act("The Patents Act, 1970", act_id="patents-act")
    assert result is not None
    assert result["id"] == "patents-act"
    mock_get.assert_called_once_with(
        "https://indiacode.ecourtsindia.com/api/v1/acts/patents-act"
    )


@patch("app.services.indiacode_client._http_get")
def test_harvest_sections_skips_missing(mock_get):
    mock_get.side_effect = [
        {"id": "patents-act", "short_title": "The Patents Act, 1970"},          # resolve_act
        {"act": {"id": "patents-act"}, "section": {"number": "3", "text": "text-of-3"}},   # fetch section 3
        None,                                                                    # section 10 missing
    ]
    act = {
        "id": "patents-act", "act_name": "patents_act_1970",
        "title": "The Patents Act, 1970", "authority": "Legislative Department",
        "jurisdiction": "India", "priority_sections": ["3", "10"],
    }
    docs = ic.harvest_sections_for_act(act)
    assert len(docs) == 1
    assert docs[0]["document_id"] == "patents-act_section_3"


@patch("app.services.indiacode_client._http_get")
def test_unresolvable_act_returns_empty(mock_get):
    mock_get.return_value = None
    act = {"id": "no-such-act", "title": "Missing Act", "priority_sections": ["1"]}
    assert ic.harvest_sections_for_act(act) == []


def test_register_section_passages_into_engine():
    from app.services.retrieval_engine import HybridRetrievalEngine
    saved_db = list(HybridRetrievalEngine._passages_db)
    saved_loaded = HybridRetrievalEngine._loaded
    HybridRetrievalEngine._passages_db = []
    HybridRetrievalEngine._loaded = True
    try:
        count = register_section_passages([{
            "title": "Patents Act — Section 3",
            "locator": {"section": "3", "act_id": "patents-act"},
            "authority": "Legislative Department",
            "jurisdiction": "India",
            "text": "The following are not inventions within the meaning of this Act",
            "source_url": "https://indiacode.ecourtsindia.com/patents-act/section/3/",
            "effective_from": "",
            "document_id": "patents-act_section_3",
        }])
        assert count == 1
        hits = HybridRetrievalEngine.search_passages("traditional knowledge inventions", top_k=1)
        assert hits
        assert "Patents Act" in hits[0].act_title
    finally:
        HybridRetrievalEngine._passages_db = saved_db
        HybridRetrievalEngine._loaded = saved_loaded