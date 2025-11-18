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
    mock_azure_credential: Mock,
) -> Generator[Mock]:
    """Mock AzureDefenderClient for CONTRACT tests only.

    This fixture mocks the entire AzureDefenderClient and its methods.
    Use this for contract tests that only verify API schemas.

    For integration tests, use mock_azure_sdk_for_integration instead.

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

    # Patch Azure credential, subscription ID, and client factory
    # Patch where it's used (in recommendations.py), not where it's defined
    with (
        patch(
            "src.api.v1.recommendations.get_azure_defender_client",
            return_value=mock_client,
        ),
        patch("src.middleware.auth.get_azure_credential", return_value=mock_azure_credential),
        patch("os.getenv", return_value="test-subscription-id"),
    ):
        yield mock_client


@pytest.fixture
def mock_azure_sdk_for_integration(
    mock_security_center_client: Mock,
    mock_azure_credential: Mock,
) -> Generator[Mock]:
    """Mock Azure SDK for INTEGRATION tests.

    This fixture mocks at the Azure SDK level (SecurityCenter client),
    allowing the real AzureDefenderClient service layer to run with all
    its filtering, pagination, parsing, and retry logic.

    This is the proper way to do integration testing - mock the external
    dependency (Azure SDK) but let the application code run.

    Yields:
        Mock SecurityCenter client that will be used by real AzureDefenderClient
    """
    from unittest.mock import patch

    # Patch at the Azure SDK level
    with (
        patch(
            "src.services.azure_defender.SecurityCenter",
            return_value=mock_security_center_client,
        ),
        patch("src.middleware.auth.get_azure_credential", return_value=mock_azure_credential),
        patch("os.getenv", return_value="test-subscription-id"),
    ):
        yield mock_security_center_client


@pytest.fixture
def test_client(mock_azure_defender_client: Mock) -> TestClient:
    """FastAPI TestClient for CONTRACT tests.

    This fixture uses mock_azure_defender_client which mocks the entire
    service layer. Use this for contract tests that verify API schemas.

    For integration tests, use test_client_integration instead.

    Args:
        mock_azure_defender_client: Mock Azure Defender client fixture

    Returns:
        TestClient instance for making HTTP requests to API
    """
    from src.main import app

    return TestClient(app)


@pytest.fixture
def test_client_integration(mock_azure_sdk_for_integration: Mock) -> TestClient:
    """FastAPI TestClient for INTEGRATION tests.

    This fixture uses mock_azure_sdk_for_integration which mocks at the
    Azure SDK level, allowing the real service layer to run. This properly
    tests the integration between API layer and service layer.

    Args:
        mock_azure_sdk_for_integration: Mock Azure SDK client fixture

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
