#!/usr/bin/env python3
"""Scripted OpenAI-compatible endpoint for pipeline tests WITHOUT a GPU. Never use for experiments.

    python scripts/dev/fake_endpoint.py --port 8901 --model Qwen/Qwen3-Coder-30B-A3B-Instruct --script s.json

The script is a JSON list of bash commands; reply i (i = number of assistant messages so far) calls the bash tool
with command i. After the list is exhausted, the last command is repeated (use it to burn the budget), unless the
list ends with the submit command.
"""

import argparse
import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--script", required=True)
    args = ap.parse_args()
    commands = json.load(open(args.script))

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
                self._send({"object": "list", "data": [{"id": args.model, "object": "model"}]})
            elif self.path == "/version":
                self._send({"version": "fake-endpoint"})
            else:
                self._send({}, 404)

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            i = sum(m.get("role") == "assistant" for m in req["messages"])
            cmd = commands[min(i, len(commands) - 1)]
            msg = {"role": "assistant", "content": f"Step {i}: running a scripted command.",
                   "tool_calls": [{"id": f"call_{uuid.uuid4().hex[:8]}", "type": "function",
                                   "function": {"name": "bash", "arguments": json.dumps({"command": cmd})}}]}
            self._send({"id": f"chatcmpl-{uuid.uuid4().hex[:8]}", "object": "chat.completion", "model": args.model,
                        "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls"}],
                        "usage": {"prompt_tokens": 100 * (i + 1), "completion_tokens": 20, "total_tokens": 100 * (i + 1) + 20}})

    ThreadingHTTPServer(("127.0.0.1", args.port), H).serve_forever()


if __name__ == "__main__":
    main()
