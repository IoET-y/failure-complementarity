#!/usr/bin/env python3
"""D-025, applied retroactively and uniformly: an attempt in which any agent command was SIGKILLed by the host
(returncode -9 without our own timeout, i.e. the OOM killer) is an infrastructure failure (CONTAINER_ERROR).
Original fields are kept under ``reclassified.original``; the branch-level result.json is removed so the normal
retry (D-012) runs a fresh attempt. Dry run unless --apply.

    python scripts/apply_d025.py --experiment pilot_v1 [--apply]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from failure_complementarity.logging.trajectory import utc_now

ROOT = Path(__file__).resolve().parents[1]


def host_killed_steps(traj: Path) -> list[int]:
    steps = []
    for line in open(traj):
        e = json.loads(line)
        if e["event_type"] == "tool_result" and e["metadata"].get("returncode") == -9 and not e["metadata"].get("exception_info"):
            steps.append(e["step"])
    return steps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    exp = ROOT / "runs" / args.experiment
    for res in sorted(exp.glob("*/*/result.json")):
        r = json.loads(res.read_text())
        att = res.parent / r["final_attempt"]
        steps = host_killed_steps(att / "trajectory.jsonl")
        if not steps or r["outcome_class"] == "INFRA_FAILURE":
            continue
        print(f"{res.parent.parent.name[:50]} {res.parent.name} {att.name}: host SIGKILL at steps {steps}; was {r['status']}")
        if not args.apply:
            continue
        ar = json.loads((att / "result.json").read_text())
        orig = {k: ar.get(k) for k in ("exit_reason", "eval_status", "outcome_class", "status", "solved", "primary_failure")}
        ar.update(exit_reason="CONTAINER_ERROR", outcome_class="INFRA_FAILURE", status="CONTAINER_ERROR", solved=None)
        ar.pop("primary_failure", None)
        ar["reclassified"] = {"decision": "D-025", "at": utc_now(), "host_killed_steps": steps, "original": orig}
        (att / "result.json").write_text(json.dumps(ar, indent=2, default=str))
        res.rename(res.with_name("result.superseded_by_D-025.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
