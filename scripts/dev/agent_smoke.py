#!/usr/bin/env python3
"""Spec §16.5: trivial end-to-end agent smoke test with a REAL model endpoint (not an experiment run).

The agent must create /work/hello.txt containing exactly `hello` inside a throw-away no-network container
and submit. Verifies chat template + tool-call parsing + harness + sandbox together.

    python scripts/dev/agent_smoke.py --config configs/pilot.yaml --agent qwen --sif <some.sif> --out <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from failure_complementarity.agents.miniswe import ApptainerEnvironment, RecordingAgent, build_model, load_miniswe_config
from failure_complementarity.config import load_experiment
from failure_complementarity.fsutil import remove_tree
from failure_complementarity.logging.trajectory import TrajectoryWriter
from failure_complementarity.runner.sandbox import Instance, run_oneshot, unpack_sif

TASK = ("Create the file /work/hello.txt whose entire content is the single word hello followed by a newline. "
        "Verify the content with cat, then finish.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--sif", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cfg = load_experiment(args.config)
    out = Path(args.out) / args.agent
    out.mkdir(parents=True, exist_ok=True)
    rootfs = cfg.paths.work_root / "_agent_smoke" / args.agent / "rootfs"
    remove_tree(rootfs.parent)
    unpack_sif(Path(args.sif), rootfs)
    (rootfs / "work").mkdir(exist_ok=True)
    miniswe = load_miniswe_config(cfg.prompt_path("miniswe_config"))
    model = build_model(cfg.agent(args.agent), miniswe, max_tokens=cfg.budgets.max_tokens_per_response,
                        request_timeout=cfg.budgets.model_request_timeout_seconds)
    agent_cfg = {k: v for k, v in miniswe["agent"].items() if k not in ("mode", "cost_limit", "step_limit")}
    agent_cfg.update(step_limit=20, cost_limit=0.0, wall_time_limit_seconds=300, output_path=out / "mini_trajectory.json")
    report: dict = {"agent": args.agent}
    with TrajectoryWriter(out / "trajectory.jsonl", run_id="agent_smoke", task_id="hello", agent=args.agent) as traj:
        with Instance(rootfs, env=miniswe.get("environment", {}).get("env", {})) as inst:
            env = ApptainerEnvironment(inst, cwd="/work", timeout=60)
            agent = RecordingAgent(model, env, traj=traj, **agent_cfg)
            try:
                report["exit"] = agent.run(TASK)
            except Exception as e:  # noqa: BLE001
                report["exception"] = f"{type(e).__name__}: {e}"
            report.update(steps=agent.n_calls, format_errors=agent.n_format_errors, usage=agent.usage)
    rc, content, _, _, _ = run_oneshot(rootfs, "cat /work/hello.txt", network=False, writable=False, merge_stderr=False)
    report["file_content"] = content.decode(errors="replace")
    # the check is about the pipeline (tool calls, sandbox, submission), not about the trailing newline
    report["passed"] = rc == 0 and report["file_content"].strip() == "hello" and report.get("exit", {}).get("exit_status") == "Submitted"
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, default=str))
    remove_tree(rootfs.parent)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
