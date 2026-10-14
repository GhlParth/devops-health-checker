from typing import Any

from devops_health_checker.schemas import (
    ToolSchema,
)


class ToolValidationError(Exception):
    """Raised when tool arguments are invalid."""


TYPE_MAPPING: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_tool_arguments(
    schema: ToolSchema,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate and normalize arguments for a tool.

    Validation includes:
    - required parameters
    - unknown parameters
    - basic type validation
    - applying default values

    Returns:
        A validated and normalized argument dictionary.

    Raises:
        ToolValidationError:
            If the arguments are invalid.
    """

    if arguments is None:
        arguments = {}

    if not isinstance(arguments, dict):
        raise ToolValidationError("Tool arguments must be a dictionary.")

    parameters = {parameter.name: parameter for parameter in schema.parameters}

    # ---------------------------------------------------------
    # 1. Check for unknown parameters
    # ---------------------------------------------------------

    unknown_parameters = [name for name in arguments if name not in parameters]

    if unknown_parameters:
        raise ToolValidationError("Unknown parameter(s): " + ", ".join(sorted(unknown_parameters)))

    # ---------------------------------------------------------
    # 2. Check required parameters
    # ---------------------------------------------------------

    missing_parameters = []

    for parameter in schema.parameters:
        if parameter.required and parameter.name not in arguments:
            missing_parameters.append(parameter.name)

    if missing_parameters:
        raise ToolValidationError("Missing required parameter(s): " + ", ".join(missing_parameters))

    # ---------------------------------------------------------
    # 3. Apply defaults
    # ---------------------------------------------------------

    validated_arguments = dict(arguments)

    for parameter in schema.parameters:
        if parameter.name not in validated_arguments and not parameter.required:
            validated_arguments[parameter.name] = parameter.default

    # ---------------------------------------------------------
    # 4. Validate types
    # ---------------------------------------------------------

    for parameter in schema.parameters:
        if parameter.name not in validated_arguments:
            continue

        value = validated_arguments[parameter.name]

        # Allow None when an optional parameter has
        # a default value of None.
        if value is None:
            if not parameter.required:
                continue

            raise ToolValidationError(f"Parameter '{parameter.name}' cannot be None.")

        expected_type = TYPE_MAPPING.get(parameter.type)

        if expected_type is None:
            raise ToolValidationError(f"Unsupported parameter type: {parameter.type}")

        if not isinstance(
            value,
            expected_type,
        ):
            raise ToolValidationError(
                f"Parameter '{parameter.name}' must be of type {parameter.type}."
            )

    return validated_arguments
