import logging
import os
import sys

try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:
    from pythonjsonlogger.jsonlogger import JsonFormatter  # type: ignore[no-redef]


def setup_logger(name: str = "devops-health-checker", level: str | None = None) -> logging.Logger:
    """Return a structured JSON logger suitable for Kubernetes/Loki scraping.

    Uses python-json-logger so every log line is valid JSON and can be
    queried by field (level, request_id, tool_name, etc.) in Grafana/Loki.
    Falls back to plain text when LOG_FORMAT=text (useful in local dev).
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    resolved_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(resolved_level)

    handler = logging.StreamHandler(sys.stdout)

    log_format = os.getenv("LOG_FORMAT", "json").lower()
    if log_format == "text":
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
