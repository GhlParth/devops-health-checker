import json

from devops_health_checker.llm import (
    OpenRouterClient,
)
from devops_health_checker.llm_tools import (
    registry_to_openrouter_tools,
)


SYSTEM_PROMPT = """
You are a DevOps infrastructure assistant.

You have access to read-only infrastructure health
tools for AWS, Kubernetes, and GitHub.

Use tools when the user's question requires
actual infrastructure information.

Never invent infrastructure data.

When a tool returns structured results, use those
results to produce a concise and accurate answer.

Do not claim that an action was performed unless
a tool actually executed it successfully.

Only use tools that are provided to you.

If a tool execution fails, clearly communicate
the failure instead of inventing a result.
"""


class DevOpsAgent:
    def __init__(
        self,
        registry,
        llm_client=None,
        max_iterations: int = 5,
    ):
        self.registry = registry

        self.llm = (
            llm_client
            or OpenRouterClient()
        )

        self.max_iterations = max_iterations

        self.tools = registry_to_openrouter_tools(
            registry
        )

    def run(
        self,
        user_message: str,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        for iteration in range(
            self.max_iterations
        ):
            response = self.llm.chat(
                messages=messages,
                tools=self.tools,
            )

            if "error" in response:
                raise RuntimeError(
                    "LLM returned an error: "
                    f"{response['error']}"
                )

            choices = response.get("choices")

            if not choices:
                raise RuntimeError(
                    "LLM response did not contain "
                    "'choices'. Response: "
                    f"{response}"
                )

            message = choices[0]["message"]

            tool_calls = message.get(
                "tool_calls"
            )

            # No tool call means the model has
            # produced the final answer.
            if not tool_calls:
                return (
                    message.get("content")
                    or ""
                )

            # Preserve the assistant tool-call
            # message in the conversation.
            messages.append(message)

            for tool_call in tool_calls:
                function = tool_call["function"]

                tool_name = function["name"]

                arguments_text = (
                    function.get(
                        "arguments",
                        "{}",
                    )
                )

                try:
                    arguments = json.loads(
                        arguments_text
                    )

                except json.JSONDecodeError as error:
                    tool_result = {
                        "success": False,
                        "error": (
                            "Invalid JSON arguments "
                            f"from model: {error}"
                        ),
                    }

                else:
                    try:
                        execution = (
                            self.registry.execute(
                                tool_name,
                                arguments,
                            )
                        )

                        tool_result = (
                            execution.to_dict()
                        )

                    except KeyError as error:
                        tool_result = {
                            "success": False,
                            "error": (
                                "Unknown tool requested "
                                f"by model: {error}"
                            ),
                        }

                    except Exception as error:
                        tool_result = {
                            "success": False,
                            "error": (
                                "Tool execution failed: "
                                f"{error}"
                            ),
                        }

                messages.append({
                    "role": "tool",
                    "tool_call_id": (
                        tool_call["id"]
                    ),
                    "content": json.dumps(
                        tool_result
                    ),
                })

        raise RuntimeError(
            "Agent reached the maximum number "
            "of iterations."
        )
