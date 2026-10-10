"""Process-level logging: JSON lines to a file, concise text to stderr."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from failure_complementarity.logging.trajectory import utc_now

_STD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": utc_now(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # anything passed via `extra={...}` becomes a structured field
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STD_ATTRS})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger("fc")
    root.setLevel(level)
    root.handlers.clear()
    root.propagate = False
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(console)
    if log_file is not None:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(JsonFormatter())
        root.addHandler(fh)
    return root
