#!/usr/bin/env python3
"""Per-model worker: runs every branch that needs model ``--agent``, stage by stage, with barriers on the other
models' progress. Each branch uses exactly one model (recovery A->B and control B need only B; Repo_t^A is a file
archive), so one job per model on its own GPUs is equivalent to one job serving all models (decision D-019).

Stages (protocol order; each waits for the previous one to be complete for ALL models):
  1. validation primaries  2. validation recovery  3. check_validation (stop everything on failure)
  4. calibration primaries (needs the committed frozen task list)  5. D-016 rule  6. calibration recovery

    python scripts/worker.py --agent qwen
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from failure_complementarity.benchmark.swebench_pro import load_tasks
from failure_complementarity.config import ExperimentConfig, load_experiment
from failure_complementarity.logging.structured import setup_logging
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.manifest import build_manifest, write_manifest
from failure_complementarity.runner.handoff_stage import generate_notes, wait_for_notes
from failure_complementarity.runner.orchestrate import execute, load_task_list, plan_primary, plan_recovery, prepare_all

ROOT = Path(__file__).resolve().parents[1]
POLL = 60


def branches_done(cfg: ExperimentConfig, plan) -> bool:
    exp = cfg.paths.runs_root / cfg.id
    return all((exp / tid / spec.name / "result.json").exists() for tid, spec in plan)


def task_list_committed(path: Path) -> bool:
    if not path.exists():
        return False
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", str(path)], capture_output=True).returncode == 0
    clean = not subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", str(path)], capture_output=True, text=True).stdout.strip()
    return tracked and clean


def run_script(*args: str) -> int:
    return subprocess.run([sys.executable, *args], cwd=ROOT).returncode


class Stage:
    def __init__(self, cfg_path: Path, tasks_path: Path, agent: str, log):
        self.cfg = load_experiment(cfg_path)
        self.tasks_path, self.agent, self.log = tasks_path, agent, log
        self.ids = load_task_list(tasks_path)
        all_tasks = load_tasks(self.cfg.paths.benchmark_repo, self.cfg.benchmark)
        write_manifest(self.cfg.paths.runs_root / self.cfg.id, build_manifest(self.cfg))
        self.ctxs = prepare_all(self.cfg, [all_tasks[t] for t in self.ids])

    def primary(self) -> None:
        plan = [(t, s) for t, s in plan_primary(self.cfg, self.ids) if s.agent == self.agent]
        self.log.info(f"[{self.cfg.id}] primaries for {self.agent}: {len(plan)} branches")
        execute(self.cfg, self.ctxs, plan)

    def wait_all_primaries(self) -> None:
        full = plan_primary(self.cfg, self.ids)
        while not branches_done(self.cfg, full):
            time.sleep(POLL)

    def recovery(self) -> None:
        plan, notes = plan_recovery(self.cfg, self.ctxs, self.ids)
        if self.cfg.conditions is not None and self.cfg.conditions.note:  # D-026/D-034: notes before note branches
            failures = [(n["task_id"], n["primary_agent"]) for n in notes if n["entered"]]
            generate_notes(self.cfg, self.ctxs, failures, self.agent, self.log)
            wait_for_notes(self.ctxs, failures, POLL)
        exp = self.cfg.paths.runs_root / self.cfg.id
        (exp / "recovery_plan.json").write_text(json.dumps(
            {"created_at": utc_now(), "definition": self.cfg.primary_failure.definition, "entries": notes,
             "branches": [[t, s.name] for t, s in plan]}, indent=2))
        mine = [(t, s) for t, s in plan if s.agent == self.agent]
        self.log.info(f"[{self.cfg.id}] recovery/control for {self.agent}: {len(mine)} of {len(plan)} branches")
        execute(self.cfg, self.ctxs, mine)
        while not branches_done(self.cfg, plan):  # barrier: other models' recovery branches
            time.sleep(POLL)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--val-config", default="configs/validation_v1.yaml")
    ap.add_argument("--val-tasks", default="configs/tasks/validation_v0.json")
    ap.add_argument("--cal-config", default="configs/pilot_v1.yaml")
    ap.add_argument("--cal-tasks", default="configs/tasks/calibration_v1.json")
    ap.add_argument("--gate-rule", default="v1", choices=["v0", "v1"])
    ap.add_argument("--skip-validation", action="store_true", help="only if validation already passed")
    ap.add_argument("--only-primaries", action="store_true", help="screening: run this model's primaries, then stop")
    args = ap.parse_args()
    VAL = (ROOT / args.val_config, ROOT / args.val_tasks)
    CAL = (ROOT / args.cal_config, ROOT / args.cal_tasks)
    log = setup_logging(ROOT / "runs" / "_slurm" / f"worker_{args.agent}_{utc_now().replace(':', '')}.log")

    if not args.skip_validation and not args.only_primaries:
        v = Stage(*VAL, args.agent, log)
        v.primary(); v.wait_all_primaries()
        v.recovery()
        run_script("scripts/summarize_results.py", "--config", str(VAL[0]), "--tasks", str(VAL[1]))
        if run_script("scripts/check_validation.py", "--config", str(VAL[0]), "--tasks", str(VAL[1])) != 0:
            log.error("validation failed: stopping before calibration")
            return 1

    while not task_list_committed(CAL[1]):
        log.info("waiting for the committed calibration task list (D-011)")
        time.sleep(POLL)
    c = Stage(*CAL, args.agent, log)
    if c.cfg.primary_source:  # replicate of another experiment: same primaries / failed workspaces (D-036)
        log.info(f"[{c.cfg.id}] primaries and start rule taken from {c.cfg.primary_source}")
        c.recovery()
        run_script("scripts/summarize_results.py", "--config", str(CAL[0]), "--tasks", str(CAL[1]))
        run_script("scripts/summarize_ctx.py", "--config", str(CAL[0]), "--tasks", str(CAL[1]))
        log.info("all stages done")
        return 0
    c.primary()
    if args.only_primaries:
        run_script("scripts/summarize_results.py", "--config", str(CAL[0]), "--tasks", str(CAL[1]))
        log.info("primaries done (screening mode)")
        return 0
    c.wait_all_primaries()
    run_script("scripts/summarize_results.py", "--config", str(CAL[0]), "--tasks", str(CAL[1]))
    if run_script("scripts/check_calibration_gate.py", "--config", str(CAL[0]), "--tasks", str(CAL[1]), "--rule", args.gate_rule) != 0:
        log.warning("D-016 rule not met: stopping before recovery for task-mix review")
        return 0
    c.recovery()
    run_script("scripts/summarize_results.py", "--config", str(CAL[0]), "--tasks", str(CAL[1]))
    if c.cfg.conditions is not None and c.cfg.conditions.note:
        run_script("scripts/summarize_ctx.py", "--config", str(CAL[0]), "--tasks", str(CAL[1]))
    log.info("all stages done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
