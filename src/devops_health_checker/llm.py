import os

import requests
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Errors that are safe to retry (transient network / server-side issues).
_RETRYABLE = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


class LLMError(Exception):
    """Raised when an LLM request fails."""


class OpenRouterClient:
    """Client for the OpenRouter Chat Completions API.

    Automatically retries on transient network errors with exponential
    back-off (up to 3 attempts, 1-10 s delay).  Non-retryable HTTP errors
    (e.g. 401 Unauthorized, 400 Bad Request) are surfaced immediately.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY is not configured.")

        self.model = model
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        return self._chat_with_retry(messages, tools)

    @retry(
        reraise=True,
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _chat_with_retry(
        self,
        messages: list[dict],
        tools: list[dict] | None,
    ) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )

        if not response.ok:
            raise LLMError(
                f"OpenRouter request failed (HTTP {response.status_code}): {response.text}"
            )

        return response.json()
