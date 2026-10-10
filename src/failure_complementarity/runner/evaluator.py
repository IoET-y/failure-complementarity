"""Official-protocol evaluation (decision D-005): apply a captured diff to a FRESH pristine rootfs and run the
unchanged V2 verifier (``tests/test.sh``) with network, as ``v2/tooling/patch_replay.py`` does.

The agent's sandbox is never used for grading, so nothing the agent did to its environment (shimmed tools,
edited node_modules, …) can influence the result.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from failure_complementarity.benchmark.swebench_pro import Task
from failure_complementarity.fsutil import remove_tree
from failure_complementarity.logging.schema import EvalStatus
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.runner.sandbox import SandboxError, run_oneshot, unpack_sif

# Same fallback chain as the official patch_replay.py (plus --binary-safe git apply, which is the default).
APPLY_AND_TEST = r"""
cd /app 2>/dev/null || cd /testbed
if [ -s /tmp/fc_replay.patch ]; then
  { git apply --verbose /tmp/fc_replay.patch || git apply --3way /tmp/fc_replay.patch || patch --fuzz=3 -p1 -i /tmp/fc_replay.patch; } > /logs/apply.log 2>&1
  echo $? > /logs/apply_rc
else
  echo "empty patch" > /logs/apply.log; echo none > /logs/apply_rc
fi
rm -f /tmp/fc_replay.patch
bash /tests/test.sh > /logs/test_stdout.txt 2>&1
echo $? > /logs/test_rc
"""


@dataclass
class EvalResult:
    status: EvalStatus
    reward: int | None
    patch_bytes: int
    apply_rc: str | None
    verifier_timed_out: bool
    seconds: float
    started_at: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


def evaluate_patch(task: Task, patch: bytes, sif: Path, out_dir: Path, work_dir: Path, timeout: float) -> EvalResult:
    """Grade ``patch`` (a ``git diff --binary`` against the base commit). Writes logs to ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    logs = out_dir / "logs"
    if logs.exists():
        remove_tree(logs)
    logs.mkdir()
    (out_dir / "evaluated.patch").write_bytes(patch)
    started, t0 = utc_now(), time.monotonic()
    rootfs = work_dir / "eval_rootfs"
    try:
        if rootfs.exists():
            remove_tree(rootfs)
        unpack_sif(sif, rootfs)
        for d in ("tests", "logs"):
            (rootfs / d).mkdir(exist_ok=True)  # bind targets must exist in a writable sandbox
        (rootfs / "tmp" / "fc_replay.patch").write_bytes(patch)
        rc, out, _, timed_out, _ = run_oneshot(
            rootfs, APPLY_AND_TEST, network=True, writable=True,
            binds=[f"{task.tests_dir}:/tests:ro", f"{logs}:/logs"], timeout=timeout,
        )
        (out_dir / "apptainer_output.txt").write_bytes(out)
        reward_file = logs / "verifier" / "reward.txt"
        apply_rc = (logs / "apply_rc").read_text().strip() if (logs / "apply_rc").exists() else None
        secs = round(time.monotonic() - t0, 1)
        if rc == -9 and not timed_out:  # verifier killed by the host (OOM), not by its own timeout: D-025
            res = EvalResult(EvalStatus.EVALUATOR_ERROR, None, len(patch), apply_rc, False, secs, started,
                             error="verifier killed by host SIGKILL (probable OOM kill)")
        elif timed_out:
            res = EvalResult(EvalStatus.UNSOLVED, 0, len(patch), apply_rc, True, secs, started)  # D-015
        elif reward_file.exists() and reward_file.read_text().strip() in ("0", "1"):
            reward = int(reward_file.read_text().strip())
            res = EvalResult(EvalStatus.SOLVED if reward == 1 else EvalStatus.UNSOLVED, reward, len(patch),
                             apply_rc, False, secs, started)
        else:
            res = EvalResult(EvalStatus.EVALUATOR_ERROR, None, len(patch), apply_rc, False, secs, started,
                             error=f"no reward file (apptainer rc={rc}): {out.decode(errors='replace')[-1500:]}")
    except SandboxError as e:
        res = EvalResult(EvalStatus.EVALUATOR_ERROR, None, len(patch), None, False,
                         round(time.monotonic() - t0, 1), started, error=str(e))
    finally:
        remove_tree(rootfs)
    (out_dir / "eval.json").write_text(json.dumps(res.to_dict(), indent=2))
    return res
