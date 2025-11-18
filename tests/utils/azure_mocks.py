"""Utility functions for mocking Azure SDK responses in tests.

Provides factory functions to create realistic mock Azure objects for testing
without requiring actual Azure credentials or API calls.
"""

from unittest.mock import Mock

from azure.core.exceptions import HttpResponseError


def create_mock_assessment(
    assessment_id: str = "rec-001",
    display_name: str = "Test Recommendation",
    severity: str = "High",
    status_code: str = "Unhealthy",
    resource_id: str = (
        "/subscriptions/test-sub/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1"
    ),
) -> Mock:
    """Create a mock Azure assessment (recommendation) object.

    Args:
        assessment_id: Assessment ID
        display_name: Human-readable recommendation name
        severity: Severity level (High, Medium, Low)
        status_code: Status code (Healthy, Unhealthy, NotApplicable)
        resource_id: Full Azure resource ID

    Returns:
        Mock assessment object matching Azure SDK structure
    """
    mock_assessment = Mock()
    mock_assessment.id = (
        f"/subscriptions/test-sub/providers/Microsoft.Security/assessments/{assessment_id}"
    )
    mock_assessment.name = assessment_id
    mock_assessment.type = "Microsoft.Security/assessments"

    # Properties
    mock_properties = Mock()
    mock_properties.display_name = display_name
    mock_properties.severity = severity

    # Resource details
    mock_resource_details = Mock()
    mock_resource_details.id = resource_id
    mock_resource_details.source = "Azure"
    mock_resource_details.resource_type = resource_id.split("/providers/")[1].split("/")[0]
    mock_properties.resource_details = mock_resource_details

    # Status
    mock_status = Mock()
    mock_status.code = status_code
    mock_status.cause = "OffByPolicy" if status_code == "Unhealthy" else None
    mock_status.description = (
        "Resource does not meet security requirements"
        if status_code == "Unhealthy"
        else "Resource is secure"
    )
    mock_properties.status = mock_status

    # Additional data
    mock_properties.additional_data = {
        "severity": severity,
        "remediation_description": f"Apply security controls for {display_name}",
    }

    mock_assessment.properties = mock_properties

    return mock_assessment


def create_mock_active_user_suggestion(
    user_email: str = "user@example.com",
    confidence_score: float = 0.85,
    user_name: str = "Test User",
    department: str = "Engineering",
) -> Mock:
    """Create a mock Azure Active User suggestion object.

    Args:
        user_email: User email address
        confidence_score: Confidence score (0.0 - 1.0)
        user_name: User's display name
        department: User's department

    Returns:
        Mock Active User suggestion matching Azure SDK structure
    """
    mock_suggestion = Mock()
    mock_suggestion.user_email = user_email
    mock_suggestion.confidence_score = confidence_score

    # User details
    mock_user_details = Mock()
    mock_user_details.display_name = user_name
    mock_user_details.email = user_email
    mock_user_details.department = department
    mock_user_details.job_title = "Software Engineer"
    mock_user_details.manager_email = "manager@example.com"
    mock_suggestion.user_details = mock_user_details

    # Activities
    mock_activity = Mock()
    mock_activity.activity_type = "ResourceAccess"
    mock_activity.timestamp = "2025-11-15T10:30:00Z"
    mock_activity.resource_id = "/subscriptions/test-sub/resourceGroups/rg1"
    mock_suggestion.activities = [mock_activity]

    return mock_suggestion


def create_mock_assignment(
    assessment_id: str = "rec-001",
    assigned_user_email: str = "user@example.com",
    due_date: str = "2025-12-31",
    status: str = "active",
) -> Mock:
    """Create a mock Azure Active User assignment object.

    Args:
        assessment_id: Assessment ID
        assigned_user_email: Email of assigned user
        due_date: ISO 8601 due date
        status: Assignment status (active, completed, overdue)

    Returns:
        Mock assignment object matching Azure SDK structure
    """
    mock_assignment = Mock()
    mock_assignment.id = (
        f"/subscriptions/test-sub/providers/Microsoft.Security/assessments/"
        f"{assessment_id}/assignments/{assigned_user_email}"
    )
    mock_assignment.assessment_id = assessment_id
    mock_assignment.assigned_user_email = assigned_user_email
    mock_assignment.due_date = due_date
    mock_assignment.status = status
    mock_assignment.grace_period_enabled = True
    mock_assignment.notification_sent_at = "2025-11-18T09:00:00Z"
    mock_assignment.notification_status = "sent"
    mock_assignment.created_at = "2025-11-18T09:00:00Z"
    mock_assignment.updated_at = "2025-11-18T09:00:00Z"

    return mock_assignment


def create_mock_http_response_error(
    status_code: int = 403, message: str = "Forbidden"
) -> HttpResponseError:
    """Create a mock Azure HttpResponseError for testing error handling.

    Args:
        status_code: HTTP status code
        message: Error message

    Returns:
        HttpResponseError with specified status and message
    """
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.headers = {"Retry-After": "60"} if status_code == 429 else {}

    error = HttpResponseError(message=message)
    error.status_code = status_code  # type: ignore[attr-defined]
    error.response = mock_response  # type: ignore[attr-defined]

    return error
