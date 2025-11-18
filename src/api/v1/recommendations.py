"""Recommendations endpoints for User Story 1.

Implements GET /v1/recommendations with filtering, pagination, snake_case
transformation, and response size validation per FR-001 through FR-007.
"""

import logging
from typing import Annotated

from azure.core.exceptions import HttpResponseError
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from src.models.recommendation import RecommendationListResponse
from src.services.azure_defender import get_azure_defender_client
from src.utils.validators import validate_response_size

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Recommendations"])


@router.get(
    "/recommendations",
    response_model=RecommendationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List security recommendations",
    description=(
        "Retrieve security recommendations from Azure Defender for Cloud with "
        "optional filtering. Maps to FR-001, FR-002. Supports User Story 1 "
        "acceptance scenarios."
    ),
)
async def list_recommendations(
    subscription_id: Annotated[
        str | None,
        Query(
            description="Azure subscription ID to filter recommendations",
            pattern="^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        ),
    ] = None,
    severity: Annotated[
        list[str] | None,
        Query(
            description="Filter by severity level (can specify multiple)",
        ),
    ] = None,
    resource_type: Annotated[
        str | None,
        Query(
            description='Filter by Azure resource type (e.g., "Microsoft.Compute/virtualMachines")',
        ),
    ] = None,
    resource_group: Annotated[
        str | None,
        Query(
            description="Filter by resource group name",
        ),
    ] = None,
    assignment_status: Annotated[
        str | None,
        Query(
            description="Filter by assignment status",
            pattern="^(assigned|unassigned|overdue|all)$",
        ),
    ] = "all",
    assessment_status: Annotated[
        list[str] | None,
        Query(
            description="Filter by assessment health status",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            description="Maximum number of recommendations to return (pagination)",
            ge=1,
            le=1000,
        ),
    ] = 100,
    offset: Annotated[
        int,
        Query(
            description="Number of recommendations to skip (pagination)",
            ge=0,
        ),
    ] = 0,
) -> JSONResponse:
    """List security recommendations with filtering and pagination.

    Per TDD workflow: This endpoint implements User Story 1 requirements.
    Validates query parameters, calls Azure Defender service, applies
    transformations, and validates response size.

    Args:
        subscription_id: Optional subscription filter
        severity: Optional severity filter (can be multiple)
        resource_type: Optional resource type filter
        resource_group: Optional resource group filter
        assignment_status: Optional assignment status filter
        assessment_status: Optional assessment status filter
        limit: Pagination limit (default 100, max 1000)
        offset: Pagination offset (default 0)

    Returns:
        JSONResponse with recommendations list and pagination metadata

    Raises:
        ValidationError: If query parameters are invalid (400)
        PermissionDenied: If user lacks permissions (403)
        ResponseTooLargeError: If response exceeds 1MB (413)
    """
    # Validate severity enum values (if provided)
    if severity:
        valid_severities = {"Critical", "High", "Medium", "Low"}
        invalid_severities = set(severity) - valid_severities
        if invalid_severities:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid severity value",
                    "details": {
                        "parameter": "severity",
                        "provided_value": list(invalid_severities),
                        "valid_values": list(valid_severities),
                    },
                },
            )

    # Validate assessment_status enum values (if provided)
    if assessment_status:
        valid_statuses = {"Healthy", "Unhealthy", "NotApplicable"}
        invalid_statuses = set(assessment_status) - valid_statuses
        if invalid_statuses:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid assessment_status value",
                    "details": {
                        "parameter": "assessment_status",
                        "provided_value": list(invalid_statuses),
                        "valid_values": list(valid_statuses),
                    },
                },
            )

    try:
        # Get Azure Defender client
        client = get_azure_defender_client(subscription_id=subscription_id)

        # Call service layer to retrieve recommendations
        recommendations = client.list_recommendations(
            severity=severity,
            resource_type=resource_type,
            resource_group=resource_group,
            assignment_status=assignment_status,
            assessment_status=assessment_status,
            limit=limit,
            offset=offset,
        )

        # Note: list_recommendations already returns paginated results
        # We need to get total count before pagination for the response
        # For now, get all to count (will optimize later with count-only query)
        all_recommendations = client.list_recommendations(
            severity=severity,
            resource_type=resource_type,
            resource_group=resource_group,
            assignment_status=assignment_status,
            assessment_status=assessment_status,
            limit=999999,  # Get all for counting
            offset=0,
        )
        total_count = len(all_recommendations)

        # Build response
        response_data = {
            "recommendations": recommendations,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

        # Validate response size <1MB (FR-020)
        validate_response_size(response_data)

        return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)

    except HttpResponseError as e:
        # Handle Azure API errors
        logger.error("Azure API error: %s", e, exc_info=True)

        # Map Azure error status codes to API error responses
        error_code_map = {
            403: "PERMISSION_DENIED",
            429: "RATE_LIMIT_EXCEEDED",
            401: "AUTHENTICATION_FAILED",
            404: "RESOURCE_NOT_FOUND",
            500: "INTERNAL_SERVER_ERROR",
        }

        http_status = getattr(e, "status_code", 500)
        error_code = error_code_map.get(http_status, "AZURE_API_ERROR")

        return JSONResponse(
            status_code=http_status,
            content={
                "error_code": error_code,
                "message": str(e),
                "details": {
                    "status_code": http_status,
                },
            },
        )
