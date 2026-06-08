"""Unit tests for BCL client and models."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest
import requests
from requests.exceptions import HTTPError

from altissimo.bcl import (
    BCLClient,
    BCLOrderSample,
    BCLOrderStatus,
    BCLPatient,
    BCLProject,
    BCLSampleResult,
    BCLSampleStatus,
    BCLSettings,
    BCLTestSample,
    validate_metadata_helper,
)


def test_bcl_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BCLSettings.from_env() behavior."""
    # Test ValueError when service account key is missing
    monkeypatch.delenv("BCL_SERVICE_ACCOUNT_KEY", raising=False)
    with pytest.raises(ValueError, match="BCL_SERVICE_ACCOUNT_KEY is not set"):
        BCLSettings.from_env()

    # Test dev setting
    monkeypatch.setenv("BCL_SERVICE_ACCOUNT_KEY", "{}")
    monkeypatch.setenv("ENV", "dev")
    settings = BCLSettings.from_env()
    assert settings.env == "dev"
    assert settings.host == "gpo-staging.broadinstitute.org"
    assert settings.base_url == "https://gpo-staging.broadinstitute.org"

    # Test prod setting
    monkeypatch.setenv("ENV", "prod")
    settings = BCLSettings.from_env()
    assert settings.env == "prod"
    assert settings.host == "gpo.broadinstitute.org"
    assert settings.base_url == "https://gpo.broadinstitute.org"


def test_validate_metadata_helper() -> None:
    """Test validate_metadata_helper() metadata normalization."""
    # Dict input
    assert validate_metadata_helper({"key": "val"}) == {"key": "val"}

    # List of dicts input
    list_input = [
        {"key": "gender", "value": ["male"]},
        {"key": "age", "value": "30"},
        {"key": "invalid"},  # should be ignored
    ]
    assert validate_metadata_helper(list_input) == {
        "gender": "male",
        "age": "30",
    }

    # Invalid input types
    assert validate_metadata_helper("not-a-dict-or-list") == {}
    assert validate_metadata_helper(None) == {}


@patch("google.oauth2.service_account.IDTokenCredentials.from_service_account_info")
@patch("google.auth.transport.requests.Request")
def test_bcl_client_authentication(
    mock_request_cls: MagicMock,
    mock_from_info: MagicMock,
) -> None:
    """Test BCLClient OIDC authentication."""
    mock_credentials = MagicMock()
    mock_from_info.return_value = mock_credentials

    settings = BCLSettings(service_account_key='{"key": "val"}', env="dev", host="gpo-staging.broadinstitute.org")
    client = BCLClient(settings)

    # Trigger authenticate
    client._authenticate()

    mock_from_info.assert_called_once_with(
        info={"key": "val"},
        target_audience="https://gpo-staging.broadinstitute.org",
    )
    mock_credentials.refresh.assert_called_once()
    mock_credentials.apply.assert_called_once_with(client._headers)


@patch("google.oauth2.service_account.IDTokenCredentials.from_service_account_info")
@patch("google.auth.transport.requests.Request")
def test_bcl_client_api_calls(
    mock_request_cls: MagicMock,
    mock_from_info: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test BCLClient API retrieval methods."""
    mock_credentials = MagicMock()
    mock_from_info.return_value = mock_credentials

    settings = BCLSettings(service_account_key='{"key": "val"}', env="dev", host="gpo-staging.broadinstitute.org")

    # Mock requests.Session
    mock_session = MagicMock(spec=requests.Session)
    client = BCLClient(settings, session=mock_session)

    # 1. get_current_user
    mock_response = MagicMock()
    mock_response.json.return_value = {"email": "test@altissimo.io"}
    mock_session.get.return_value = mock_response

    user = client.get_current_user()
    assert user == {"email": "test@altissimo.io"}
    mock_session.get.assert_called_with(
        "https://gpo-staging.broadinstitute.org/auth",
        headers=client._headers,
        timeout=30,
    )

    # 2. get_bcl_api_order
    mock_response_order = MagicMock()
    mock_response_order.json.return_value = {"order_id": "ORD-1"}
    mock_session.get.return_value = mock_response_order

    order = client.get_bcl_api_order("ORD-1")
    assert order == {"order_id": "ORD-1"}
    mock_response_order.raise_for_status.assert_called_once()

    # 3. get_bcl_api_sample
    mock_response_sample = MagicMock()
    mock_response_sample.json.return_value = {"sample_id": "SMP-1"}
    mock_session.get.return_value = mock_response_sample

    sample = client.get_bcl_api_sample("SMP-1")
    assert sample == {"sample_id": "SMP-1"}

    # 4. list_bcl_api_orders with pagination
    mock_response_page1 = MagicMock()
    mock_response_page1.json.return_value = {
        "items": [{"order_id": "ORD-1"}],
        "paging": {"links": {"next_link": "/api/orders?page=2"}},
    }
    mock_response_page2 = MagicMock()
    mock_response_page2.json.return_value = {
        "items": [{"order_id": "ORD-2"}],
        "paging": {"links": {}},
    }

    mock_session.get.side_effect = [mock_response_page1, mock_response_page2]
    orders = client.list_bcl_api_orders()
    assert orders == [{"order_id": "ORD-1"}, {"order_id": "ORD-2"}]
    assert mock_session.get.call_count == 5  # 1 (user) + 1 (order) + 1 (sample) + 2 (pagination)

    # 5. list_bcl_api_samples with pagination
    mock_session.get.side_effect = None
    mock_response_sample_page = MagicMock()
    mock_response_sample_page.json.return_value = {
        "items": [{"sample_id": "SMP-1"}],
        "paging": {"links": {}},
    }
    mock_session.get.return_value = mock_response_sample_page
    samples = client.list_bcl_api_samples()
    assert samples == [{"sample_id": "SMP-1"}]


@patch("google.oauth2.service_account.IDTokenCredentials.from_service_account_info")
@patch("google.auth.transport.requests.Request")
def test_bcl_client_error_logging(
    mock_request_cls: MagicMock,
    mock_from_info: MagicMock,
) -> None:
    """Test BCLClient error logging when raise_for_status=False."""
    mock_credentials = MagicMock()
    mock_from_info.return_value = mock_credentials

    settings = BCLSettings(service_account_key='{"key": "val"}', env="dev", host="gpo-staging.broadinstitute.org")
    mock_session = MagicMock(spec=requests.Session)
    client = BCLClient(settings, session=mock_session)

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("Not Found", response=mock_response)
    mock_response.json.return_value = {"error": "Not Found"}
    mock_session.get.return_value = mock_response

    with patch("altissimo.bcl.client.logger") as mock_logger:
        result = client.get_bcl_api_order("missing")
        assert result == {"error": "Not Found"}
        mock_logger.error.assert_called_once()


def test_ordered_str_enum() -> None:
    """Test OrderedStrEnum comparisons."""
    assert BCLOrderStatus.SUBMITTED < BCLOrderStatus.PROCESSING
    assert BCLOrderStatus.PROCESSING < BCLOrderStatus.COMPLETED
    assert BCLOrderStatus.COMPLETED > BCLOrderStatus.SUBMITTED
    assert BCLOrderStatus.SUBMITTED <= BCLOrderStatus.PROCESSING
    assert BCLOrderStatus.COMPLETED >= BCLOrderStatus.COMPLETED

    # Test colors
    assert BCLOrderStatus.COMPLETED.color == "success"
    assert BCLOrderStatus.PROCESSING.color == "warning"
    assert BCLOrderStatus.SUBMITTED.color == "danger"
    assert BCLOrderStatus.SUBMITTED.color != "success"

    assert BCLSampleStatus.LAB_AND_DATA_DELIVERY_COMPLETED.color == "success"
    assert BCLSampleStatus.RECEIVED.color == "info"
    assert BCLSampleStatus.AWAITING_RECEIPT.color == "warning"
    assert BCLSampleStatus.CANCELED.color == "danger"
    assert BCLSampleStatus.CREATED.color == "secondary"


def test_pydantic_model_parsing() -> None:
    """Test parsing data into Pydantic models."""
    patient_data = {
        "patient_id": "PT-1",
        "sidr_patient_id": "SIDR-PT-1",
        "files": [],
        "last_modified": "2026-06-08T10:00:00Z",
        "metadata": [{"key": "foo", "value": ["bar"]}],
    }

    patient = BCLPatient.model_validate(patient_data)
    assert patient.patient_id == "PT-1"
    assert patient.metadata == {"foo": "bar"}

    project_data = {
        "project_key": "PRJ-1",
        "name": "Project 1",
        "type": "standard",
        "organization": "Broad",
        "metadata": [{"key": "org_id", "value": "123"}],
    }
    project = BCLProject.model_validate(project_data)
    assert project.metadata == {"org_id": "123"}

    order_sample_data = {
        "sample_id": "SMP-1",
        "client_barcode": "BC-1",
        "sidr_sample_id": "SIDR-SMP-1",
        "material_type": "DNA",
        "original_material_type": "Saliva",
        "shipping_information": {"carrier": "FedEx"},
        "patient": patient_data,
        "metadata": [],
    }
    order_sample = BCLOrderSample.model_validate(order_sample_data)
    assert order_sample.patient.patient_id == "PT-1"
    assert order_sample.metadata == {}

    result_data = {
        "latest": True,
        "links": {},
        "result_type": "PDF",
        "result_url_display_text": "View PDF",
        "result_url": "https://example.com/result.pdf",
        "result_value": "positive",
        "updated_on": "2026-06-08T10:00:00",  # naive datetime
        "version": 1,
    }
    result = BCLSampleResult.model_validate(result_data)
    assert result.updated_on.tzinfo == UTC

    test_sample_data = {
        "sample_id": "SMP-1",
        "sidr_sample_id": "SIDR-SMP-1",
        "test_sample_status": "RECEIVED",
        "status_history": [
            {
                "status_key": "RECEIVED",
                "status_name": "Received",
                "timestamp": "2026-06-08T09:00:00Z",
            }
        ],
        "client_barcode": "BC-1",
        "results": [],
        "last_modified": "2026-06-08T10:00:00Z",
        "result_date": "2026-06-08T11:00:00",  # naive datetime
    }
    test_sample = BCLTestSample.model_validate(test_sample_data)
    assert test_sample.test_sample_status == BCLSampleStatus.RECEIVED
    assert test_sample.result_date is not None
    assert test_sample.result_date.tzinfo == UTC
