"""Pytest configuration and shared fixtures for all tests.

Per TDD principle: Provides Azure client mocking and test fixtures to enable
testing without actual Azure credentials or live API calls.
"""

from collections.abc import Generator
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_azure_credential() -> Mock:
    """Mock Azure DefaultAzureCredential for testing without real auth.

    Returns:
        Mock credential object that can be used with Azure SDK clients
    """
    mock_cred = Mock()
    mock_cred.get_token = Mock(return_value=Mock(token="fake-token-12345"))
    return mock_cred


@pytest.fixture
def mock_security_center_client() -> Mock:
    """Mock Azure SecurityCenter client for testing.

    Returns:
        Mock SecurityCenter client with mocked methods for assessments,
        exemptions, and assignments
    """
    mock_client = MagicMock()

    # Mock assessments (recommendations)
    mock_client.assessments = MagicMock()
    mock_client.assessments.list = Mock(return_value=[])
    mock_client.assessments.get = Mock()

    # Mock assessment metadata (for exemptions)
    mock_client.assessment_metadata = MagicMock()
    mock_client.assessment_metadata.create_in_subscription = Mock()

    # Mock Active User suggestions and assignments
    mock_client.active_user_suggestions = MagicMock()
    mock_client.active_user_suggestions.list = Mock(return_value=[])

    mock_client.active_user_assignments = MagicMock()
    mock_client.active_user_assignments.create_or_update = Mock()
    mock_client.active_user_assignments.list = Mock(return_value=[])

    return mock_client


@pytest.fixture
def mock_azure_defender_client(
    mock_security_center_client: Mock,
) -> Generator[Mock]:
    """Mock AzureDefenderClient for testing endpoints.

    Yields:
        Mock AzureDefenderClient with mocked methods
    """
    from unittest.mock import patch

    mock_client = Mock()
    mock_client.subscription_id = "test-subscription-id"
    mock_client.client = mock_security_center_client
    mock_client.list_recommendations = Mock(return_value=[])
    mock_client.get_recommendation = Mock()
    mock_client.create_exemption = Mock()

    with patch(
        "src.services.azure_defender.get_azure_defender_client",
        return_value=mock_client,
    ):
        yield mock_client


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient for integration tests.

    Returns:
        TestClient instance for making HTTP requests to API
    """
    from src.main import app

    return TestClient(app)


@pytest.fixture
def sample_recommendation() -> dict:
    """Sample recommendation data for testing.

    Returns:
        Dictionary representing a recommendation from Azure Defender
    """
    return {
        "id": "/subscriptions/test-sub/providers/Microsoft.Security/assessments/rec-123",
        "name": "rec-123",
        "type": "Microsoft.Security/assessments",
        "properties": {
            "resourceDetails": {
                "id": (
                    "/subscriptions/test-sub/resourceGroups/rg1/providers/"
                    "Microsoft.Compute/virtualMachines/vm1"
                ),
                "source": "Azure",
            },
            "displayName": "Virtual machines should encrypt temp disks",
            "status": {
                "code": "Unhealthy",
                "cause": "OffByPolicy",
                "description": "This VM does not have encryption enabled",
            },
            "additionalData": {
                "severity": "High",
                "remediation_description": "Enable disk encryption",
            },
        },
    }


@pytest.fixture
def sample_exemption_request() -> dict:
    """Sample exemption request data for testing.

    Returns:
        Dictionary representing an exemption creation request
    """
    return {
        "recommendation_id": "rec-123",
        "justification": "This VM is scheduled for decommissioning next month",
        "expiration_date": "2025-12-31",
    }
