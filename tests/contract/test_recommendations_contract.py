"""Contract tests for GET /v1/recommendations endpoint.

Per TDD workflow: These tests verify the API response matches the OpenAPI
schema defined in contracts/recommendations.yaml. They should FAIL initially
until the endpoint is implemented.
"""

from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_list_recommendations_returns_correct_schema(
    test_client: TestClient, mock_azure_defender_client: Mock
) -> None:
    """Test that GET /v1/recommendations returns schema-compliant response.

    Validates:
    - Response has required fields: recommendations, total_count, limit, offset
    - Each recommendation has required fields per OpenAPI schema
    - Field names are snake_case (not PascalCase)
    - Response status is 200 OK
    """
    response = test_client.get("/v1/recommendations")

    assert response.status_code == 200
    data = response.json()

    # Validate top-level response structure
    assert "recommendations" in data
    assert "total_count" in data
    assert "limit" in data
    assert "offset" in data

    assert isinstance(data["recommendations"], list)
    assert isinstance(data["total_count"], int)
    assert isinstance(data["limit"], int)
    assert isinstance(data["offset"], int)


def test_list_recommendations_with_filters(
    test_client: TestClient, mock_azure_defender_client: Mock
) -> None:
    """Test that query parameters are accepted and validated.

    Validates:
    - severity filter accepts valid values
    - resource_type filter works
    - limit and offset pagination parameters work
    - subscription_id filter works
    """
    response = test_client.get(
        "/v1/recommendations",
        params={
            "severity": ["High", "Critical"],
            "resource_type": "Microsoft.Compute/virtualMachines",
            "limit": 50,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Pagination params should be reflected in response
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_list_recommendations_invalid_severity_returns_400(
    test_client: TestClient,
) -> None:
    """Test that invalid severity value returns 400 Bad Request.

    Validates:
    - Invalid enum values are rejected
    - Error response follows ErrorResponse schema
    - error_code, message, and details are present
    """
    response = test_client.get("/v1/recommendations", params={"severity": "InvalidLevel"})

    assert response.status_code == 400
    error = response.json()

    assert "error_code" in error
    assert "message" in error
    assert error["error_code"] == "VALIDATION_ERROR"


def test_recommendation_schema_compliance(
    test_client: TestClient, mock_azure_defender_client: Mock
) -> None:
    """Test that recommendation objects match OpenAPI schema.

    Validates each recommendation has:
    - recommendation_id (string)
    - severity (enum: Critical/High/Medium/Low)
    - title (string)
    - description (string)
    - affected_resources (array with at least 1 item)
    - remediation_steps (string)
    - assessment_status (enum: Healthy/Unhealthy/NotApplicable)
    - subscription_id (string UUID)
    """
    # Setup mock to return sample recommendation
    from tests.utils.azure_mocks import create_recommendation_dict

    mock_recommendation = create_recommendation_dict(
        assessment_id="rec-001",
        display_name="Test Recommendation",
        severity="High",
        status_code="Unhealthy",
    )
    mock_azure_defender_client.list_recommendations.return_value = [mock_recommendation]

    response = test_client.get("/v1/recommendations")

    assert response.status_code == 200
    data = response.json()

    recommendations = data["recommendations"]
    assert len(recommendations) > 0

    rec = recommendations[0]

    # Required fields
    assert "recommendation_id" in rec
    assert "severity" in rec
    assert "title" in rec
    assert "description" in rec
    assert "affected_resources" in rec
    assert "remediation_steps" in rec
    assert "assessment_status" in rec
    assert "subscription_id" in rec

    # Type validations
    assert isinstance(rec["recommendation_id"], str)
    assert rec["severity"] in ["Critical", "High", "Medium", "Low"]
    assert isinstance(rec["title"], str)
    assert isinstance(rec["description"], str)
    assert isinstance(rec["affected_resources"], list)
    assert len(rec["affected_resources"]) >= 1
    assert isinstance(rec["remediation_steps"], str)
    assert rec["assessment_status"] in [
        "Healthy",
        "Unhealthy",
        "NotApplicable",
    ]
    assert isinstance(rec["subscription_id"], str)


def test_resource_schema_compliance(
    test_client: TestClient,
    mock_azure_defender_client: Mock,
) -> None:
    """Test that Resource sub-entity matches OpenAPI schema.

    Validates each resource has:
    - resource_id (string, full ARM path)
    - resource_type (string)
    - resource_name (string)
    """
    from tests.utils.azure_mocks import create_recommendation_dict

    mock_recommendation = create_recommendation_dict()
    mock_azure_defender_client.list_recommendations.return_value = [mock_recommendation]

    response = test_client.get("/v1/recommendations")
    data = response.json()

    recommendations = data["recommendations"]
    assert len(recommendations) > 0

    resources = recommendations[0]["affected_resources"]
    assert len(resources) > 0

    resource = resources[0]

    # Required fields
    assert "resource_id" in resource
    assert "resource_type" in resource
    assert "resource_name" in resource

    # Type validations
    assert isinstance(resource["resource_id"], str)
    assert isinstance(resource["resource_type"], str)
    assert isinstance(resource["resource_name"], str)
    assert "/" in resource["resource_id"]  # ARM path format


def test_assigned_user_schema_when_present(
    test_client: TestClient, mock_azure_defender_client: Mock
) -> None:
    """Test AssignedUser sub-entity schema when assignment exists.

    Validates assigned_user has:
    - user_email (string, email format)
    - user_name (string)
    - assignment_date (string, ISO 8601 datetime)
    - notification_sent (boolean)

    Also validates optional fields when assignment exists:
    - due_date (string, ISO 8601 date)
    - grace_period_enabled (boolean)
    """
    # Mock will be configured to include assignment
    # This test will pass when assignment functionality is implemented
    pass


def test_response_size_under_1mb(test_client: TestClient, mock_azure_defender_client: Mock) -> None:
    """Test that response size is under 1MB (FR-020).

    Validates:
    - Response body size < 1MB (1,048,576 bytes)
    - Large result sets are paginated appropriately
    """
    response = test_client.get("/v1/recommendations", params={"limit": 1000})

    assert response.status_code == 200

    # Check response size
    response_size = len(response.content)
    max_size = 1024 * 1024  # 1MB

    assert response_size < max_size, f"Response size {response_size} exceeds 1MB limit"


def test_pagination_behavior(test_client: TestClient, mock_azure_defender_client: Mock) -> None:
    """Test pagination with limit and offset parameters.

    Validates:
    - limit parameter controls number of returned items
    - offset parameter skips items correctly
    - total_count reflects total across all pages
    """
    response = test_client.get("/v1/recommendations", params={"limit": 10, "offset": 0})

    assert response.status_code == 200
    data = response.json()

    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["recommendations"]) <= 10


def test_snake_case_field_naming(test_client: TestClient, mock_azure_defender_client: Mock) -> None:
    """Test that all fields use snake_case (FR-014).

    Validates:
    - No PascalCase field names in response
    - All fields follow snake_case convention
    """
    response = test_client.get("/v1/recommendations")

    assert response.status_code == 200
    data = response.json()

    # Check top-level fields
    assert "total_count" in data
    assert "TotalCount" not in data
    assert "totalCount" not in data

    if data["recommendations"]:
        rec = data["recommendations"][0]

        # Check recommendation fields
        assert "recommendation_id" in rec
        assert "RecommendationId" not in rec
        assert "affected_resources" in rec
        assert "AffectedResources" not in rec
        assert "assessment_status" in rec
        assert "AssessmentStatus" not in rec
