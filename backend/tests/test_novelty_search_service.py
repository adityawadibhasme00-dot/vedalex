"""Tests for the live novelty / prior-art search service (every surface mocked)."""

from unittest.mock import patch

import pytest

from app.models.passport import IngredientEntry, InnovationPassport
from app.services import novelty_search_service as nss
from app.services import patentscope_client

pytestmark = pytest.mark.unit


def make_passport(ingredients=None, **kwargs):
    if ingredients is None:
        ingredients = [
            IngredientEntry(
                raw_name="Ashwagandha",
                botanical_name="Withania somnifera",
                canonical_id="ING-ASHWAGANDHA",
            ),
            IngredientEntry(
                raw_name="Brahmi",
                botanical_name="Bacopa monnieri",
                canonical_id="ING-BRAHMI",
            ),
        ]
    payload = {
        "claimed_innovation": "Standardised ashwagandha and brahmi extract",
        "process_description": "Aqueous decoction followed by spray drying",
        "target_markets": ["India"],
        "ingredients": ingredients,
    }
    payload.update(kwargs)
    return InnovationPassport(**payload)


def unmatched_passport(**kwargs):
    kwargs.setdefault(
        "ingredients",
        [IngredientEntry(raw_name="Zinc Oxide", botanical_name="", canonical_id="ING-ZINC-OXIDE")],
    )
    return make_passport(**kwargs)


def test_offline_report_shape_and_search_links():
    passport = make_passport()
    report = nss.run_novelty_search(passport, include_local_corpus=False, live=False)

    assert report["passport_id"] == passport.id
    assert report["query"]["ingredients"] == [
        "Ashwagandha",
        "Withania somnifera",
        "Brahmi",
        "Bacopa monnieri",
    ]
    assert report["query"]["target_markets"] == ["India"]
    assert report["surface_status"]["permitted_tk_corpus"] == "searched"
    assert report["surface_status"]["local_patent_corpus"] == "not_searched"
    assert report["surface_status"]["patentscope_live"] != "searched"
    assert report["surface_status"]["inpass_status"] != "searched"
    assert report["inpass_application_status"] is None
    assert report["hits"]["local_corpus"] == []
    assert report["hits"]["live"] == []
    assert "not a Freedom-to-Operate opinion" in report["coverage_limitations"]
    assert report["patentscope_availability"]["public_api"] is False

    links = report["search_links"]
    assert links["patentscope"].startswith("https://patentscope.wipo.int/search/en/advancedSearch.jsf")
    assert "cntry=India" in links["patentscope"]
    assert links["inpass"].startswith("https://iprsearch.ipindia.gov.in/PublicSearch/")
    assert links["tkdl"].startswith("https://tkdl.res.in/tkdl/langdefault/common/Search.asp")
    assert "q=Ashwagandha" in links["tkdl"]


def test_tk_hit_with_full_record_coverage_is_high_exposure():
    report = nss.run_novelty_search(make_passport(), include_local_corpus=False, live=False)

    tk_hits = report["hits"]["permitted_tk"]
    assert len(tk_hits) == 1
    hit = tk_hits[0]
    assert hit["tk_reference_id"] == "TK-CLASSIC-CHARAKA-01"
    assert hit["shared_ingredients"] == ["ING-ASHWAGANDHA", "ING-BRAHMI"]
    assert hit["coverage_pct"] == 100.0
    assert hit["source"] == "permitted-tk-corpus"
    assert hit["traditional_indication"]
    assert hit["relevance_under_sec3p"]
    assert report["strongest_overlap_pct"] == 100.0
    assert report["hit_count"] == 1
    assert report["exposure_tier"] == "HIGH_PRIOR_ART_EXPOSURE"
    assert report["exposure_band"] == "risk"


def test_tk_hit_with_partial_coverage_is_moderate_exposure():
    passport = make_passport(
        ingredients=[
            IngredientEntry(
                raw_name="Ashwagandha",
                botanical_name="Withania somnifera",
                canonical_id="ING-ASHWAGANDHA",
            )
        ]
    )
    report = nss.run_novelty_search(passport, include_local_corpus=False, live=False)

    tk_hits = report["hits"]["permitted_tk"]
    assert len(tk_hits) == 1
    assert tk_hits[0]["coverage_pct"] == 50.0
    assert tk_hits[0]["shared_ingredients"] == ["ING-ASHWAGANDHA"]
    assert report["exposure_tier"] == "MODERATE_PRIOR_ART_EXPOSURE"
    assert report["exposure_band"] == "warn"


def test_unmatched_formulation_reports_no_prior_art():
    passport = make_passport(
        ingredients=[
            IngredientEntry(raw_name="Zinc Oxide", botanical_name="", canonical_id="ING-ZINC-OXIDE")
        ]
    )
    report = nss.run_novelty_search(passport, include_local_corpus=False, live=False)

    assert report["hits"]["permitted_tk"] == []
    assert report["hit_count"] == 0
    assert report["strongest_overlap_pct"] == 0.0
    assert report["exposure_tier"] == "NO_MATCHES_FOUND"
    assert report["exposure_band"] == "warn"


def test_missing_tk_corpus_file_yields_no_tk_hits(tmp_path, monkeypatch):
    monkeypatch.setattr(nss, "_TK_PATH", str(tmp_path / "absent-tk-corpus.json"))
    report = nss.run_novelty_search(make_passport(), include_local_corpus=False, live=False)

    assert report["hits"]["permitted_tk"] == []
    assert report["hit_count"] == 0


def test_local_corpus_hits_are_mapped_and_rounded():
    sources = [
        {
            "patent_number": "US1011111",
            "title": "Ashwagandha extract capsule",
            "score": 0.9123,
            "jurisdiction": "US",
            "publication_year": "2021",
        },
        {
            "document_id": "DOC-77",
            "title": "Brahmi composition",
            "score": 0.0549,
            "jurisdiction": "",
            "date": "2019",
        },
    ]
    with patch(
        "app.rag.retrieval_pipeline.HybridRetriever.retrieve",
        return_value={"sources": sources},
    ) as mock_retrieve:
        report = nss.run_novelty_search(unmatched_passport(), include_local_corpus=True, live=False)

    mock_retrieve.assert_called_once()
    assert mock_retrieve.call_args.kwargs["category"] == "patent"
    assert "ashwagandha" in mock_retrieve.call_args.kwargs["query"]

    hits = report["hits"]["local_corpus"]
    assert len(hits) == 2
    assert hits[0] == {
        "patent_id": "US1011111",
        "title": "Ashwagandha extract capsule",
        "similarity": 91.2,
        "jurisdiction": "US",
        "publication_date": "2021",
        "source": "local-patent-corpus",
    }
    assert hits[1]["patent_id"] == "DOC-77"
    assert hits[1]["similarity"] == 5.5
    assert hits[1]["publication_date"] == "2019"
    assert report["strongest_overlap_pct"] == 91.2
    assert report["exposure_tier"] == "HIGH_PRIOR_ART_EXPOSURE"


def test_local_corpus_disabled_is_reported_as_not_searched():
    with patch("app.rag.retrieval_pipeline.HybridRetriever.retrieve") as mock_retrieve:
        report = nss.run_novelty_search(make_passport(), include_local_corpus=False, live=False)

    mock_retrieve.assert_not_called()
    assert report["hits"]["local_corpus"] == []
    assert report["surface_status"]["local_patent_corpus"] == "not_searched"


def test_weak_local_hit_keeps_exposure_low():
    sources = [{"patent_number": "WO1", "title": "Distant match", "score": 0.12}]
    with patch(
        "app.rag.retrieval_pipeline.HybridRetriever.retrieve",
        return_value={"sources": sources},
    ):
        report = nss.run_novelty_search(unmatched_passport(), include_local_corpus=True, live=False)

    assert report["strongest_overlap_pct"] == 12.0
    assert report["exposure_tier"] == "LOW_PRIOR_ART_EXPOSURE"
    assert report["exposure_band"] == "good"


def test_live_gateway_hits_are_merged_into_report():
    live_records = [
        {
            "patent_id": "WO/2020/001",
            "title": "Ashwagandha formulations",
            "similarity": 88.5,
            "jurisdiction": "International",
            "publication_date": "2020-04-01",
            "applicant": "Example Corp",
            "source": "patentscope-live",
        }
    ]
    with patch.object(patentscope_client, "gateway_live", return_value=True), patch.object(
        patentscope_client, "search_live", return_value=live_records
    ) as mock_search:
        report = nss.run_novelty_search(unmatched_passport(), include_local_corpus=False, live=True)

    assert report["surface_status"]["patentscope_live"] == "searched"
    assert report["hits"]["live"] == live_records
    assert report["hit_count"] == 1
    assert report["strongest_overlap_pct"] == 88.5
    assert report["exposure_tier"] == "HIGH_PRIOR_ART_EXPOSURE"
    assert mock_search.call_count == 1
    assert "patentscope.wipo.int" in mock_search.call_args.args[0]


def test_live_gateway_without_results_is_marked_unavailable():
    with patch.object(patentscope_client, "gateway_live", return_value=True), patch.object(
        patentscope_client, "search_live", return_value=None
    ) as mock_search:
        report = nss.run_novelty_search(make_passport(), include_local_corpus=False, live=True)

    assert report["surface_status"]["patentscope_live"] == "unavailable"
    assert report["hits"]["live"] == []
    assert mock_search.call_count == 1


def test_unconfigured_gateway_is_skipped_without_any_call():
    with patch.object(patentscope_client, "GATEWAY_URL", ""), patch.object(
        patentscope_client, "search_live"
    ) as mock_search:
        report = nss.run_novelty_search(make_passport(), include_local_corpus=False, live=True)

    assert report["surface_status"]["patentscope_live"] == "not_configured"
    assert report["hits"]["live"] == []
    mock_search.assert_not_called()


def test_inpass_status_is_searched_when_application_number_present():
    passport = make_passport()
    passport.__dict__["application_number"] = "202314000123"
    with patch(
        "app.services.inpass_client.get_application_status",
        return_value={"status_stage": "UNDER_EXAMINATION", "application_number": "202314000123"},
    ) as mock_status:
        report = nss.run_novelty_search(passport, include_local_corpus=False, live=True)

    mock_status.assert_called_once_with("202314000123")
    assert report["surface_status"]["inpass_status"] == "searched"
    assert report["inpass_application_status"]["status_stage"] == "UNDER_EXAMINATION"
    assert "q=202314000123" in report["search_links"]["inpass"]


def test_inpass_status_is_unavailable_when_lookup_returns_none():
    passport = make_passport()
    passport.__dict__["application_number"] = "202314000123"
    with patch("app.services.inpass_client.get_application_status", return_value=None):
        report = nss.run_novelty_search(passport, include_local_corpus=False, live=True)

    assert report["surface_status"]["inpass_status"] == "unavailable"
    assert report["inpass_application_status"] is None


def test_inpass_lookup_failure_degrades_to_unavailable():
    passport = make_passport()
    passport.__dict__["application_number"] = "202314000123"
    with patch(
        "app.services.inpass_client.get_application_status",
        side_effect=RuntimeError("gateway down"),
    ):
        report = nss.run_novelty_search(passport, include_local_corpus=False, live=True)

    assert report["surface_status"]["inpass_status"] == "unavailable"
    assert report["inpass_application_status"] is None


def test_inpass_lookup_is_skipped_without_application_number():
    with patch("app.services.inpass_client.get_application_status") as mock_status:
        report = nss.run_novelty_search(make_passport(), include_local_corpus=False, live=True)

    mock_status.assert_not_called()
    assert report["surface_status"]["inpass_status"] == "not_configured"
    assert report["inpass_application_status"] is None


def test_duplicate_ingredient_names_and_canonical_ids_are_deduplicated():
    passport = make_passport(
        ingredients=[
            IngredientEntry(
                raw_name="Ashwagandha",
                botanical_name="Withania somnifera",
                canonical_id="ING-ASHWAGANDHA",
            ),
            IngredientEntry(
                raw_name="Ashwagandha",
                botanical_name="Withania somnifera",
                canonical_id="ING-ASHWAGANDHA",
            ),
            IngredientEntry(raw_name="Brahmi", botanical_name="", canonical_id=None),
        ]
    )
    report = nss.run_novelty_search(passport, include_local_corpus=False, live=False)

    assert report["query"]["ingredients"] == ["Ashwagandha", "Withania somnifera", "Brahmi"]
    assert report["query"]["canonical_ingredient_ids"] == ["ING-ASHWAGANDHA"]


@pytest.mark.xfail(
    reason="run_novelty_search reads passport.product_name, a field InnovationPassport does not define, so an ingredient-free passport crashes (novelty_search_service.py:200)",
    strict=False,
)
def test_passport_without_ingredients_still_produces_a_report():
    report = nss.run_novelty_search(
        make_passport(ingredients=[]), include_local_corpus=False, live=False
    )
    assert report["exposure_tier"] == "NO_MATCHES_FOUND"


@pytest.mark.xfail(
    reason="a corrupt permitted-TK corpus is swallowed (novelty_search_service.py:41) yet the report still claims permitted_tk_corpus was searched (novelty_search_service.py:144)",
    strict=False,
)
def test_corrupt_tk_corpus_is_not_reported_as_searched(tmp_path, monkeypatch):
    corrupt = tmp_path / "permitted_tk_prior_art.json"
    corrupt.write_text("{not-valid-json", encoding="utf-8")
    monkeypatch.setattr(nss, "_TK_PATH", str(corrupt))

    report = nss.run_novelty_search(make_passport(), include_local_corpus=False, live=False)

    assert report["hits"]["permitted_tk"] == []
    assert report["surface_status"]["permitted_tk_corpus"] != "searched"


@pytest.mark.xfail(
    reason="local retriever exceptions are swallowed (novelty_search_service.py:113) yet the report still claims local_patent_corpus was searched (novelty_search_service.py:145)",
    strict=False,
)
def test_local_retriever_failure_is_not_reported_as_searched():
    with patch(
        "app.rag.retrieval_pipeline.HybridRetriever.retrieve",
        side_effect=RuntimeError("index unavailable"),
    ):
        report = nss.run_novelty_search(make_passport(), include_local_corpus=True, live=False)

    assert report["hits"]["local_corpus"] == []
    assert report["surface_status"]["local_patent_corpus"] != "searched"


@pytest.mark.xfail(
    reason="live=False skips both guarded surfaces but labels them not_configured even when a gateway URL is configured (novelty_search_service.py:158,162)",
    strict=False,
)
def test_skipped_live_surfaces_are_not_labelled_unconfigured(monkeypatch):
    monkeypatch.setattr(patentscope_client, "GATEWAY_URL", "https://gateway.test/search")
    passport = make_passport()
    passport.__dict__["application_number"] = "202314000123"

    report = nss.run_novelty_search(passport, include_local_corpus=False, live=False)

    assert report["patentscope_availability"]["gateway_configured"] is True
    assert report["surface_status"]["patentscope_live"] == "not_searched"
    assert report["surface_status"]["inpass_status"] == "not_searched"
