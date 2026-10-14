import os

import requests
from dotenv import load_dotenv


load_dotenv()


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

DEFAULT_MODEL = (
    "nvidia/nemotron-3-ultra-550b-a55b:free"
)


class LLMError(Exception):
    """Raised when an LLM request fails."""


class OpenRouterClient:
    """Client for the OpenRouter Chat Completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: int = 60,
    ):
        self.api_key = (
            api_key
            or os.getenv("OPENROUTER_API_KEY")
        )

        if not self.api_key:
            raise LLMError(
                "OPENROUTER_API_KEY is not configured."
            )

        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            payload["tools"] = tools

        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": (
                    f"Bearer {self.api_key}"
                ),
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )

        if not response.ok:
            raise LLMError(
                "OpenRouter request failed "
                f"(HTTP {response.status_code}): "
                f"{response.text}"
            )

        return response.json()