"""Utility functions for transforming Azure API responses to LLM-friendly format.

Per constitution: All API responses must use snake_case field naming
(PascalCase → snake_case) for LLM agent compatibility.
"""

import re
from typing import Any


def to_snake_case(text: str) -> str:
    """Convert PascalCase or camelCase string to snake_case.

    Args:
        text: Input string in PascalCase or camelCase format

    Returns:
        String converted to snake_case

    Examples:
        >>> to_snake_case("ResourceId")
        'resource_id'
        >>> to_snake_case("createdAt")
        'created_at'
        >>> to_snake_case("HTTPResponse")
        'http_response'
    """
    # Insert underscore before uppercase letters (except at start)
    text = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
    # Handle consecutive uppercase letters (e.g., HTTPResponse → HTTP_Response)
    text = re.sub("([a-z0-9])([A-Z])", r"\1_\2", text)
    return text.lower()


def transform_keys_to_snake_case(data: Any) -> Any:
    """Recursively transform all dictionary keys to snake_case.

    Handles nested dictionaries, lists, and preserves primitive types.
    Used to transform Azure SDK responses (PascalCase) to LLM-friendly
    snake_case format per FR-014.

    Args:
        data: Input data (dict, list, or primitive)

    Returns:
        Transformed data with all keys in snake_case

    Examples:
        >>> transform_keys_to_snake_case({"ResourceId": "123", "Status": "Active"})
        {'resource_id': '123', 'status': 'Active'}
        >>> transform_keys_to_snake_case([{"UserId": 1}, {"UserId": 2}])
        [{'user_id': 1}, {'user_id': 2}]
    """
    if isinstance(data, dict):
        return {
            to_snake_case(key): transform_keys_to_snake_case(value) for key, value in data.items()
        }
    elif isinstance(data, list):
        return [transform_keys_to_snake_case(item) for item in data]
    else:
        return data
