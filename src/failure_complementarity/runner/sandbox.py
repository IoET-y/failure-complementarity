"""Apptainer sandboxes (decision D-002).

A branch's container is a private *writable rootfs directory* on node-local disk, run with ``--fakeroot``
(uid 0 inside, like Docker). Its whole filesystem state lives in that directory, which is what makes exact
checkpoints possible (checkpoint/). Two ways to run commands:

* ``Instance`` — a persistent container (processes survive between agent commands, like ``docker exec``);
  used for the agent phase, always with no network;
* ``run_oneshot`` — a single ``apptainer exec``; used for diff capture and for the evaluator.
"""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

COMMON_FLAGS = ["--containall", "--cleanenv", "--no-home", "--no-mount", "tmp", "--fakeroot", "--ignore-fakeroot-command"]
NO_NETWORK = ["--net", "--network", "none"]
REPO_DIRS = ("/app", "/testbed")  # V2 images keep the repository in /app, a few in /testbed


class SandboxError(RuntimeError):
    """The container itself failed (maps to CONTAINER_ERROR)."""


@dataclass
class ExecResult:
    returncode: int
    output: str
    timed_out: bool
    seconds: float


def unpack_sif(sif: Path, rootfs: Path) -> None:
    if rootfs.exists():
        raise SandboxError(f"refusing to unpack into existing directory {rootfs}")
    rootfs.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["apptainer", "-q", "build", "--sandbox", str(rootfs), str(sif)], capture_output=True, text=True)
    if p.returncode != 0:
        raise SandboxError(f"unpack of {sif} failed:\n{p.stderr[-3000:]}")


def _run(cmd: list[str], timeout: float | None, *, merge_stderr: bool = True) -> tuple[int, bytes, bytes, bool, float]:
    """Run in its own process group; on timeout kill the whole group.

    Returns (rc, stdout, stderr, timed_out, seconds); with ``merge_stderr`` stderr is folded into stdout (the
    agent sees both streams interleaved, as with ``docker exec``) and the returned stderr is empty.
    """
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err or b"", False, time.monotonic() - t0
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        return -9, out or b"", err or b"", True, time.monotonic() - t0


def run_oneshot(
    rootfs: Path,
    command: str,
    *,
    network: bool,
    writable: bool = True,
    binds: list[str] = (),
    cwd: str | None = None,
    timeout: float | None = None,
    merge_stderr: bool = True,
) -> tuple[int, bytes, bytes, bool, float]:
    cmd = ["apptainer", "-q", "exec", *COMMON_FLAGS]
    if writable:
        cmd.append("--writable")
    if not network:
        cmd += NO_NETWORK
    for b in binds:
        cmd += ["-B", b]
    if cwd:
        cmd += ["--pwd", cwd]
    cmd += [str(rootfs), "bash", "-c", command]
    return _run(cmd, timeout, merge_stderr=merge_stderr)


def detect_repo_dir(rootfs: Path) -> str:
    for d in REPO_DIRS:
        if (rootfs / d.lstrip("/") / ".git").exists():
            return d
    raise SandboxError(f"no git repository at {REPO_DIRS} in {rootfs}")


class Instance:
    """Persistent no-network container over a writable rootfs."""

    def __init__(self, rootfs: Path, *, env: dict[str, str] | None = None, name: str | None = None):
        self.rootfs = Path(rootfs)
        self.name = name or f"fc{uuid.uuid4().hex[:12]}"
        self.env = dict(env or {})
        self.started = False
        self.has_timeout_bin = False

    def start(self) -> None:
        cmd = ["apptainer", "-q", "instance", "start", *COMMON_FLAGS, "--writable", *NO_NETWORK, str(self.rootfs), self.name]
        rc, out, _, timed_out, _ = _run(cmd, timeout=300)
        if rc != 0 or timed_out:
            raise SandboxError(f"instance start failed ({rc}): {out.decode(errors='replace')[-3000:]}")
        self.started = True
        probe = self.exec("command -v timeout >/dev/null && echo FC_HAS_TIMEOUT", timeout=60, use_inner_timeout=False)
        self.has_timeout_bin = "FC_HAS_TIMEOUT" in probe.output

    def is_alive(self) -> bool:
        rc, out, _, _, _ = _run(["apptainer", "-q", "instance", "list", "--json", self.name], timeout=60)
        if rc != 0:
            return False
        try:
            return any(i.get("instance") == self.name for i in json.loads(out).get("instances", []))
        except json.JSONDecodeError:
            return False

    def exec(self, command: str, *, timeout: int, cwd: str | None = None, use_inner_timeout: bool = True) -> ExecResult:
        """Run ``bash -c command``. The command is bounded *inside* the container with coreutils ``timeout`` so
        the process really dies (killing only the host-side client would leave it running in the instance)."""
        if not self.started:
            raise SandboxError("instance not started")
        cmd = ["apptainer", "-q", "exec", "--cleanenv"]
        for k, v in self.env.items():
            cmd += ["--env", f"{k}={v}"]
        if cwd:
            cmd += ["--pwd", cwd]
        cmd.append(f"instance://{self.name}")
        if use_inner_timeout and self.has_timeout_bin:
            cmd += ["timeout", "-k", "5", str(timeout), "bash", "-c", command]
        else:
            cmd += ["bash", "-c", command]
        rc, out, _, host_timed_out, secs = _run(cmd, timeout=timeout + 30)
        text = out.decode("utf-8", errors="replace")
        if rc == -9 and not host_timed_out:
            # the host-side client was SIGKILLed by something other than our own timeout (in practice the cgroup
            # OOM killer): the environment, not the agent, failed (decision D-025)
            raise SandboxError(f"command killed by host SIGKILL after {secs:.1f}s (probable OOM kill)")
        if rc == 255 and "FATAL" in text and not self.is_alive():
            raise SandboxError(f"instance {self.name} is gone: {text[-2000:]}")
        # rc 124/137 alone is ambiguous (the agent may run `timeout` itself); also require the full duration
        inner_kill = use_inner_timeout and self.has_timeout_bin and rc in (124, 137) and secs >= timeout - 0.5
        timed_out = host_timed_out or inner_kill
        return ExecResult(rc, text, timed_out, secs)

    def stop(self) -> None:
        if self.started:
            _run(["apptainer", "-q", "instance", "stop", "-t", "10", self.name], timeout=120)
            if self.is_alive():
                _run(["apptainer", "-q", "instance", "stop", "-F", self.name], timeout=120)
            self.started = False

    def __enter__(self) -> "Instance":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


def quote(s: str) -> str:
    return shlex.quote(s)
