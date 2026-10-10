"""Append-only JSONL trajectory writer (one file per run)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from failure_complementarity.logging.schema import EventType, TrajectoryEvent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class TrajectoryWriter:
    """Writes one JSON object per line and fsyncs, so a crash loses at most the event being written.

    Re-opening an existing file continues the sequence numbering (resumed runs keep a single file).
    """

    def __init__(self, path: Path, *, run_id: str, task_id: str, agent: str):
        self.path = Path(path)
        self.run_id, self.task_id, self.agent = run_id, task_id, agent
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = sum(1 for _ in open(self.path)) if self.path.exists() else 0
        self._fh = open(self.path, "a", encoding="utf-8")

    def emit(
        self,
        event_type: EventType | str,
        *,
        step: int | None = None,
        tool: str | None = None,
        content: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> TrajectoryEvent:
        event = TrajectoryEvent(
            timestamp=utc_now(),
            run_id=self.run_id,
            task_id=self.task_id,
            agent=self.agent,
            seq=self._seq,
            step=step,
            event_type=EventType(event_type),
            tool=tool,
            content=content,
            metadata=metadata or {},
        )
        self._fh.write(event.model_dump_json() + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._seq += 1
        return event

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> "TrajectoryWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def read_trajectory(path: Path) -> list[TrajectoryEvent]:
    with open(path, encoding="utf-8") as f:
        return [TrajectoryEvent.model_validate(json.loads(line)) for line in f if line.strip()]
