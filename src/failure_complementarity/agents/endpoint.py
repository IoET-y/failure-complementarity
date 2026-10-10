"""Health check for an OpenAI-compatible model endpoint.

Checks, in order: the endpoint answers; it serves exactly the configured model id (no silent fallback);
the server version (vLLM ``/version``, optional); and a tool-call probe using mini-SWE-agent's own
``bash`` tool schema, which verifies that the server's tool-call parser returns a structured call.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from failure_complementarity.config import AgentSpec

PROBE_PROMPT = "Use the bash tool to run exactly this command: echo fc_probe_ok"


def _bash_tool() -> dict[str, Any]:
    from minisweagent.models.utils.actions_toolcall import BASH_TOOL

    return BASH_TOOL


@dataclass
class EndpointReport:
    agent: str
    base_url: str
    expected_model: str
    reachable: bool = False
    served_models: list[str] = field(default_factory=list)
    model_found: bool = False
    server_version: str | None = None
    tool_call_ok: bool | None = None
    tool_call_detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.reachable and self.model_found and self.tool_call_ok is not False and self.error is None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"ok": self.ok}


def _server_root(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base[: -len("/v1")] if base.endswith("/v1") else base


def check_endpoint(spec: AgentSpec, *, tool_probe: bool = True, timeout: float = 60.0) -> EndpointReport:
    rep = EndpointReport(agent=spec.name, base_url=spec.base_url, expected_model=spec.model)
    headers = {"Authorization": f"Bearer {spec.api_key()}"}
    base = spec.base_url.rstrip("/")
    with httpx.Client(timeout=timeout, headers=headers) as client:
        try:
            r = client.get(f"{base}/models")
            r.raise_for_status()
            rep.reachable = True
            rep.served_models = [m["id"] for m in r.json().get("data", [])]
        except Exception as e:
            rep.error = f"models request failed: {type(e).__name__}: {e}"
            return rep
        rep.model_found = spec.model in rep.served_models
        if not rep.model_found:
            rep.error = f"endpoint serves {rep.served_models}, not the configured model {spec.model!r}"
            return rep
        try:
            v = client.get(f"{_server_root(spec.base_url)}/version")
            if v.status_code == 200:
                rep.server_version = v.json().get("version")
        except Exception:
            pass  # /version is vLLM-specific; absence is not an error
        if tool_probe:
            rep.tool_call_ok, rep.tool_call_detail = _probe_tool_call(client, base, spec)
            if not rep.tool_call_ok:
                rep.error = f"tool-call probe failed: {rep.tool_call_detail.get('reason')}"
    return rep


def _probe_tool_call(client: httpx.Client, base: str, spec: AgentSpec) -> tuple[bool, dict[str, Any]]:
    body = {
        "model": spec.model,
        "messages": [{"role": "user", "content": PROBE_PROMPT}],
        "tools": [_bash_tool()],
        "max_tokens": 512,
        **spec.sampling,
    }
    t0 = time.monotonic()
    try:
        r = client.post(f"{base}/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return False, {"reason": f"{type(e).__name__}: {e}"}
    detail: dict[str, Any] = {"latency_s": round(time.monotonic() - t0, 3), "usage": data.get("usage")}
    try:
        msg = data["choices"][0]["message"]
        detail["finish_reason"] = data["choices"][0].get("finish_reason")
        calls = msg.get("tool_calls") or []
        detail["n_tool_calls"] = len(calls)
        if not calls:
            detail["reason"] = "no structured tool_calls (parser not enabled or model answered in text)"
            detail["content_head"] = (msg.get("content") or "")[:500]
            return False, detail
        fn = calls[0]["function"]
        args = json.loads(fn["arguments"])
        detail.update(tool=fn["name"], arguments=args)
        if fn["name"] != "bash" or "command" not in args:
            detail["reason"] = "tool call does not match the mini-swe-agent bash schema"
            return False, detail
        return True, detail
    except Exception as e:
        detail["reason"] = f"malformed response: {type(e).__name__}: {e}"
        return False, detail
