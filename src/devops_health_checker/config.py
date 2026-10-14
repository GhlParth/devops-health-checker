import os
from pathlib import Path
from typing import Any

import yaml


def _config_path() -> Path:
    """Return the environment-specific config file.

    Resolution order:
    1. CONFIG_FILE env var (absolute override)
    2. config.<APP_ENV>.yaml  (e.g. config.production.yaml)
    3. config.yaml            (fallback)
    """
    env_override = os.getenv("CONFIG_FILE")
    if env_override:
        return Path(env_override)

    app_env = os.getenv("APP_ENV", "development")
    env_path = Path(f"config.{app_env}.yaml")
    if env_path.exists():
        return env_path

    return Path("config.yaml")


def load_config() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {}
    with path.open("r") as fh:
        return yaml.safe_load(fh) or {}


def get_aws_region(config: dict[str, Any]) -> str:
    return config.get("aws", {}).get("region", "ap-south-1")


def get_github_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("github", {})


def get_kubernetes_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("kubernetes", {})


def get_llm_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return LLM settings from config, falling back to env vars."""
    llm = config.get("llm", {})
    return {
        "model": llm.get("model")
        or os.getenv("LLM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
        "provider": llm.get("provider", "openrouter"),
        "timeout": int(llm.get("timeout", os.getenv("LLM_TIMEOUT", "60"))),
    }
