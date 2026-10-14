from devops_health_checker.schemas import ToolSchema


def schema_to_openrouter_tool(
    schema: ToolSchema,
) -> dict:
    properties = {}

    required = []

    for parameter in schema.parameters:
        properties[parameter.name] = {
            "type": parameter.type,
            "description": parameter.description,
        }

        if parameter.default is not None:
            properties[
                parameter.name
            ]["default"] = parameter.default

        if parameter.required:
            required.append(parameter.name)

    return {
        "type": "function",
        "function": {
            "name": schema.name,
            "description": schema.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def registry_to_openrouter_tools(
    registry,
) -> list[dict]:
    return [
        schema_to_openrouter_tool(tool.schema)
        for tool in registry.list_tools()
    ]