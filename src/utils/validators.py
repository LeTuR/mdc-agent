"""Validation utilities for API responses and requests.

Per constitution: All API responses must be under 1MB to fit within
LLM context windows (FR-020).
"""

import json
from typing import Any

# 1MB limit for LLM context windows per FR-020
MAX_RESPONSE_SIZE_BYTES = 1024 * 1024  # 1MB


class ResponseTooLargeError(Exception):
    """Raised when response payload exceeds 1MB limit."""

    def __init__(self, actual_size: int, max_size: int = MAX_RESPONSE_SIZE_BYTES) -> None:
        """Initialize error with size information.

        Args:
            actual_size: Actual response size in bytes
            max_size: Maximum allowed size in bytes (default 1MB)
        """
        self.actual_size = actual_size
        self.max_size = max_size
        super().__init__(
            f"Response size {actual_size} bytes exceeds limit of {max_size} bytes "
            f"({actual_size / 1024:.2f}KB > {max_size / 1024}KB)"
        )


def validate_response_size(data: Any) -> None:
    """Validate that response payload is under 1MB limit.

    Per FR-020: All API responses must stay under 1MB to ensure they fit
    within LLM context windows. Raises ResponseTooLargeError if limit exceeded.

    Args:
        data: Response data to validate (will be JSON-serialized to check size)

    Raises:
        ResponseTooLargeError: If serialized response exceeds 1MB

    Examples:
        >>> validate_response_size({"key": "value"})  # Small response - OK
        >>> large_data = {"items": ["x" * 1000000]}
        >>> validate_response_size(large_data)  # Raises ResponseTooLargeError
        Traceback (most recent call last):
            ...
        ResponseTooLargeError: Response size ... exceeds limit ...
    """
    # Serialize to JSON to get actual response size
    serialized = json.dumps(data)
    size_bytes = len(serialized.encode("utf-8"))

    if size_bytes > MAX_RESPONSE_SIZE_BYTES:
        raise ResponseTooLargeError(actual_size=size_bytes)


def get_response_size(data: Any) -> int:
    """Calculate the serialized size of response data in bytes.

    Args:
        data: Response data to measure

    Returns:
        Size in bytes when JSON-serialized

    Examples:
        >>> get_response_size({"key": "value"})
        16
    """
    serialized = json.dumps(data)
    return len(serialized.encode("utf-8"))
