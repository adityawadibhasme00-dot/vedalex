"""Tests for the IP India InPASS application-status client (guarded + mocked)."""

import os
from unittest.mock import patch

from app.services import inpass_client as ipc


def test_parse_status_stage_classification():
    assert ipc.parse_status_text("Granted on 14-Jan-2024")["status_stage"] == "GRANTED"
    assert ipc.parse_status_text("First Examination Report issued")["status_stage"] == "FIRST_EXAM_REPORT"
    assert ipc.parse_status_text("Application abandoned")["status_stage"] == "ABANDONED"
    assert ipc.parse_status_text("")["status_stage"] == "UNKNOWN"


def test_status_is_live_only_when_configured():
    orig = os.environ.get("IPSAKTI_INPASS_WRAPPER_URL")
    os.environ.pop("IPSAKTI_INPASS_WRAPPER_URL", None)
    try:
        assert ipc.status_is_live() is False
        assert ipc.get_application_status("202314000123") is None
    finally:
        if orig is not None:
            os.environ["IPSAKTI_INPASS_WRAPPER_URL"] = orig


@patch("app.services.inpass_client.WRAPPER_URL", "https://parse.bot/marketplace/x/get_application_status")
@patch("app.services.inpass_client.status_is_live", return_value=True)
@patch("requests.post")
def test_get_application_status_parses_payload(mock_post, *_):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "application_number": "202314000123",
        "status": "Under Examination",
        "filing_date": "2023-04-12",
        "applicant": "Example Ayurveda Pvt Ltd",
        "first_exam_report": "2024-06-01",
    }
    result = ipc.get_application_status("202314000123")
    assert result is not None
    assert result["status_stage"] == "UNDER_EXAMINATION"
    assert result["application_number"] == "202314000123"
    assert result["examination"]["first_exam_report"] == "2024-06-01"
    assert result["source"] == "inpass-status"


@patch("app.services.inpass_client.WRAPPER_URL", "https://parse.bot/marketplace/x/get_application_status")
@patch("app.services.inpass_client.status_is_live", return_value=True)
@patch("requests.post", side_effect=Exception("network down"))
def test_get_application_status_degrades_silently(mock_post, *_):
    assert ipc.get_application_status("202314000123") is None


def test_format_status_brief():
    brief = ipc.format_status_brief({
        "application_number": "IN-202314000123",
        "status_stage": "GRANTED",
    })
    assert "IN-202314000123" in brief
    assert "GRANTED" in brief
    assert ipc.format_status_brief(None).startswith("InPASS status unavailable")