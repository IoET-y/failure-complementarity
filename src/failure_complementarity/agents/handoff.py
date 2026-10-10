"""Handoff note (decision D-026): after a primary failure, A's own model — given A's final conversation — writes
a short note for the next engineer. The note is the only extra information the "note" rescue conditions get.

The request is appended to A's conversation (system, task, every assistant/tool turn) and sent once with
``tool_choice="none"``. If the conversation is too long for the context window, whole steps (an assistant turn
with its tool results) are dropped from the middle and replaced by a one-line marker; how many is recorded.
No reasoning/thinking content is sent or kept.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import litellm
from minisweagent.models.utils.actions_toolcall import BASH_TOOL

from failure_complementarity.config import AgentSpec

KEEP_KEYS = ("role", "content", "tool_calls", "tool_call_id", "name")
CHARS_PER_TOKEN = 3.0  # conservative estimate for code-heavy text


def load_conversation(mini_trajectory: Path) -> list[dict[str, Any]]:
    data = json.loads(Path(mini_trajectory).read_text())
    msgs = []
    for m in data["messages"]:
        if m.get("role") not in ("system", "user", "assistant", "tool"):
            continue  # the final "exit" record is not a chat message
        msg = {k: m[k] for k in KEEP_KEYS if k in m and m[k] is not None}
        if msg["role"] == "assistant":
            msg.setdefault("content", "")
            if not msg.get("tool_calls"):
                msg.pop("tool_calls", None)
        msgs.append(msg)
    return msgs


def group_steps(msgs: list[dict]) -> tuple[list[dict], list[list[dict]]]:
    """(head = system + task message, steps = [assistant turn + the tool/user messages that follow it])."""
    head, rest = msgs[:2], msgs[2:]
    steps: list[list[dict]] = []
    for m in rest:
        if m["role"] == "assistant" or not steps:
            steps.append([m])
        else:
            steps[-1].append(m)
    return head, steps


def truncate(msgs: list[dict], max_chars: int) -> tuple[list[dict], int]:
    """Keep head and as many most-recent whole steps as fit; return (messages, number of dropped steps)."""
    size = lambda ms: sum(len(json.dumps(m)) for m in ms)  # noqa: E731
    if size(msgs) <= max_chars:
        return msgs, 0
    head, steps = group_steps(msgs)
    kept: list[list[dict]] = []
    budget = max_chars - size(head) - 200
    for step in reversed(steps):
        s = size(step)
        if s > budget:
            break
        kept.insert(0, step)
        budget -= s
    dropped = len(steps) - len(kept)
    marker = {"role": "user", "content": f"[{dropped} earlier steps of this conversation are omitted for length.]"}
    out = head + [marker] + [m for step in kept for m in step]
    return out, dropped


def generate_note(spec: AgentSpec, mini_trajectory: Path, request: str, *, max_model_len: int,
                  max_tokens: int = 2048, timeout: int = 900) -> dict[str, Any]:
    msgs = load_conversation(mini_trajectory)
    max_chars = int((max_model_len - max_tokens - 2048) * CHARS_PER_TOKEN)
    standard = {k: v for k, v in spec.sampling.items() if k in ("temperature", "top_p")}
    extra = {k: v for k, v in spec.sampling.items() if k not in standard}
    last_error = None
    for attempt in range(3):  # shrink the window if the server still says the prompt is too long
        window, dropped = truncate(msgs, int(max_chars / (2 ** attempt)))
        t0 = time.monotonic()
        try:
            resp = litellm.completion(
                model=f"openai/{spec.model}", api_base=spec.base_url, api_key=spec.api_key(),
                messages=window + [{"role": "user", "content": request}], tools=[BASH_TOOL], tool_choice="none",
                max_tokens=max_tokens, timeout=timeout, num_retries=0, **standard,
                **({"extra_body": extra} if extra else {}),
            )
        except Exception as e:  # noqa: BLE001
            last_error = f"{type(e).__name__}: {str(e)[:2000]}"
            if "context" in str(e).lower() or "too long" in str(e).lower() or "maximum" in str(e).lower():
                continue
            raise
        choice = resp.choices[0]
        return {
            "note": (choice.message.content or "").strip(),
            "finish_reason": choice.finish_reason,
            "usage": resp.usage.model_dump() if resp.usage else None,
            "dropped_steps": dropped,
            "n_messages_sent": len(window) + 1,
            "seconds": round(time.monotonic() - t0, 2),
            "attempts": attempt + 1,
            "response_id": resp.id,
        }
    raise RuntimeError(f"handoff note: prompt too long even after shrinking ({last_error})")
