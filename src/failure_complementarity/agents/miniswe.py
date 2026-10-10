"""mini-SWE-agent bound to our sandbox and endpoint (decision D-004).

Unchanged mini-SWE-agent ``DefaultAgent`` control flow and prompts; this module only adds:
* ``ApptainerEnvironment`` — executes each bash action in the branch's no-network instance (mirrors the
  official ``v2/tooling/host_mini_swe.py``, incl. its completion-marker check);
* ``EndpointModel`` — ``LitellmModel`` without silent retries (D-014) and with context-overflow detection;
* ``RecordingAgent`` — emits every model response / tool call / result to ``trajectory.jsonl``.
"""

from __future__ import annotations

import platform
import time
from pathlib import Path
from typing import Any

import litellm
import yaml
from minisweagent.agents.default import DefaultAgent
from minisweagent.exceptions import FormatError, Submitted
from minisweagent.models.litellm_model import LitellmModel

from failure_complementarity.config import AgentSpec
from failure_complementarity.logging.schema import EventType
from failure_complementarity.logging.trajectory import TrajectoryWriter
from failure_complementarity.runner.sandbox import Instance, SandboxError

SUBMIT_MARKER = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"


class ContextLimitExceeded(Exception):
    """Prompt no longer fits the (shared) context window: model behaviour, not infrastructure (D-012)."""


class ModelEndpointError(Exception):
    """Endpoint failure (connection, timeout, 5xx, bad request): infrastructure (D-014)."""


# --------------------------------------------------------------------------- environment


class ApptainerEnvironment:
    def __init__(self, instance: Instance, *, cwd: str, timeout: int):
        self.instance, self.cwd, self.timeout = instance, cwd, timeout
        self.config = {"cwd": cwd, "timeout": timeout, "env": instance.env, "runtime": "apptainer-instance"}

    def execute(self, action: dict, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        command = action.get("command", "")
        t = timeout or self.timeout
        try:
            r = self.instance.exec(command, timeout=t, cwd=cwd or self.cwd)
        except SandboxError:
            raise  # the container itself failed: CONTAINER_ERROR
        except Exception as e:  # noqa: BLE001 - e.g. a NUL byte in the command; same observation as mini-swe-agent's
            # LocalEnvironment / DockerEnvironment give for exceptions during execution (decision D-032)
            output = {"output": "", "returncode": -1,
                      "exception_info": f"An error occurred while executing the command: {e}",
                      "extra": {"exception_type": type(e).__name__, "exception": str(e)}}
            return output
        if r.timed_out:  # same observation shape as mini-swe-agent's LocalEnvironment on TimeoutExpired
            msg = f"Command '{command}' timed out after {t} seconds"
            output = {"output": r.output, "returncode": -1,
                      "exception_info": f"An error occurred while executing the command: {msg}",
                      "extra": {"exception_type": "TimeoutExpired", "exception": msg, "seconds": round(r.seconds, 3)}}
        else:
            output = {"output": r.output, "returncode": r.returncode, "exception_info": "",
                      "extra": {"seconds": round(r.seconds, 3)}}
        lines = output["output"].lstrip().splitlines(keepends=True)
        if lines and lines[0].strip() == SUBMIT_MARKER and output["returncode"] == 0:
            submission = "".join(lines[1:])
            raise Submitted({"role": "exit", "content": submission,
                             "extra": {"exit_status": "Submitted", "submission": submission}})
        return output

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return {"cwd": self.cwd, "timeout": self.timeout, **platform.uname()._asdict(), **kwargs}

    def serialize(self) -> dict:
        return {"info": {"config": {"environment": self.config,
                                    "environment_type": f"{self.__class__.__module__}.{self.__class__.__name__}"}}}


# --------------------------------------------------------------------------- model


def _is_context_overflow(e: Exception) -> bool:
    if isinstance(e, litellm.exceptions.ContextWindowExceededError):
        return True
    text = str(e).lower()
    return isinstance(e, litellm.exceptions.BadRequestError) and (
        "maximum context length" in text or "context length" in text or "too many tokens" in text
        or "prompt is too long" in text or ("max_tokens" in text and "too large" in text))


class EndpointModel(LitellmModel):
    """One attempt per model call (no tenacity retries): any failure ends the run with a classified exception."""

    abort_exceptions = [Exception]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.call_log: list[dict[str, Any]] = []

    def _query(self, messages, **kwargs):
        t0 = time.monotonic()
        try:
            resp = super()._query(messages, **kwargs)
        except Exception as e:
            self.call_log.append({"ok": False, "seconds": round(time.monotonic() - t0, 3),
                                  "error_type": type(e).__name__, "error": str(e)[:4000]})
            if _is_context_overflow(e):
                raise ContextLimitExceeded(str(e)[:4000]) from e
            raise ModelEndpointError(f"{type(e).__name__}: {str(e)[:4000]}") from e
        self.call_log.append({"ok": True, "seconds": round(time.monotonic() - t0, 3)})
        return resp


def build_model(spec: AgentSpec, miniswe_cfg: dict[str, Any], *, max_tokens: int, request_timeout: int) -> EndpointModel:
    """Official V2 model templates + our endpoint. ``reasoning_effort`` from the V2 config is provider-specific
    and dropped (D-004); sampling is the model card's (D-008); top_k / repetition_penalty go via extra_body."""
    model_cfg = dict(miniswe_cfg.get("model", {}))
    model_cfg.pop("model_class", None)
    model_kwargs = {k: v for k, v in dict(model_cfg.pop("model_kwargs", {})).items() if k not in ("reasoning_effort",)}
    standard = {k: v for k, v in spec.sampling.items() if k in ("temperature", "top_p")}
    extra_body = {k: v for k, v in spec.sampling.items() if k not in standard}
    model_kwargs.update(standard, api_base=spec.base_url, api_key=spec.api_key(), max_tokens=max_tokens,
                        timeout=request_timeout, num_retries=0)
    if extra_body:
        model_kwargs["extra_body"] = extra_body
    return EndpointModel(model_name=f"openai/{spec.model}", model_kwargs=model_kwargs, cost_tracking="ignore_errors",
                         **model_cfg)


def load_miniswe_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


# --------------------------------------------------------------------------- agent


class RecordingAgent(DefaultAgent):
    def __init__(self, model, env, *, traj: TrajectoryWriter, **kwargs):
        super().__init__(model, env, **kwargs)
        self.traj = traj
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.n_format_errors = 0
        self.n_tool_calls = 0

    def _add_usage(self, response: Any) -> dict[str, Any] | None:
        usage = response.get("usage") if isinstance(response, dict) else None
        if usage:
            for k in self.usage:
                self.usage[k] += int(usage.get(k) or 0)
        return usage

    def query(self) -> dict:
        step, t0 = self.n_calls + 1, time.monotonic()
        try:
            message = super().query()
        except FormatError as e:
            self.n_format_errors += 1
            extra = e.messages[0].get("extra", {})
            usage = self._add_usage(extra.get("response"))
            self.traj.emit(EventType.FORMAT_ERROR, step=step, content=e.messages[0].get("content"),
                           metadata={"seconds": round(time.monotonic() - t0, 3), "usage": usage,
                                     "response": extra.get("response")})
            raise
        response = message.get("extra", {}).get("response", {})
        usage = self._add_usage(response)
        choice = (response.get("choices") or [{}])[0]
        self.traj.emit(EventType.MODEL_RESPONSE, step=step,
                       content={"content": message.get("content"), "tool_calls": message.get("tool_calls")},
                       metadata={"seconds": round(time.monotonic() - t0, 3), "usage": usage,
                                 "finish_reason": choice.get("finish_reason"), "response_id": response.get("id")})
        return message

    def execute_actions(self, message: dict) -> list[dict]:
        outputs = []
        for action in message.get("extra", {}).get("actions", []):
            self.n_tool_calls += 1
            self.traj.emit(EventType.TOOL_CALL, step=self.n_calls, tool="bash", content=action.get("command"),
                           metadata={"tool_call_id": action.get("tool_call_id")})
            try:
                out = self.env.execute(action)
            except Submitted as e:
                self.traj.emit(EventType.TOOL_RESULT, step=self.n_calls, tool="bash", content=e.messages[0]["content"],
                               metadata={"returncode": 0, "submitted": True})
                raise
            self.traj.emit(EventType.TOOL_RESULT, step=self.n_calls, tool="bash", content=out.get("output"),
                           metadata={"returncode": out.get("returncode"), "exception_info": out.get("exception_info"),
                                     **out.get("extra", {})})
            outputs.append(out)
        return self.add_messages(*self.model.format_observation_messages(message, outputs, self.get_template_vars()))
