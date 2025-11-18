"""Global error handler middleware for LLM-friendly error responses.

Per constitution: All errors must return structured ErrorResponse with
consistent error codes and human-readable messages.
"""

import logging

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.models.error import ErrorResponse
from src.utils.validators import ResponseTooLargeError

logger = logging.getLogger(__name__)


async def handle_exception(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all API errors.

    Converts exceptions to LLM-friendly ErrorResponse format with
    appropriate HTTP status codes.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSONResponse with ErrorResponse payload and appropriate status code
    """
    # Azure authentication errors
    if isinstance(exc, ClientAuthenticationError):
        error = ErrorResponse(
            error_code="AUTHENTICATION_FAILED",
            message="Azure authentication failed. Check credentials.",
            details={"error": str(exc)},
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error.model_dump(),
        )

    # Azure resource not found
    if isinstance(exc, ResourceNotFoundError):
        error = ErrorResponse(
            error_code="RESOURCE_NOT_FOUND",
            message="The requested Azure resource was not found.",
            details={"error": str(exc)},
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error.model_dump(),
        )

    # Azure HTTP errors (rate limits, permissions, etc.)
    if isinstance(exc, HttpResponseError):
        # Extract Azure error code if available
        error_code = getattr(exc, "error_code", "AZURE_API_ERROR")
        # Get status code, default to 500 if not available or None
        status_code: int = (
            exc.status_code if hasattr(exc, "status_code") and exc.status_code is not None else 500
        )

        # Handle rate limiting
        if status_code == 429:
            retry_after = None
            if exc.response and hasattr(exc.response, "headers"):
                retry_after = exc.response.headers.get("Retry-After")

            error = ErrorResponse(
                error_code="RATE_LIMIT_EXCEEDED",
                message="Azure API rate limit exceeded. Retry with exponential backoff.",
                details={"retry_after": retry_after} if retry_after else None,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error.model_dump(),
            )

        # Handle permission errors
        if status_code == 403:
            error = ErrorResponse(
                error_code="PERMISSION_DENIED",
                message="Insufficient permissions to perform this operation.",
                details={"error": str(exc)},
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=error.model_dump(),
            )

        # Generic Azure error
        error = ErrorResponse(
            error_code=error_code,
            message=f"Azure API error: {exc.message}",
            details={"status_code": status_code},
        )
        return JSONResponse(
            status_code=status_code,
            content=error.model_dump(),
        )

    # Response too large error
    if isinstance(exc, ResponseTooLargeError):
        error = ErrorResponse(
            error_code="RESPONSE_TOO_LARGE",
            message=str(exc),
            details={
                "actual_size_bytes": exc.actual_size,
                "max_size_bytes": exc.max_size,
                "actual_size_kb": round(exc.actual_size / 1024, 2),
                "max_size_kb": exc.max_size / 1024,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=error.model_dump(),
        )

    # Validation errors (from Pydantic)
    if isinstance(exc, ValueError):
        error = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message=str(exc),
            details=None,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error.model_dump(),
        )

    # Unexpected errors
    logger.exception("Unexpected error occurred", exc_info=exc)
    error = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again.",
        details={"error_type": type(exc).__name__} if logger.level <= logging.DEBUG else None,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.model_dump(),
    )
