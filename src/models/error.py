"""Error response models for LLM-optimized API responses.

Per constitution: Error responses must be LLM-friendly with structured
error codes, clear messages, and optional details for debugging.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model for all API errors.

    Attributes:
        error_code: Machine-readable error code (e.g., PERMISSION_DENIED,
            RESOURCE_NOT_FOUND)
        message: Human-readable error message explaining what went wrong
        details: Optional additional context (validation errors, stack traces
            in dev)
    """

    error_code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["PERMISSION_DENIED", "RESOURCE_NOT_FOUND", "INVALID_REQUEST"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["User does not have permission to create exemptions"],
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional context for debugging",
        examples=[{"field": "justification", "error": "must be at least 10 characters"}],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "PERMISSION_DENIED",
                    "message": "User does not have Security Administrator role",
                    "details": {"required_role": "Security Administrator"},
                },
                {
                    "error_code": "RESOURCE_NOT_FOUND",
                    "message": "Recommendation not found",
                    "details": {"recommendation_id": "abc-123"},
                },
            ]
        }
    }
