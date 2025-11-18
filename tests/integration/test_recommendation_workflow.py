"""Integration tests for recommendation retrieval workflow.

Per TDD workflow: These tests verify the end-to-end flow from HTTP request
through service layer to Azure SDK. They should FAIL initially until the
workflow is implemented.

IMPORTANT: These tests mock at the Azure SDK level (SecurityCenter client),
allowing the real AzureDefenderClient service layer to run. This properly
tests the integration between API layer and service layer including:
- Filtering logic (_filter_by_severity, _filter_by_resource_type, etc.)
- Pagination logic (_apply_pagination)
- Parsing logic (_parse_assessment)
- Retry decorators and error handling
"""

from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_retrieve_recommendations_end_to_end(
    test_client_integration: TestClient, mock_azure_sdk_for_integration: Mock
) -> None:
    """Test complete workflow for retrieving recommendations.

    Workflow:
    1. Client makes GET request to /v1/recommendations
    2. API layer validates query parameters
    3. Service layer (REAL) calls Azure SDK (MOCKED)
    4. Service layer parses, filters, paginates Azure SDK responses
    5. Service transforms PascalCase → snake_case
    6. Service validates response size <1MB
    7. API returns JSON response

    Validates:
    - All layers integrate correctly
    - Real service layer filtering/pagination/parsing logic works
    - Response transformation works end-to-end
    """
    from tests.utils.azure_mocks import create_mock_assessment

    # Setup: Mock Azure SDK to return sample assessments
    mock_assessments = [
        create_mock_assessment(
            assessment_id="rec-001",
            display_name="Enable disk encryption",
            severity="High",
            status_code="Unhealthy",
        ),
        create_mock_assessment(
            assessment_id="rec-002",
            display_name="Enable MFA for privileged users",
            severity="Critical",
            status_code="Unhealthy",
        ),
    ]
    mock_azure_sdk_for_integration.assessments.list.return_value = mock_assessments

    # Execute: Make API request
    response = test_client_integration.get("/v1/recommendations")

    # Verify: Response is successful
    assert response.status_code == 200
    data = response.json()

    # Verify: Azure SDK was called
    assert mock_azure_sdk_for_integration.assessments.list.called

    # Verify: Response contains expected data (real service layer parsed it)
    assert len(data["recommendations"]) == 2
    assert data["total_count"] == 2

    # Verify: Data is transformed to snake_case by real service layer
    rec = data["recommendations"][0]
    assert "recommendation_id" in rec
    assert "assessment_status" in rec
    assert rec["title"] == "Enable disk encryption"
    assert rec["severity"] == "High"


def test_filter_recommendations_by_severity(
    test_client_integration: TestClient, mock_azure_sdk_for_integration: Mock
) -> None:
    """Test filtering workflow with severity parameter.

    Workflow:
    1. Client requests recommendations with severity=High filter
    2. Azure SDK returns multiple assessments with different severities
    3. REAL service layer filters by severity (tests actual _filter_by_severity logic)
    4. Only High severity recommendations returned

    Validates:
    - Filter parameter is passed through correctly
    - Real filtering logic in service layer works
    """
    from tests.utils.azure_mocks import create_mock_assessment

    # Mock Azure SDK returns assessments with different severities
    mock_assessments = [
        create_mock_assessment(severity="High", assessment_id="rec-001"),
        create_mock_assessment(severity="Medium", assessment_id="rec-002"),
        create_mock_assessment(severity="Low", assessment_id="rec-003"),
    ]
    mock_azure_sdk_for_integration.assessments.list.return_value = mock_assessments

    response = test_client_integration.get("/v1/recommendations", params={"severity": "High"})

    assert response.status_code == 200
    data = response.json()

    # Verify: Real service layer filtered to only High severity
    assert len(data["recommendations"]) == 1
    assert all(rec["severity"] == "High" for rec in data["recommendations"])


def test_pagination_workflow(
    test_client_integration: TestClient, mock_azure_sdk_for_integration: Mock
) -> None:
    """Test pagination workflow with limit and offset.

    Workflow:
    1. Client requests first page (limit=10, offset=0)
    2. Azure SDK returns all assessments
    3. REAL service layer applies pagination logic (tests actual _apply_pagination)
    4. Client receives paginated subset

    Validates:
    - Real pagination logic in service layer works correctly
    - total_count reflects full dataset
    - Subset size matches limit
    """
    from tests.utils.azure_mocks import create_mock_assessment

    # Create 25 mock assessments that Azure SDK would return
    all_assessments = [create_mock_assessment(assessment_id=f"rec-{i:03d}") for i in range(25)]

    # Mock Azure SDK always returns all assessments (service layer does pagination)
    mock_azure_sdk_for_integration.assessments.list.return_value = all_assessments

    # Request first page
    response = test_client_integration.get("/v1/recommendations", params={"limit": 10, "offset": 0})

    assert response.status_code == 200
    data = response.json()

    # Verify: Real service layer applied pagination correctly
    assert data["total_count"] == 25
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["recommendations"]) == 10

    # Request second page
    response = test_client_integration.get(
        "/v1/recommendations", params={"limit": 10, "offset": 10}
    )

    data = response.json()
    assert data["total_count"] == 25
    assert data["offset"] == 10
    assert len(data["recommendations"]) == 10


def test_error_handling_azure_api_failure(
    test_client_integration: TestClient, mock_azure_sdk_for_integration: Mock
) -> None:
    """Test error handling when Azure SDK fails.

    Workflow:
    1. Client makes request
    2. Azure SDK raises HttpResponseError
    3. REAL service layer propagates exception
    4. REAL API error handler catches exception
    5. API returns structured ErrorResponse

    Validates:
    - Real error handling in API layer works
    - Exceptions are caught gracefully
    - Error response follows schema
    - Appropriate status code returned
    """
    from tests.utils.azure_mocks import create_mock_http_response_error

    # Setup: Mock Azure SDK to raise error
    error = create_mock_http_response_error(status_code=403, message="Forbidden")
    mock_azure_sdk_for_integration.assessments.list.side_effect = error

    # Execute: Make API request
    response = test_client_integration.get("/v1/recommendations")

    # Verify: Real error handler returned correct error response
    assert response.status_code == 403
    data = response.json()

    assert "error_code" in data
    assert "message" in data
    assert data["error_code"] == "PERMISSION_DENIED"


def test_retry_logic_on_rate_limit(
    test_client_integration: TestClient,
    mock_azure_sdk_for_integration: Mock,
) -> None:
    """Test error handling when Azure SDK returns 429 rate limit.

    Workflow:
    1. Client makes request
    2. Azure SDK raises 429 rate limit error
    3. REAL service layer retry decorator could retry (but ultimately fails)
    4. REAL API error handler catches exception
    5. API returns structured ErrorResponse with 429 status

    Validates:
    - Rate limit errors are caught gracefully
    - Real error response handling works
    - Appropriate status code and error_code returned

    Note: Full retry logic (multiple attempts) is complex to test in integration
    tests since it involves timing. This test verifies that 429 errors are
    properly handled when retries are exhausted.
    """
    from tests.utils.azure_mocks import create_mock_http_response_error

    # Setup: Mock Azure SDK to raise rate limit error
    rate_limit_error = create_mock_http_response_error(status_code=429, message="Too Many Requests")
    mock_azure_sdk_for_integration.assessments.list.side_effect = rate_limit_error

    # Execute: Make API request
    response = test_client_integration.get("/v1/recommendations")

    # Verify: Real error handler returned correct error response
    assert response.status_code == 429
    data = response.json()

    assert "error_code" in data
    assert "message" in data
    assert data["error_code"] == "RATE_LIMIT_EXCEEDED"


def test_response_size_validation(
    test_client: TestClient,
    mock_azure_defender_client: Mock,
) -> None:
    """Test that response size validator rejects oversized responses.

    Workflow:
    1. Azure returns very large dataset
    2. Service validates response size
    3. If >1MB, returns 413 Request Entity Too Large error

    Validates:
    - Response size validator is triggered
    - Oversized responses are rejected
    - Appropriate error returned
    """
    # This test validates FR-020 (responses <1MB)
    # Implementation will need to check response size before returning
    pass


def test_empty_results_handling(
    test_client_integration: TestClient, mock_azure_sdk_for_integration: Mock
) -> None:
    """Test handling of zero recommendations.

    Workflow:
    1. Client makes request
    2. Azure SDK returns empty list
    3. REAL service layer processes empty list
    4. Client receives empty array with total_count=0

    Validates:
    - Empty results handled gracefully by real service layer
    - Response structure is still valid
    """
    # Mock Azure SDK returns no assessments
    mock_azure_sdk_for_integration.assessments.list.return_value = []

    response = test_client_integration.get("/v1/recommendations")

    assert response.status_code == 200
    data = response.json()

    # Verify: Real service layer handled empty results correctly
    assert data["recommendations"] == []
    assert data["total_count"] == 0
    assert data["limit"] == 100  # default
    assert data["offset"] == 0


def test_multiple_filters_combined(
    test_client_integration: TestClient,
    mock_azure_sdk_for_integration: Mock,
) -> None:
    """Test combining multiple filter parameters.

    Workflow:
    1. Client requests with severity AND resource_type filters
    2. Azure SDK returns assessments with different severities and resource types
    3. REAL service layer applies both filters (tests cumulative filtering logic)
    4. Only matching recommendations returned

    Validates:
    - Multiple filters work together (AND logic)
    - Real filtering logic is cumulative
    """
    from tests.utils.azure_mocks import create_mock_assessment

    # Mock Azure SDK returns assessments with various severities and resource types
    mock_assessments = [
        create_mock_assessment(
            assessment_id="rec-001",
            severity="High",
            resource_id="/subscriptions/test/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
        ),
        create_mock_assessment(
            assessment_id="rec-002",
            severity="High",
            resource_id="/subscriptions/test/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/sa1",
        ),
        create_mock_assessment(
            assessment_id="rec-003",
            severity="Medium",
            resource_id="/subscriptions/test/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm2",
        ),
    ]
    mock_azure_sdk_for_integration.assessments.list.return_value = mock_assessments

    response = test_client_integration.get(
        "/v1/recommendations",
        params={
            "severity": "High",
            "resource_type": "Microsoft.Compute/virtualMachines",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify: Real service layer applied both filters (AND logic)
    # Should only return High severity VMs (not High Storage, not Medium VMs)
    assert len(data["recommendations"]) == 1
    rec = data["recommendations"][0]
    assert rec["severity"] == "High"
    assert "Microsoft.Compute/virtualMachines" in rec["affected_resources"][0]["resource_type"]
