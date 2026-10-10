from types import SimpleNamespace

import pytest
from minisweagent.exceptions import Submitted

from failure_complementarity.agents.miniswe import ApptainerEnvironment
from failure_complementarity.runner.sandbox import SandboxError


class FakeInstance:
    env = {}

    def __init__(self, behaviour):
        self.behaviour = behaviour

    def exec(self, command, *, timeout, cwd=None):
        return self.behaviour(command)


def test_exception_in_exec_becomes_observation():
    def boom(cmd):
        raise ValueError("embedded null byte")
    out = ApptainerEnvironment(FakeInstance(boom), cwd="/app", timeout=60).execute({"command": "echo a\x00b"})
    assert out["returncode"] == -1 and "embedded null byte" in out["exception_info"]


def test_container_failure_still_propagates():
    def dead(cmd):
        raise SandboxError("instance gone")
    with pytest.raises(SandboxError):
        ApptainerEnvironment(FakeInstance(dead), cwd="/app", timeout=60).execute({"command": "ls"})


def test_timeout_and_submit():
    env = ApptainerEnvironment(FakeInstance(lambda c: SimpleNamespace(returncode=-9, output="partial", timed_out=True, seconds=60.0)), cwd="/app", timeout=60)
    out = env.execute({"command": "sleep 100"})
    assert out["returncode"] == -1 and "timed out after 60 seconds" in out["exception_info"]
    env = ApptainerEnvironment(FakeInstance(lambda c: SimpleNamespace(returncode=0, output="COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n", timed_out=False, seconds=0.1)), cwd="/app", timeout=60)
    with pytest.raises(Submitted):
        env.execute({"command": "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"})
