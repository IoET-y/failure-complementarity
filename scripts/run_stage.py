#!/usr/bin/env python3
"""Run one stage of an experiment over a frozen task list (resumable).

    python scripts/run_stage.py --config configs/pilot.yaml --tasks configs/tasks/calibration_v0.json --stage primary
    python scripts/run_stage.py --config configs/pilot.yaml --tasks configs/tasks/calibration_v0.json --stage recovery
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from failure_complementarity.benchmark.swebench_pro import load_tasks
from failure_complementarity.config import load_experiment
from failure_complementarity.logging.structured import setup_logging
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.manifest import build_manifest, write_manifest
from failure_complementarity.runner.orchestrate import execute, load_task_list, plan_primary, plan_recovery, prepare_all


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--stage", required=True, choices=["primary", "recovery"])
    args = ap.parse_args()
    cfg = load_experiment(args.config)
    exp_dir = cfg.paths.runs_root / cfg.id
    log = setup_logging(exp_dir / "logs" / f"stage_{args.stage}_{utc_now().replace(':', '')}.log")
    write_manifest(exp_dir, build_manifest(cfg))
    all_tasks = load_tasks(cfg.paths.benchmark_repo, cfg.benchmark)
    task_ids = load_task_list(args.tasks)
    (exp_dir / "task_list.json").write_text(json.dumps({"source": args.tasks, "task_ids": task_ids}, indent=2))
    ctxs = prepare_all(cfg, [all_tasks[t] for t in task_ids])
    if args.stage == "primary":
        plan = plan_primary(cfg, task_ids)
    else:
        plan, notes = plan_recovery(cfg, ctxs, task_ids)
        (exp_dir / "recovery_plan.json").write_text(json.dumps(
            {"created_at": utc_now(), "definition": cfg.primary_failure.definition, "entries": notes,
             "branches": [[t, s.name] for t, s in plan]}, indent=2))
    log.info(f"stage {args.stage}: {len(plan)} branches over {len(task_ids)} tasks")
    results = execute(cfg, ctxs, plan)
    log.info(f"stage {args.stage} finished: {dict(Counter(r.get('status') for r in results))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
