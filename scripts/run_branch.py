#!/usr/bin/env python3
"""Run one branch of one task (resumable; a finished branch is not rerun).

    python scripts/run_branch.py --config configs/pilot.yaml --task <instance_id> --branch primary:qwen
    python scripts/run_branch.py ... --branch recovery:qwen:devstral   # devstral on Repo_t^qwen
    python scripts/run_branch.py ... --branch control:devstral:qwen    # devstral on Repo_0 (control for qwen failures)
"""

from __future__ import annotations

import argparse
import json
import sys

from failure_complementarity.benchmark.swebench_pro import load_tasks
from failure_complementarity.config import load_experiment
from failure_complementarity.logging.structured import setup_logging
from failure_complementarity.manifest import build_manifest, write_manifest
from failure_complementarity.runner.branch import control_branch, prepare_task, primary_branch, recovery_branch, run_branch


def parse_branch(text: str, agents: list[str]):
    kind, *names = text.split(":")
    if any(n not in agents for n in names):
        raise SystemExit(f"unknown agent in {text!r}; experiment agents: {agents}")
    if kind == "primary" and len(names) == 1:
        return primary_branch(names[0])
    if kind == "recovery" and len(names) == 2:
        return recovery_branch(names[0], names[1])
    if kind == "control" and len(names) == 2:
        return control_branch(names[0], names[1])
    raise SystemExit(f"bad --branch {text!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--branch", required=True, action="append")
    args = ap.parse_args()
    log = setup_logging()
    cfg = load_experiment(args.config)
    write_manifest(cfg.paths.runs_root / cfg.id, build_manifest(cfg))
    task = load_tasks(cfg.paths.benchmark_repo, cfg.benchmark)[args.task]
    ctx = prepare_task(cfg, task)
    for b in args.branch:
        res = run_branch(ctx, parse_branch(b, cfg.agents))
        log.info(json.dumps({k: res.get(k) for k in ("branch", "status", "exit_reason", "eval_status", "outcome_class",
                                                    "agent_seconds", "final_attempt")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
