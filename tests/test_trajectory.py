import json

import pytest
from pydantic import ValidationError

from failure_complementarity.logging.schema import EventType
from failure_complementarity.logging.structured import setup_logging
from failure_complementarity.logging.trajectory import TrajectoryWriter, read_trajectory


def test_write_read_and_resume(tmp_path):
    p = tmp_path / "run" / "trajectory.jsonl"
    with TrajectoryWriter(p, run_id="r1", task_id="t1", agent="qwen") as w:
        w.emit(EventType.RUN_START, metadata={"phase": "primary"})
        w.emit("tool_call", step=1, tool="bash", content="ls -la")
    with TrajectoryWriter(p, run_id="r1", task_id="t1", agent="qwen") as w:  # resumed session
        w.emit(EventType.RUN_END, content={"exit_reason": "SUBMITTED"})
    events = read_trajectory(p)
    assert [e.seq for e in events] == [0, 1, 2]
    assert events[1].event_type is EventType.TOOL_CALL and events[1].tool == "bash" and events[1].step == 1
    raw = json.loads(p.read_text().splitlines()[0])
    assert set(raw) == {"timestamp", "run_id", "task_id", "agent", "seq", "step", "event_type", "tool",
                        "content", "metadata"}
    assert raw["timestamp"].endswith("+00:00")


def test_unknown_event_type_rejected(tmp_path):
    with TrajectoryWriter(tmp_path / "t.jsonl", run_id="r", task_id="t", agent="a") as w:
        with pytest.raises(ValueError):
            w.emit("made_up_event")


def test_extra_fields_rejected_on_read(tmp_path):
    p = tmp_path / "t.jsonl"
    with TrajectoryWriter(p, run_id="r", task_id="t", agent="a") as w:
        w.emit(EventType.ERROR, content="boom")
    line = json.loads(p.read_text())
    line["unexpected"] = 1
    p.write_text(json.dumps(line) + "\n")
    with pytest.raises(ValidationError):
        read_trajectory(p)


def test_structured_log_file_is_json(tmp_path):
    log = setup_logging(tmp_path / "run.log")
    log.getChild("runner").info("branch started", extra={"task_id": "t1", "branch": "recovery_devstral"})
    rec = json.loads((tmp_path / "run.log").read_text().splitlines()[-1])
    assert rec["message"] == "branch started" and rec["task_id"] == "t1" and rec["logger"] == "fc.runner"
