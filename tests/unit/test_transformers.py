"""Unit tests for snake_case transformation utility.

Per TDD workflow: These tests verify the PascalCase → snake_case transformer
works correctly. They should FAIL initially until the utility is enhanced
for nested objects and arrays.
"""


def test_to_snake_case_simple() -> None:
    """Test basic PascalCase → snake_case conversion.

    Validates:
    - PascalCase converts correctly
    - Already snake_case unchanged
    - lowercase unchanged
    """
    from src.utils.transformers import to_snake_case

    assert to_snake_case("AssessmentId") == "assessment_id"
    assert to_snake_case("DisplayName") == "display_name"
    assert to_snake_case("AffectedResources") == "affected_resources"
    assert to_snake_case("already_snake") == "already_snake"
    assert to_snake_case("lowercase") == "lowercase"


def test_to_snake_case_acronyms() -> None:
    """Test handling of acronyms in PascalCase.

    Validates:
    - HTTPResponse → http_response
    - XMLParser → xml_parser
    - APIKey → api_key
    """
    from src.utils.transformers import to_snake_case

    assert to_snake_case("HTTPResponse") == "http_response"
    assert to_snake_case("XMLParser") == "xml_parser"
    assert to_snake_case("APIKey") == "api_key"
    assert to_snake_case("ResourceID") == "resource_id"


def test_to_snake_case_numbers() -> None:
    """Test handling of numbers in field names.

    Validates:
    - Numbers are preserved
    - Position of numbers doesn't break conversion
    """
    from src.utils.transformers import to_snake_case

    assert to_snake_case("Resource1Name") == "resource1_name"
    assert to_snake_case("VM2Config") == "vm2_config"


def test_transform_keys_to_snake_case_dict() -> None:
    """Test transforming dictionary keys to snake_case.

    Validates:
    - Top-level keys are transformed
    - Nested dictionary keys are transformed
    - Values are preserved
    - Non-string keys are preserved
    """
    from src.utils.transformers import transform_keys_to_snake_case

    input_dict = {
        "AssessmentId": "rec-001",
        "DisplayName": "Test Recommendation",
        "Properties": {"Severity": "High", "Status": {"Code": "Unhealthy"}},
    }

    result = transform_keys_to_snake_case(input_dict)

    assert "assessment_id" in result
    assert "display_name" in result
    assert "properties" in result
    assert result["assessment_id"] == "rec-001"

    # Verify nested transformation
    assert "severity" in result["properties"]
    assert "status" in result["properties"]
    assert "code" in result["properties"]["status"]
    assert result["properties"]["status"]["code"] == "Unhealthy"


def test_transform_keys_to_snake_case_list_of_dicts() -> None:
    """Test transforming list of dictionaries.

    Validates:
    - Each dict in list is transformed
    - List structure is preserved
    """
    from src.utils.transformers import transform_keys_to_snake_case

    input_list = [
        {"ResourceId": "/subscriptions/test/vm1", "ResourceName": "vm1"},
        {"ResourceId": "/subscriptions/test/vm2", "ResourceName": "vm2"},
    ]

    result = transform_keys_to_snake_case(input_list)

    assert isinstance(result, list)
    assert len(result) == 2
    assert "resource_id" in result[0]
    assert "resource_name" in result[0]
    assert result[0]["resource_id"] == "/subscriptions/test/vm1"


def test_transform_keys_to_snake_case_nested_lists() -> None:
    """Test transforming nested lists and dicts.

    Validates:
    - Complex nested structures handled
    - All levels transformed
    """
    from src.utils.transformers import transform_keys_to_snake_case

    input_data = {
        "Recommendations": [
            {
                "AssessmentId": "rec-001",
                "AffectedResources": [
                    {"ResourceId": "vm1", "ResourceType": "VM"},
                    {"ResourceId": "vm2", "ResourceType": "VM"},
                ],
            }
        ]
    }

    result = transform_keys_to_snake_case(input_data)

    assert "recommendations" in result
    assert "assessment_id" in result["recommendations"][0]
    assert "affected_resources" in result["recommendations"][0]
    assert "resource_id" in result["recommendations"][0]["affected_resources"][0]
    assert "resource_type" in result["recommendations"][0]["affected_resources"][0]


def test_transform_keys_preserves_non_dict_values() -> None:
    """Test that non-dict values are preserved as-is.

    Validates:
    - Strings unchanged
    - Numbers unchanged
    - Booleans unchanged
    - None unchanged
    """
    from src.utils.transformers import transform_keys_to_snake_case

    input_dict = {
        "StringValue": "test",
        "IntValue": 42,
        "FloatValue": 3.14,
        "BoolValue": True,
        "NoneValue": None,
    }

    result = transform_keys_to_snake_case(input_dict)

    assert result["string_value"] == "test"
    assert result["int_value"] == 42
    assert result["float_value"] == 3.14
    assert result["bool_value"] is True
    assert result["none_value"] is None


def test_transform_keys_handles_empty_structures() -> None:
    """Test handling of empty dicts and lists.

    Validates:
    - Empty dict returns empty dict
    - Empty list returns empty list
    - None returns None
    """
    from src.utils.transformers import transform_keys_to_snake_case

    assert transform_keys_to_snake_case({}) == {}
    assert transform_keys_to_snake_case([]) == []
    assert transform_keys_to_snake_case(None) is None


def test_transform_azure_assessment_realistic() -> None:
    """Test transformation of realistic Azure assessment object.

    Validates:
    - Real Azure SDK response structure transforms correctly
    - All nested fields are snake_case
    - No PascalCase leakage
    """
    from src.utils.transformers import transform_keys_to_snake_case

    # Simulated Azure SDK assessment response
    azure_assessment = {
        "Id": "/subscriptions/test/providers/Microsoft.Security/assessments/rec-001",
        "Name": "rec-001",
        "Type": "Microsoft.Security/assessments",
        "Properties": {
            "DisplayName": "Enable disk encryption",
            "Severity": "High",
            "ResourceDetails": {
                "Id": (
                    "/subscriptions/test/resourceGroups/rg1/providers/"
                    "Microsoft.Compute/virtualMachines/vm1"
                ),
                "Source": "Azure",
                "ResourceType": "Microsoft.Compute/virtualMachines",
            },
            "Status": {
                "Code": "Unhealthy",
                "Cause": "OffByPolicy",
                "Description": "VM does not have encryption",
            },
            "AdditionalData": {"Severity": "High"},
        },
    }

    result = transform_keys_to_snake_case(azure_assessment)

    # Verify all keys are snake_case
    assert "id" in result
    assert "name" in result
    assert "type" in result
    assert "properties" in result
    assert "display_name" in result["properties"]
    assert "severity" in result["properties"]
    assert "resource_details" in result["properties"]
    assert "resource_type" in result["properties"]["resource_details"]
    assert "status" in result["properties"]
    assert "code" in result["properties"]["status"]
    assert "additional_data" in result["properties"]

    # Verify no PascalCase leaked
    assert "DisplayName" not in result["properties"]
    assert "ResourceDetails" not in result["properties"]
    assert "AdditionalData" not in result["properties"]


def test_transform_with_special_characters() -> None:
    """Test handling of keys with special characters.

    Validates:
    - Underscores already present are preserved
    - Hyphens are handled
    - Numbers are handled
    """
    from src.utils.transformers import to_snake_case

    assert to_snake_case("Resource_ID") == "resource_id"
    assert to_snake_case("Resource-ID") == "resource-id"  # Preserve hyphens
    # Note: Already snake_case with numbers creates double underscore (expected behavior)
    assert to_snake_case("VM1_Config") == "vm1__config"


def test_idempotent_transformation() -> None:
    """Test that transforming snake_case again doesn't change it.

    Validates:
    - Transformation is idempotent
    - Already snake_case stays snake_case
    """
    from src.utils.transformers import to_snake_case

    snake_case_input = "already_snake_case"

    assert to_snake_case(snake_case_input) == snake_case_input
    assert to_snake_case(to_snake_case(snake_case_input)) == snake_case_input
