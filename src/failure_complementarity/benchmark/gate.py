"""Runtime validity gate (decision D-003): under OUR runtime the gold patch must solve the task and the empty
patch must not. Depends only on task + image + runtime (never on any model), so results are cached per task
in ``<runs_root>/_gate/``.
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from failure_complementarity.benchmark.images import ensure_sif
from failure_complementarity.benchmark.swebench_pro import Task
from failure_complementarity.config import ExperimentConfig
from failure_complementarity.fsutil import remove_tree
from failure_complementarity.logging.schema import EvalStatus
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.runner.evaluator import evaluate_patch

GATE_VERSION = 1


def gate_dir(cfg: ExperimentConfig) -> Path:
    return cfg.paths.runs_root / "_gate"


def run_gate(cfg: ExperimentConfig, task: Task, *, force: bool = False) -> dict[str, Any]:
    out = gate_dir(cfg) / task.instance_id
    result_file = out / "gate.json"
    if result_file.exists() and not force:
        return json.loads(result_file.read_text())
    out.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {"instance_id": task.instance_id, "subset": task.subset, "gate_version": GATE_VERSION,
                              "started_at": utc_now()}
    try:
        sif, image_info = ensure_sif(task.image, task.instance_id, cfg.paths.sif_cache, cfg.paths.apptainer_cache)
        record["image"] = image_info
    except Exception as e:  # image could not be obtained: excluded, reason recorded
        record.update(passed=False, reason=f"image: {type(e).__name__}: {e}"[:2000], finished_at=utc_now())
        result_file.write_text(json.dumps(record, indent=2))
        return record
    work = cfg.paths.work_root / "_gate" / task.instance_id
    try:
        gold = evaluate_patch(task, task.gold_patch.read_bytes(), sif, out / "gold", work,
                              cfg.budgets.evaluator_timeout_seconds)
        empty = evaluate_patch(task, b"", sif, out / "empty", work, cfg.budgets.evaluator_timeout_seconds)
    finally:
        remove_tree(work)
    record["gold"], record["empty"] = gold.to_dict(), empty.to_dict()
    record["passed"] = gold.status is EvalStatus.SOLVED and empty.status is EvalStatus.UNSOLVED
    if not record["passed"]:
        record["reason"] = f"gold={gold.status.value} empty={empty.status.value}"
    record["finished_at"] = utc_now()
    result_file.write_text(json.dumps(record, indent=2))
    return record
