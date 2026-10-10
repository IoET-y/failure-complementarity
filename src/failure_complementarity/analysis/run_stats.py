"""Per-run behaviour counts derived from the JSONL trajectory and the final diff.

``files_edited`` is exact (from the diff). ``n_test_commands`` and ``files_read`` are command-pattern
heuristics, labelled as such in result.json.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

from failure_complementarity.logging.schema import EventType, TrajectoryEvent

TEST_CMD = re.compile(
    r"(\bpytest\b|\bpy\.test\b|-m\s+unittest\b|\btox\b|\bnox\b|\bgo\s+test\b|\b(npm|yarn|pnpm)\s+(run\s+)?test\b|"
    r"\b(npx\s+)?(jest|mocha|vitest|karma)\b|\bmake\s+(test|check)\b|\bcargo\s+test\b|\bansible-test\b|"
    r"/tests/run_script\.sh|\brun_tests?\b|\btest\.sh\b)"
)
READ_CMDS = {"cat", "head", "tail", "nl", "less", "more", "sed", "grep", "rg", "awk", "wc", "view", "bat"}
_PATHLIKE = re.compile(r"^[\w./@+-]*[./][\w./@+-]*$")


def files_edited_from_diff(diff: bytes) -> list[str]:
    files = []
    for line in diff.decode("utf-8", errors="replace").splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.+?) b/(.+)$", line)
            if m:
                files.append(m.group(2))
    return sorted(set(files))


def _read_paths(command: str) -> set[str]:
    out: set[str] = set()
    for segment in re.split(r"&&|\|\||;|\|", command):
        try:
            toks = shlex.split(segment)
        except ValueError:
            continue
        if not toks or toks[0] not in READ_CMDS:
            continue
        for t in toks[1:]:
            if not t.startswith("-") and _PATHLIKE.match(t) and not re.fullmatch(r"[\d,.$p]+", t):
                out.add(t)
    return out


def compute_run_stats(events: list[TrajectoryEvent], diff: bytes) -> dict[str, Any]:
    commands = [e.content or "" for e in events if e.event_type is EventType.TOOL_CALL]
    model_events = [e for e in events if e.event_type in (EventType.MODEL_RESPONSE, EventType.FORMAT_ERROR)]
    files_read: set[str] = set()
    for c in commands:
        files_read |= _read_paths(c)
    return {
        "n_model_calls": len(model_events),
        "n_format_errors": sum(e.event_type is EventType.FORMAT_ERROR for e in events),
        "n_tool_calls": len(commands),
        "n_shell_commands": len(commands),  # the harness exposes a single bash tool
        "n_test_commands_heuristic": sum(bool(TEST_CMD.search(c)) for c in commands),
        "files_read_heuristic": sorted(files_read),
        "files_edited": files_edited_from_diff(diff),
        "model_seconds": round(sum(float(e.metadata.get("seconds") or 0) for e in model_events), 3),
        "tool_seconds": round(sum(float(e.metadata.get("seconds") or 0) for e in events
                                  if e.event_type is EventType.TOOL_RESULT), 3),
    }
