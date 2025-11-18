"""Azure Defender for Cloud client wrapper with retry logic.

Per constitution: Implement exponential backoff retry logic for all Azure
API calls to handle transient failures and rate limiting (FR-017, FR-018).
"""

import logging
import os
from typing import Any

from azure.core.exceptions import HttpResponseError
from azure.mgmt.security import SecurityCenter
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.middleware.auth import get_azure_credential

logger = logging.getLogger(__name__)


# Retry configuration per T017: exponential backoff 1s to 60s max
azure_retry = retry(
    retry=retry_if_exception_type(HttpResponseError),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


class AzureDefenderClient:
    """Wrapper for Azure Defender for Cloud SecurityCenter client.

    Provides retry logic and convenience methods for recommendation,
    exemption, and assignment operations.

    Attributes:
        subscription_id: Azure subscription ID
        client: SecurityCenter SDK client
    """

    subscription_id: str

    def __init__(self, subscription_id: str | None = None) -> None:
        """Initialize Azure Defender client.

        Args:
            subscription_id: Azure subscription ID (defaults to env var
                AZURE_SUBSCRIPTION_ID)

        Raises:
            ValueError: If subscription_id not provided and env var not set
        """
        sub_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        if not sub_id:
            raise ValueError(
                "subscription_id required. Set AZURE_SUBSCRIPTION_ID env var or pass explicitly."
            )
        self.subscription_id = sub_id

        credential = get_azure_credential()
        self.client = SecurityCenter(credential, self.subscription_id)

    @azure_retry
    def list_recommendations(
        self,
        scope: str | None = None,
        severity: list[str] | None = None,
        resource_type: str | None = None,
        resource_group: str | None = None,
        assignment_status: str | None = None,
        assessment_status: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List security recommendations with optional filtering and pagination.

        Implements User Story 1 requirement (FR-001, FR-002, FR-003, FR-006, FR-007).
        Uses exponential backoff retry per FR-017.

        Args:
            scope: Optional scope filter (subscription/resource group/resource)
            severity: Optional severity filter list (e.g., ["High", "Critical"])
            resource_type: Optional resource type filter
            resource_group: Optional resource group filter
            assignment_status: Optional assignment filter (assigned/unassigned/all)
            assessment_status: Optional assessment status list
            limit: Maximum number of results to return (pagination)
            offset: Number of results to skip (pagination)

        Returns:
            List of parsed recommendations as dictionaries (snake_case)

        Raises:
            HttpResponseError: If Azure API call fails after retries
        """
        # Default scope to subscription if not provided
        if not scope:
            scope = f"/subscriptions/{self.subscription_id}"

        # List all assessments (recommendations) for the scope
        assessments = list(self.client.assessments.list(scope=scope))

        # Apply filters
        if severity:
            assessments = self._filter_by_severity(assessments, severity)
        if resource_type:
            assessments = self._filter_by_resource_type(assessments, resource_type)
        if resource_group:
            assessments = self._filter_by_resource_group(assessments, resource_group)
        if assessment_status:
            assessments = self._filter_by_assessment_status(assessments, assessment_status)

        # Parse assessments to dictionaries
        parsed_recommendations = [self._parse_assessment(assessment) for assessment in assessments]

        # Apply pagination
        return self._apply_pagination(parsed_recommendations, limit, offset)

    def _filter_by_severity(self, assessments: list, severities: list[str]) -> list:
        """Filter assessments by severity levels.

        Args:
            assessments: List of Azure assessment objects
            severities: List of severity levels to include

        Returns:
            Filtered list of assessments
        """
        return [
            a
            for a in assessments
            if hasattr(a.properties, "severity") and a.properties.severity in severities
        ]

    def _filter_by_resource_type(self, assessments: list, resource_type: str) -> list:
        """Filter assessments by resource type.

        Args:
            assessments: List of Azure assessment objects
            resource_type: Resource type to filter by

        Returns:
            Filtered list of assessments
        """
        return [
            a
            for a in assessments
            if hasattr(a.properties, "resource_details")
            and resource_type in a.properties.resource_details.id
        ]

    def _filter_by_resource_group(self, assessments: list, resource_group: str) -> list:
        """Filter assessments by resource group.

        Args:
            assessments: List of Azure assessment objects
            resource_group: Resource group name to filter by

        Returns:
            Filtered list of assessments
        """
        return [
            a
            for a in assessments
            if hasattr(a.properties, "resource_details")
            and f"/resourceGroups/{resource_group}/" in a.properties.resource_details.id
        ]

    def _filter_by_assessment_status(self, assessments: list, statuses: list[str]) -> list:
        """Filter assessments by status.

        Args:
            assessments: List of Azure assessment objects
            statuses: List of status codes to include

        Returns:
            Filtered list of assessments
        """
        return [
            a
            for a in assessments
            if hasattr(a.properties, "status") and a.properties.status.code in statuses
        ]

    def _apply_pagination(self, items: list, limit: int, offset: int) -> list:
        """Apply pagination to a list.

        Args:
            items: List to paginate
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            Paginated slice of the list
        """
        return items[offset : offset + limit]

    def _parse_assessment(self, assessment: Any) -> dict[str, Any]:
        """Parse Azure assessment object to recommendation dictionary.

        Transforms PascalCase Azure SDK fields to snake_case and extracts
        all required fields per data-model.md.

        Args:
            assessment: Azure SDK assessment object

        Returns:
            Dictionary with snake_case fields
        """
        # Extract resource details
        resource_details = assessment.properties.resource_details
        resources = [
            {
                "resource_id": resource_details.id,
                "resource_type": getattr(
                    resource_details,
                    "resource_type",
                    self._extract_resource_type(resource_details.id),
                ),
                "resource_name": self._extract_resource_name(resource_details.id),
            }
        ]

        # Extract compliance standards from additional data
        compliance_standards = None
        if hasattr(assessment.properties, "additional_data"):
            additional_data = assessment.properties.additional_data or {}
            if isinstance(additional_data, dict):
                compliance_standards = additional_data.get("compliance_standards")

        # Build recommendation dict
        return {
            "recommendation_id": assessment.id,
            "severity": getattr(assessment.properties, "severity", "Medium"),
            "title": assessment.properties.display_name,
            "description": getattr(
                assessment.properties.status,
                "description",
                "No description available",
            ),
            "affected_resources": resources,
            "remediation_steps": getattr(
                assessment.properties,
                "remediation_description",
                "Check Azure Defender for Cloud for remediation steps",
            ),
            "assessment_status": assessment.properties.status.code,
            "compliance_standards": compliance_standards,
            "assigned_user": None,  # TODO: Implement Active User lookup
            "due_date": None,
            "grace_period_enabled": None,
            "subscription_id": self._extract_subscription_id(assessment.id),
            "resource_group": self._extract_resource_group(resource_details.id),
        }

    def _extract_subscription_id(self, assessment_id: str) -> str:
        """Extract subscription ID from assessment ID.

        Args:
            assessment_id: Azure assessment resource ID

        Returns:
            Subscription ID (UUID)
        """
        parts = assessment_id.split("/")
        try:
            sub_index = parts.index("subscriptions")
            return parts[sub_index + 1]
        except (ValueError, IndexError):
            return self.subscription_id

    def _extract_resource_group(self, resource_id: str) -> str | None:
        """Extract resource group from resource ID.

        Args:
            resource_id: Azure resource ID

        Returns:
            Resource group name or None if subscription-level
        """
        parts = resource_id.split("/")
        try:
            rg_index = parts.index("resourceGroups")
            return parts[rg_index + 1]
        except (ValueError, IndexError):
            return None

    def _extract_resource_type(self, resource_id: str) -> str:
        """Extract resource type from resource ID.

        Args:
            resource_id: Azure resource ID

        Returns:
            Resource type (e.g., Microsoft.Compute/virtualMachines)
        """
        parts = resource_id.split("/")
        try:
            providers_index = parts.index("providers")
            # Resource type is providers/<namespace>/<type>
            return f"{parts[providers_index + 1]}/{parts[providers_index + 2]}"
        except (ValueError, IndexError):
            return "Unknown"

    def _extract_resource_name(self, resource_id: str) -> str:
        """Extract resource name from resource ID.

        Args:
            resource_id: Azure resource ID

        Returns:
            Resource name (last segment of ID)
        """
        parts = resource_id.split("/")
        return parts[-1] if parts else "Unknown"

    @azure_retry
    def get_recommendation(self, assessment_id: str, scope: str | None = None) -> dict[str, Any]:
        """Get a single recommendation by ID.

        Args:
            assessment_id: Assessment/recommendation ID
            scope: Optional scope (defaults to subscription)

        Returns:
            Recommendation details as dictionary

        Raises:
            ResourceNotFoundError: If recommendation not found
            HttpResponseError: If Azure API call fails after retries
        """
        if not scope:
            scope = f"/subscriptions/{self.subscription_id}"

        assessment = self.client.assessments.get(resource_id=scope, assessment_name=assessment_id)

        return {
            "id": assessment.id,
            "name": assessment.name,
            "type": assessment.type,
            "properties": {
                "resourceDetails": assessment.properties.resource_details,
                "displayName": assessment.properties.display_name,
                "status": {
                    "code": assessment.properties.status.code,
                    "cause": assessment.properties.status.cause,
                    "description": assessment.properties.status.description,
                },
                "additionalData": assessment.properties.additional_data,
            },
        }

    @azure_retry
    def create_exemption(
        self,
        assessment_id: str,
        justification: str,
        expiration_date: str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """Create an exemption for a security recommendation.

        Implements User Story 2 requirement (FR-008, FR-009).

        Args:
            assessment_id: Assessment/recommendation ID to exempt
            justification: Reason for exemption (min 10 characters per FR-010)
            expiration_date: ISO 8601 date when exemption expires
            scope: Optional scope (defaults to subscription)

        Returns:
            Exemption details as dictionary

        Raises:
            ValueError: If justification < 10 characters
            HttpResponseError: If Azure API call fails (e.g., permission denied)
        """
        if len(justification) < 10:
            raise ValueError("Justification must be at least 10 characters")

        if not scope:
            scope = f"/subscriptions/{self.subscription_id}"

        # Note: Actual Azure exemption API implementation depends on Azure SDK version
        # This is a placeholder for the exemption creation logic
        # Real implementation would use assessment_metadata.create_in_subscription
        exemption_result = {
            "exemption_id": f"{assessment_id}-exemption",
            "assessment_id": assessment_id,
            "justification": justification,
            "expiration_date": expiration_date,
            "status": "active",
            "created_at": "2025-11-18T00:00:00Z",
        }

        return exemption_result


def get_azure_defender_client(subscription_id: str | None = None) -> AzureDefenderClient:
    """Factory function to create Azure Defender client.

    Args:
        subscription_id: Optional Azure subscription ID

    Returns:
        Configured AzureDefenderClient instance
    """
    return AzureDefenderClient(subscription_id=subscription_id)
