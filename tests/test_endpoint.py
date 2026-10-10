"""Endpoint health check against an in-process fake OpenAI-compatible server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from failure_complementarity.agents.endpoint import check_endpoint
from failure_complementarity.agents.serve import vllm_command


def _make_server(served_model: str, tool_mode: str):
    seen = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/v1/models":
                self._send({"object": "list", "data": [{"id": served_model, "object": "model"}]})
            elif self.path == "/version":
                self._send({"version": "0.31.0"})
            else:
                self._send({"error": "nf"}, 404)

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["request"] = req
            if tool_mode == "ok":
                msg = {"role": "assistant", "content": None, "tool_calls": [{
                    "id": "c1", "type": "function",
                    "function": {"name": "bash", "arguments": json.dumps({"command": "echo fc_probe_ok"})}}]}
            elif tool_mode == "text":
                msg = {"role": "assistant", "content": "<tool_call>bash echo fc_probe_ok</tool_call>"}
            else:
                self._send({"error": "boom"}, 500)
                return
            self._send({"choices": [{"message": msg, "finish_reason": "tool_calls"}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


@pytest.fixture
def spec(cfg):
    return cfg.agent("qwen")


def _with_url(spec, srv):
    return spec.model_copy(update={"base_url": f"http://127.0.0.1:{srv.server_address[1]}/v1"})


def test_endpoint_ok_and_sampling_forwarded(spec):
    srv, seen = _make_server(spec.model, "ok")
    try:
        rep = check_endpoint(_with_url(spec, srv))
    finally:
        srv.shutdown()
    assert rep.ok, rep
    assert rep.server_version == "0.31.0"
    assert rep.tool_call_detail["arguments"] == {"command": "echo fc_probe_ok"}
    req = seen["request"]
    assert req["model"] == spec.model and req["tools"][0]["function"]["name"] == "bash"
    assert req["temperature"] == 0.7 and req["top_k"] == 20


def test_wrong_model_is_not_accepted(spec):
    srv, _ = _make_server("some/other-model", "ok")
    try:
        rep = check_endpoint(_with_url(spec, srv))
    finally:
        srv.shutdown()
    assert not rep.ok and rep.reachable and not rep.model_found
    assert "not the configured model" in rep.error


def test_text_only_tool_call_detected(spec):
    srv, _ = _make_server(spec.model, "text")
    try:
        rep = check_endpoint(_with_url(spec, srv))
    finally:
        srv.shutdown()
    assert not rep.ok and rep.tool_call_ok is False
    assert "no structured tool_calls" in rep.tool_call_detail["reason"]


def test_server_error_during_probe(spec):
    srv, _ = _make_server(spec.model, "error")
    try:
        rep = check_endpoint(_with_url(spec, srv))
    finally:
        srv.shutdown()
    assert not rep.ok and rep.tool_call_ok is False


def test_unreachable(spec):
    rep = check_endpoint(spec.model_copy(update={"base_url": "http://127.0.0.1:9/v1"}), timeout=2)
    assert not rep.ok and not rep.reachable and "models request failed" in rep.error


def test_vllm_command_pins_revision_and_parser(cfg):
    q = vllm_command(cfg.agent("qwen"))
    assert q[:3] == ["vllm", "serve", "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8"]
    assert q[q.index("--revision") + 1] == "dcaee4d4dfc5ee71ad501f01f530e5652438fde0"
    assert q[q.index("--tool-call-parser") + 1] == "qwen3_coder"
    d = vllm_command(cfg.agent("devstral"))
    assert d[d.index("--tool-call-parser") + 1] == "mistral"
    assert d[d.index("--served-model-name") + 1] == cfg.agent("devstral").model
