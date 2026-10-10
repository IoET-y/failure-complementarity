"""Stage scheduling over a frozen task list.

* ``primary``  — every agent on Repo_0 of every task (Phase-0 calibration runs = the primary runs).
* ``recovery`` — for every task where agent A had a *primary failure* (§4, D-009): A→X recovery for every agent X
  (incl. A itself) and the Repo_0 control X for every X≠A.

Each agent has its own worker pool of ``runtime.max_concurrent_per_endpoint`` workers (D-013); every pool walks
the tasks in the same order. Branches are resumable, so a stage can be re-invoked after an interruption.
"""

from __future__ import annotations

import json
import logging
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from failure_complementarity.benchmark.swebench_pro import Task
from failure_complementarity.config import ExperimentConfig
from failure_complementarity.logging.schema import OutcomeClass
from failure_complementarity.runner.branch import (
    BranchBusy,
    BranchSpec,
    TaskContext,
    control_branch,
    prepare_task,
    primary_branch,
    recovery_branch,
    run_branch,
)

log = logging.getLogger("fc.orchestrate")


def load_task_list(path: Path) -> list[str]:
    return list(json.loads(Path(path).read_text())["task_ids"])


def prepare_all(cfg: ExperimentConfig, tasks: list[Task], parallel: int = 4) -> dict[str, TaskContext]:
    with ThreadPoolExecutor(parallel) as ex:
        ctxs = list(ex.map(lambda t: prepare_task(cfg, t), tasks))
    return {c.task.instance_id: c for c in ctxs}


def plan_primary(cfg: ExperimentConfig, task_ids: list[str]) -> list[tuple[str, BranchSpec]]:
    return [(tid, primary_branch(a)) for tid in task_ids for a in cfg.agents]


def plan_recovery(cfg: ExperimentConfig, ctxs: dict[str, TaskContext], task_ids: list[str]) -> tuple[list[tuple[str, BranchSpec]], list[dict]]:
    """Branches for every primary failure of A (per ``cfg.conditions``; default = V0 design: recovery by every model
    and Repo_0 controls of the other models). Also returns why other (task, agent) pairs are not entered."""
    from failure_complementarity.runner.branch import primary_dir, recovery_note_branch

    cond = cfg.conditions
    plan: list[tuple[str, BranchSpec]] = []
    notes: list[dict] = []
    for tid in task_ids:
        for a in cfg.agents:
            f = primary_dir(ctxs[tid], a) / "result.json"
            if not f.exists():
                notes.append({"task_id": tid, "primary_agent": a, "entered": False, "reason": "primary not finished"})
                continue
            r = json.loads(f.read_text())
            if r["outcome_class"] == OutcomeClass.INFRA_FAILURE.value:
                notes.append({"task_id": tid, "primary_agent": a, "entered": False, "reason": f"primary infra failure ({r['status']})"})
                continue
            if not r.get("primary_failure"):
                notes.append({"task_id": tid, "primary_agent": a, "entered": False,
                              "reason": f"not a primary failure (status={r['status']}, exit={r['exit_reason']})"})
                continue
            notes.append({"task_id": tid, "primary_agent": a, "entered": True, "reason": r["status"]})
            if cond is None or cond.v0:
                plan += [(tid, recovery_branch(a, x)) for x in cfg.agents]
            if cond is not None and cond.note:
                plan += [(tid, recovery_note_branch(a, x)) for x in cfg.agents]
            same = cond is not None and cond.controls == "both"
            plan += [(tid, control_branch(x, a)) for x in cfg.agents if x != a or same]
    # one Repo_0 control per (task, model): several failures on a task share it (it does not depend on A)
    seen: set[tuple[str, str]] = set()
    unique = []
    for tid, spec in plan:
        if (tid, spec.name) not in seen:
            seen.add((tid, spec.name))
            unique.append((tid, spec))
    return unique, notes


def execute(cfg: ExperimentConfig, ctxs: dict[str, TaskContext], plan: list[tuple[str, BranchSpec]]) -> list[dict[str, Any]]:
    pools = {a: ThreadPoolExecutor(cfg.runtime.max_concurrent_per_endpoint, thread_name_prefix=f"pool-{a}")
             for a in cfg.agents}
    futures: list[tuple[str, BranchSpec, Future]] = []

    def _run(tid: str, spec: BranchSpec) -> dict[str, Any]:
        try:
            res = run_branch(ctxs[tid], spec)
            log.info(f"done {tid} {spec.name}: {res.get('status')} ({res.get('exit_reason')}, {res.get('eval_status')})")
            return res
        except BranchBusy:
            log.info(f"skip {tid} {spec.name}: running in another worker")
            return {"task_id": tid, "branch": spec.name, "status": "BUSY_ELSEWHERE"}
        except Exception as e:  # noqa: BLE001 - a bug in one branch must not stop the others; it is recorded
            log.error(f"branch crashed {tid} {spec.name}: {e}\n{traceback.format_exc()}")
            return {"task_id": tid, "branch": spec.name, "status": "RUNNER_CRASH", "error": str(e)}

    for tid, spec in plan:
        futures.append((tid, spec, pools[spec.agent].submit(_run, tid, spec)))
    results = [f.result() for _, _, f in futures]
    for p in pools.values():
        p.shutdown()
    return results


# --------------------------------------------------------------------------- context transfer (D-026)


def failures_in_source(cfg: ExperimentConfig, ctxs: dict[str, TaskContext], task_ids: list[str]) -> list[tuple[str, str]]:
    """(task_id, A) for every primary failure of A in the primary-source experiment."""
    from failure_complementarity.runner.branch import primary_dir

    out = []
    for tid in task_ids:
        for a in cfg.agents:
            f = primary_dir(ctxs[tid], a) / "result.json"
            if f.exists():
                r = json.loads(f.read_text())
                if r["outcome_class"] != OutcomeClass.INFRA_FAILURE.value and r.get("primary_failure"):
                    out.append((tid, a))
    return out


def plan_ctx(cfg: ExperimentConfig, ctxs: dict[str, TaskContext], task_ids: list[str]) -> list[tuple[str, BranchSpec]]:
    """For each source failure of A: note-rescue by every model (incl. A) + same-model Repo_0 control of A."""
    from failure_complementarity.runner.branch import recovery_note_branch

    plan: list[tuple[str, BranchSpec]] = []
    for tid, a in failures_in_source(cfg, ctxs, task_ids):
        plan += [(tid, recovery_note_branch(a, x)) for x in cfg.agents]
        plan.append((tid, control_branch(a, a)))
    return plan
