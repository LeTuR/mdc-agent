"""Pydantic models for security recommendations.

Per data-model.md: Recommendation entity with Resource and AssignedUser sub-entities.
All models use snake_case field naming for LLM optimization.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class Resource(BaseModel):
    """Azure resource affected by a security recommendation.

    Sub-entity of Recommendation representing an individual affected resource.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    resource_id: str = Field(
        ...,
        description="Azure resource ID (full ARM path)",
        examples=[
            "/subscriptions/12345/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm-web-01"
        ],
    )
    resource_type: str = Field(
        ...,
        description="Azure resource type",
        examples=["Microsoft.Compute/virtualMachines"],
    )
    resource_name: str = Field(
        ..., description="Display name of the resource", examples=["vm-web-01"]
    )


class AssignedUser(BaseModel):
    """User assigned to remediate a recommendation via Active User API.

    Sub-entity of Recommendation when assignment exists.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    user_email: str = Field(
        ...,
        description="Email address of assigned user",
        examples=["alice@contoso.com"],
    )
    user_name: str = Field(
        ..., description="Display name of assigned user", examples=["Alice Smith"]
    )
    assignment_date: datetime = Field(
        ...,
        description="When the assignment was created (ISO 8601)",
        examples=["2025-11-15T10:30:00Z"],
    )
    notification_sent: bool = Field(..., description="Whether Azure sent email notification")


class Recommendation(BaseModel):
    """Security recommendation from Azure Defender for Cloud.

    Represents a security finding with affected resources, remediation steps,
    and optional assignment information.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    recommendation_id: str = Field(
        ...,
        description="Azure assessment ID (unique identifier)",
        examples=["/subscriptions/12345/providers/Microsoft.Security/assessments/abc-123"],
    )
    severity: str = Field(
        ...,
        description="Severity level of the security finding",
        pattern="^(Critical|High|Medium|Low)$",
        examples=["High"],
    )
    title: str = Field(
        ...,
        description="Short recommendation title",
        examples=["Enable disk encryption on virtual machines"],
    )
    description: str = Field(
        ...,
        description="Detailed explanation of the security issue",
        examples=["Virtual machines without disk encryption are vulnerable to data theft"],
    )
    affected_resources: list[Resource] = Field(
        ...,
        description="List of affected Azure resources",
        min_length=1,
    )
    remediation_steps: str = Field(
        ...,
        description="Instructions on how to fix the issue",
        examples=["Enable Azure Disk Encryption for VM disks in the Azure Portal"],
    )
    assessment_status: str = Field(
        ...,
        description="Current health status of the assessment",
        pattern="^(Healthy|Unhealthy|NotApplicable)$",
        examples=["Unhealthy"],
    )
    compliance_standards: list[str] | None = Field(
        default=None,
        description='Related compliance frameworks (e.g., "CIS", "PCI-DSS")',
        examples=[["CIS", "PCI-DSS"]],
    )
    assigned_user: AssignedUser | None = Field(
        default=None, description="Present if Active User assignment exists"
    )
    due_date: date | None = Field(
        default=None,
        description="Assignment due date (ISO 8601 format)",
        examples=["2025-12-15"],
    )
    grace_period_enabled: bool | None = Field(
        default=None,
        description="Whether grace period is active for this assignment",
    )
    subscription_id: str = Field(
        ...,
        description="Azure subscription containing the resource",
        pattern="^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        examples=["12345678-1234-1234-1234-123456789012"],
    )
    resource_group: str | None = Field(
        default=None,
        description="Resource group name (if applicable)",
        examples=["rg-prod"],
    )


class RecommendationListResponse(BaseModel):
    """Response model for GET /v1/recommendations endpoint.

    Includes pagination metadata and list of recommendations.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    recommendations: list[Recommendation] = Field(
        ..., description="List of recommendations matching filters"
    )
    total_count: int = Field(..., description="Total number of recommendations (across all pages)")
    limit: int = Field(..., description="Maximum items per page", ge=1, le=1000)
    offset: int = Field(..., description="Number of items skipped", ge=0)
