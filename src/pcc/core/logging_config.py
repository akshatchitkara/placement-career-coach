"""JSON-lines logging setup. Never log secrets (api_key, student free text)."""

import json
import logging
from datetime import UTC, datetime


class JsonLinesFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLinesFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
