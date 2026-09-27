"""Tests for the guarded PATENTSCOPE adapter (link builder + optional gateway)."""

from typing import cast
from unittest.mock import patch

import pytest

from app.services import patentscope_client as pc

pytestmark = pytest.mark.unit


def _gateway(url="https://gateway.test/patentscope"):
    return patch.object(pc, "GATEWAY_URL", url)


def test_cql_terms_quote_each_term_and_cap_at_four():
    terms = ["Ashwagandha", "Brahmi", "Neem", "Tulsi", "Haldi"]
    query = pc._cql_terms(terms)

    assert query.startswith("EN_AB:(")
    assert " OR EN_CLMS:(" in query
    assert query.count('"') == 16
    assert "Haldi" not in query


def test_cql_terms_strips_punctuation_from_terms():
    query = pc._cql_terms(["ashwagandha-root", "curcumin (95%)"])

    assert '"ashwagandha root"' in query
    assert "95" in query
    assert "-" not in query
    assert "%" not in query
    assert "(" not in query.split("EN_AB:(", 1)[1].replace("EN_CLMS:(", "")


def test_cql_terms_returns_empty_for_unusable_terms():
    assert pc._cql_terms([]) == ""
    assert pc._cql_terms(["!!!", "   ", "###"]) == ""


def test_build_search_link_includes_tab_query_and_country_codes():
    link = pc.build_search_link(["Ashwagandha", "Brahmi"], ["India", "United States"])

    assert link.startswith(pc.ADVANCED_SEARCH_URL + "?")
    assert "tab=PCTBiblio" in link
    assert "query=EN_AB%3A" in link
    assert "cntry=India%2CUnited%20States" in link


def test_build_search_link_omits_country_when_no_markets():
    link = pc.build_search_link(["Ashwagandha"])

    assert "query=" in link
    assert "cntry=" not in link


def test_build_search_link_without_terms_still_builds_a_url():
    link = pc.build_search_link([], ["India"])

    assert link.startswith(pc.ADVANCED_SEARCH_URL + "?")
    assert "cntry=India" in link


def test_build_inpass_link_with_and_without_application_number():
    assert pc.build_inpass_link(None) == "https://iprsearch.ipindia.gov.in/PublicSearch/"
    link = pc.build_inpass_link("202314000123")
    assert link.startswith("https://iprsearch.ipindia.gov.in/PublicSearch/?searchtype=applicationNumber")
    assert "q=202314000123" in link


def test_build_tkdl_link_quotes_keyword():
    link = pc.build_tkdl_link("Withania somnifera")

    assert link.startswith("https://tkdl.res.in/tkdl/langdefault/common/Search.asp?gl=EN&q=")
    assert "Withania%20somnifera" in link


def test_gateway_live_reflects_configuration():
    with _gateway(""):
        assert pc.gateway_live() is False
    with _gateway("https://gateway.test/search"):
        assert pc.gateway_live() is True


def test_patentscope_status_reports_no_public_api():
    with _gateway(""):
        status = pc.patentscope_status()

    assert status["public_api"] is False
    assert status["gateway_configured"] is False
    assert status["advanced_search_url"] == pc.ADVANCED_SEARCH_URL
    assert "no public REST/JSON" in status["note"]


def test_search_live_returns_none_without_gateway():
    with _gateway(""), patch("requests.post") as mock_post:
        assert pc.search_live("EN_AB:(ashwagandha)") is None

    mock_post.assert_not_called()


def test_search_live_maps_gateway_records():
    payload = {
        "records": [
            {
                "publication_number": "WO/2020/001234",
                "publication_date": "2020-04-01",
                "title": "Ashwagandha extract",
                "applicants": ["Example Corp"],
                "abstract": "An extract",
                "score": 91.4,
                "jurisdiction": "International",
            },
            {
                "patent_id": "US1011111",
                "title": "Brahmi composition",
                "similarity": 12.5,
                "applicant": "Solo Inventor",
                "publication_date": "2019",
            },
        ]
    }
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = payload
        results = pc.search_live("EN_AB:(ashwagandha)", limit=5)

    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["json"] == {
        "query": "EN_AB:(ashwagandha)",
        "limit": 5,
        "kind": "prior_art",
    }
    assert results is not None
    assert results[0] == {
        "patent_id": "WO/2020/001234",
        "title": "Ashwagandha extract",
        "similarity": 91.4,
        "jurisdiction": "International",
        "publication_date": "2020-04-01",
        "applicant": ["Example Corp"],
        "source": "patentscope-live",
    }
    assert results[1]["patent_id"] == "US1011111"
    assert results[1]["similarity"] == 12.5
    assert results[1]["jurisdiction"] == "International"
    assert results[1]["applicant"] == "Solo Inventor"
    assert results[1]["source"] == "patentscope-live"


def test_search_live_defaults_fill_missing_record_fields():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"records": [{"publication_number": "WO2"}]}
        results = pc.search_live("q")

    assert results is not None
    assert results[0]["similarity"] == 50.0
    assert results[0]["jurisdiction"] == "International"
    assert results[0]["publication_date"] == ""
    assert results[0]["applicant"] == ""


def test_search_live_respects_limit():
    records = [{"publication_number": f"WO{n}"} for n in range(5)]
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"records": records}
        results = pc.search_live("q", limit=2)

    assert results is not None
    assert len(results) == 2
    assert mock_post.call_args.kwargs["timeout"] == pc.TIMEOUT


def test_search_live_skips_non_dict_records():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"records": [7, "junk", {"publication_number": "WO1"}]}
        results = pc.search_live("q")

    assert results is not None
    assert [r["patent_id"] for r in results] == ["WO1"]


def test_search_live_returns_none_for_non_list_records():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"records": "not-a-list"}
        assert pc.search_live("q") is None


def test_search_live_returns_empty_list_when_payload_has_no_records():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {}
        assert pc.search_live("q") == []


def test_search_live_accepts_results_key_as_records_alias():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"results": [{"publication_number": "WO9"}]}
        results = pc.search_live("q")

    assert results is not None
    assert results[0]["patent_id"] == "WO9"


def test_search_live_degrades_to_none_on_http_error():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.raise_for_status.side_effect = RuntimeError("HTTP 502")
        assert pc.search_live("q") is None


def test_search_live_degrades_to_none_on_invalid_json():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.side_effect = ValueError("not json")
        assert pc.search_live("q") is None


@pytest.mark.xfail(
    reason="a non-numeric gateway score is converted outside the try/except and raises ValueError, breaking the documented silent-None contract (patentscope_client.py:106)",
    strict=False,
)
def test_search_live_survives_malformed_score():
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "records": [{"publication_number": "WO1", "score": "high"}]
        }
        assert pc.search_live("q") is None


@pytest.mark.xfail(
    reason="limit is never validated, so a negative limit is applied as a Python slice and silently drops the trailing records (patentscope_client.py:100)",
    strict=False,
)
def test_search_live_rejects_negative_limit():
    records = [{"publication_number": f"WO{n}"} for n in range(3)]
    with _gateway(), patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"records": records}
        pc.search_live("q", limit=-1)

    raise AssertionError("negative limit must be rejected")


@pytest.mark.xfail(
    reason="target_markets is joined without type validation, so a plain string is joined character-by-character into cntry (patentscope_client.py:46)",
    strict=False,
)
def test_build_search_link_validates_target_markets_type():
    link = pc.build_search_link(["Ashwagandha"], cast("list[str] | None", "India"))

    assert "cntry=India" in link
