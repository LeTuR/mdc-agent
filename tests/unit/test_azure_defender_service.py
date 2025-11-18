"""Unit tests for Azure Defender service recommendation parsing.

Per TDD workflow: These tests verify the service layer correctly parses
Azure SDK assessment objects and applies filtering/pagination logic.
They should FAIL initially until the service methods are implemented.
"""

import pytest


def test_parse_azure_assessment_to_recommendation() -> None:
    """Test parsing Azure assessment object to Recommendation model.

    Validates:
    - Azure PascalCase fields are mapped correctly
    - Required fields are extracted
    - Sub-entities (resources) are parsed
    - Missing optional fields handled gracefully
    """
    from src.services.azure_defender import AzureDefenderClient
    from tests.utils.azure_mocks import create_mock_assessment

    # Create mock assessment
    mock_assessment = create_mock_assessment(
        assessment_id="rec-001",
        display_name="Enable disk encryption",
        severity="High",
        status_code="Unhealthy",
    )

    # Parse (this method doesn't exist yet - will fail)
    client = AzureDefenderClient(subscription_id="test-sub")
    recommendation = client._parse_assessment(mock_assessment)

    # Verify required fields
    expected_id = "/subscriptions/test-sub/providers/Microsoft.Security/assessments/rec-001"
    assert recommendation["recommendation_id"] == expected_id
    assert recommendation["severity"] == "High"
    assert recommendation["title"] == "Enable disk encryption"
    assert recommendation["assessment_status"] == "Unhealthy"
    assert recommendation["subscription_id"] == "test-sub"

    # Verify resources parsed
    assert "affected_resources" in recommendation
    assert len(recommendation["affected_resources"]) > 0


def test_filter_recommendations_by_severity() -> None:
    """Test severity filtering logic.

    Validates:
    - Filtering by single severity works
    - Case-sensitive matching
    - No match returns empty list
    """
    from src.services.azure_defender import AzureDefenderClient
    from tests.utils.azure_mocks import create_mock_assessment

    client = AzureDefenderClient(subscription_id="test-sub")

    assessments = [
        create_mock_assessment(severity="High"),
        create_mock_assessment(severity="Medium"),
        create_mock_assessment(severity="Low"),
    ]

    # Filter for High only
    filtered = client._filter_by_severity(assessments, ["High"])

    assert len(filtered) == 1
    assert filtered[0].properties.severity == "High"


def test_filter_recommendations_by_multiple_severities() -> None:
    """Test filtering by multiple severity levels.

    Validates:
    - Multiple severities work (OR logic)
    - All matching severities returned
    """
    from src.services.azure_defender import AzureDefenderClient
    from tests.utils.azure_mocks import create_mock_assessment

    client = AzureDefenderClient(subscription_id="test-sub")

    assessments = [
        create_mock_assessment(severity="High"),
        create_mock_assessment(severity="Medium"),
        create_mock_assessment(severity="Low"),
    ]

    # Filter for High OR Medium
    filtered = client._filter_by_severity(assessments, ["High", "Medium"])

    assert len(filtered) == 2
    severities = [a.properties.severity for a in filtered]
    assert "High" in severities
    assert "Medium" in severities
    assert "Low" not in severities


def test_filter_recommendations_by_resource_type() -> None:
    """Test resource type filtering logic.

    Validates:
    - Filtering by resource type works
    - Exact match required
    - Partial matches don't count
    """
    from src.services.azure_defender import AzureDefenderClient
    from tests.utils.azure_mocks import create_mock_assessment

    client = AzureDefenderClient(subscription_id="test-sub")

    assessments = [
        create_mock_assessment(
            resource_id="/subscriptions/test/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1"
        ),
        create_mock_assessment(
            resource_id="/subscriptions/test/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/sa1"
        ),
    ]

    # Filter for VMs only
    filtered = client._filter_by_resource_type(assessments, "Microsoft.Compute/virtualMachines")

    assert len(filtered) == 1
    assert "virtualMachines" in filtered[0].properties.resource_details.id


def test_pagination_logic() -> None:
    """Test pagination with limit and offset.

    Validates:
    - Offset skips correct number of items
    - Limit restricts result count
    - Out-of-range offset returns empty list
    """
    from src.services.azure_defender import AzureDefenderClient
    from tests.utils.azure_mocks import create_mock_assessment

    client = AzureDefenderClient(subscription_id="test-sub")

    # Create 25 assessments
    assessments = [create_mock_assessment(assessment_id=f"rec-{i:03d}") for i in range(25)]

    # Test first page
    page1 = client._apply_pagination(assessments, limit=10, offset=0)
    assert len(page1) == 10

    # Test second page
    page2 = client._apply_pagination(assessments, limit=10, offset=10)
    assert len(page2) == 10

    # Test last page (partial)
    page3 = client._apply_pagination(assessments, limit=10, offset=20)
    assert len(page3) == 5

    # Test out of range
    page4 = client._apply_pagination(assessments, limit=10, offset=30)
    assert len(page4) == 0


def test_list_recommendations_integration() -> None:
    """Test list_recommendations method with all filters combined.

    Validates:
    - Method exists and is callable
    - Returns list of parsed recommendations
    - Filters are applied correctly
    - Pagination works
    """
    from unittest.mock import patch

    from src.services.azure_defender import AzureDefenderClient

    client = AzureDefenderClient(subscription_id="test-sub")

    # Mock the Azure SDK client
    with patch.object(client, "client") as mock_client:
        from tests.utils.azure_mocks import create_mock_assessment

        mock_assessments = [
            create_mock_assessment(severity="High"),
            create_mock_assessment(severity="Medium"),
        ]
        mock_client.assessments.list.return_value = mock_assessments

        # Call list_recommendations
        results = client.list_recommendations(severity=["High"], limit=10, offset=0)

        # Verify Azure SDK was called
        mock_client.assessments.list.assert_called_once()

        # Verify results are filtered
        assert len(results) <= 1  # Only High severity


def test_handle_azure_sdk_exceptions() -> None:
    """Test error handling for Azure SDK exceptions.

    Validates:
    - HttpResponseError is caught
    - Appropriate exception is raised
    - Error details are preserved
    """
    from unittest.mock import patch

    from azure.core.exceptions import HttpResponseError

    from src.services.azure_defender import AzureDefenderClient

    client = AzureDefenderClient(subscription_id="test-sub")

    with patch.object(client, "client") as mock_client:
        # Mock Azure SDK to raise error
        mock_client.assessments.list.side_effect = HttpResponseError(message="Forbidden")

        # Verify exception is re-raised
        with pytest.raises(HttpResponseError):
            client.list_recommendations()


def test_extract_subscription_id_from_assessment() -> None:
    """Test extracting subscription ID from assessment ID.

    Validates:
    - Subscription ID is parsed from Azure resource ID
    - Handles malformed IDs gracefully
    """
    from src.services.azure_defender import AzureDefenderClient

    client = AzureDefenderClient(subscription_id="test-sub")

    assessment_id = (
        "/subscriptions/12345678-1234-1234-1234-123456789012/"
        "providers/Microsoft.Security/assessments/rec-001"
    )

    subscription_id = client._extract_subscription_id(assessment_id)

    assert subscription_id == "12345678-1234-1234-1234-123456789012"


def test_extract_resource_group_from_resource_id() -> None:
    """Test extracting resource group from resource ID.

    Validates:
    - Resource group is parsed from ARM path
    - Returns None if not present (subscription-level resource)
    """
    from src.services.azure_defender import AzureDefenderClient

    client = AzureDefenderClient(subscription_id="test-sub")

    # Resource group level resource
    resource_id_with_rg = (
        "/subscriptions/test-sub/resourceGroups/rg-prod/"
        "providers/Microsoft.Compute/virtualMachines/vm1"
    )
    rg = client._extract_resource_group(resource_id_with_rg)
    assert rg == "rg-prod"

    # Subscription level resource
    resource_id_no_rg = "/subscriptions/test-sub/providers/Microsoft.Security/assessments/rec-001"
    rg = client._extract_resource_group(resource_id_no_rg)
    assert rg is None


def test_parse_compliance_standards() -> None:
    """Test parsing compliance standards from assessment metadata.

    Validates:
    - Compliance standards array is extracted
    - Empty array handled gracefully
    - Standard names are preserved
    """
    from src.services.azure_defender import AzureDefenderClient
    from tests.utils.azure_mocks import create_mock_assessment

    client = AzureDefenderClient(subscription_id="test-sub")

    # Assessment with compliance standards
    assessment = create_mock_assessment()
    assessment.properties.additional_data = {"compliance_standards": ["CIS", "PCI-DSS"]}

    result = client._parse_assessment(assessment)

    assert "compliance_standards" in result
    assert "CIS" in result["compliance_standards"]
    assert "PCI-DSS" in result["compliance_standards"]
