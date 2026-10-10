#!/usr/bin/env python3
"""Freeze the calibration task list (D-011): seeded order per stratum + runtime gate (D-003).

    python scripts/select_tasks.py --config configs/pilot.yaml --out configs/tasks/calibration_v0.json [--parallel 3]
    python scripts/select_tasks.py --config configs/pilot.yaml --dry-run      # print the candidate order only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from failure_complementarity.benchmark.gate import run_gate
from failure_complementarity.benchmark.swebench_pro import load_tasks
from failure_complementarity.benchmark.task_selection import select_tasks, stratum_order
from failure_complementarity.config import load_experiment
from failure_complementarity.logging.structured import setup_logging


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    log = setup_logging()
    cfg = load_experiment(args.config)
    tasks = load_tasks(cfg.paths.benchmark_repo, cfg.benchmark)
    ts = cfg.task_selection
    if args.dry_run:
        for s, n in (("hard", ts.n_hard), ("nonhard", ts.n_nonhard)):
            print(s, stratum_order(tasks, s, ts.seed)[: n + 5])
        return 0

    def gate(tid: str) -> dict:
        r = run_gate(cfg, tasks[tid])
        log.info(f"gate {tid}: passed={r.get('passed')} {r.get('reason') or ''}")
        return r

    record = select_tasks(tasks, seed=ts.seed, n_hard=ts.n_hard, n_nonhard=ts.n_nonhard, gate=gate, parallel=args.parallel)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} exists: the task list is frozen; a new list needs a new file and a decisions.md entry")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2))
    log.info(f"selected {len(record['task_ids'])} tasks -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
