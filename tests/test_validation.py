import pytest

from devops_health_checker.schemas import (
    ToolParameter,
    ToolSchema,
)
from devops_health_checker.validation import (
    ToolValidationError,
    validate_tool_arguments,
)


def test_required_parameter_is_valid():
    schema = ToolSchema(
        name="github_repository",
        description="Check GitHub repository",
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description="Repository owner",
                required=True,
            )
        ],
    )

    result = validate_tool_arguments(
        schema,
        {
            "owner": "kubernetes",
        },
    )

    assert result == {
        "owner": "kubernetes",
    }


def test_missing_required_parameter():
    schema = ToolSchema(
        name="github_repository",
        description="Check GitHub repository",
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description="Repository owner",
                required=True,
            )
        ],
    )

    with pytest.raises(
        ToolValidationError,
        match="Missing required parameter",
    ):
        validate_tool_arguments(
            schema,
            {},
        )


def test_unknown_parameter():
    schema = ToolSchema(
        name="github_repository",
        description="Check GitHub repository",
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description="Repository owner",
                required=True,
            )
        ],
    )

    with pytest.raises(
        ToolValidationError,
        match="Unknown parameter",
    ):
        validate_tool_arguments(
            schema,
            {
                "owner": "kubernetes",
                "password": "secret",
            },
        )


def test_wrong_type():
    schema = ToolSchema(
        name="github_repository",
        description="Check GitHub repository",
        parameters=[
            ToolParameter(
                name="owner",
                type="string",
                description="Repository owner",
                required=True,
            )
        ],
    )

    with pytest.raises(
        ToolValidationError,
        match="must be of type string",
    ):
        validate_tool_arguments(
            schema,
            {
                "owner": 123,
            },
        )


def test_default_value_is_applied():
    schema = ToolSchema(
        name="kubernetes_health",
        description="Check Kubernetes health",
        parameters=[
            ToolParameter(
                name="namespace",
                type="string",
                description="Kubernetes namespace",
                required=False,
                default=None,
            )
        ],
    )

    result = validate_tool_arguments(
        schema,
        {},
    )

    assert result == {
        "namespace": None,
    }


def test_optional_parameter_can_be_none():
    schema = ToolSchema(
        name="kubernetes_health",
        description="Check Kubernetes health",
        parameters=[
            ToolParameter(
                name="namespace",
                type="string",
                description="Kubernetes namespace",
                required=False,
                default=None,
            )
        ],
    )

    result = validate_tool_arguments(
        schema,
        {
            "namespace": None,
        },
    )

    assert result == {
        "namespace": None,
    }


def test_arguments_must_be_dictionary():
    schema = ToolSchema(
        name="test",
        description="Test tool",
    )

    with pytest.raises(
        ToolValidationError,
        match="must be a dictionary",
    ):
        validate_tool_arguments(
            schema,
            "invalid",
        )


def test_tool_with_no_parameters_accepts_empty_arguments():
    schema = ToolSchema(
        name="aws_ec2_health",
        description="Check AWS EC2 health",
    )

    result = validate_tool_arguments(
        schema,
        {},
    )

    assert result == {}


def test_tool_with_no_parameters_rejects_arguments():
    schema = ToolSchema(
        name="aws_ec2_health",
        description="Check AWS EC2 health",
    )

    with pytest.raises(
        ToolValidationError,
        match="Unknown parameter",
    ):
        validate_tool_arguments(
            schema,
            {
                "region": "ap-south-1",
            },
        )
