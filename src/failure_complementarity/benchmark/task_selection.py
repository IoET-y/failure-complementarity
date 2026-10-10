"""Outcome-blind task selection (decision D-011).

Each stratum (HARD-51, non-HARD V2) is shuffled with the recorded seed; tasks are taken in that order, keeping
those that pass the runtime gate (D-003), until the quota is met. No model outcome is involved at any point, so
the order of gate checks cannot bias the selection; the full ordered list and every gate verdict are recorded.
"""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from failure_complementarity.benchmark.swebench_pro import Task
from failure_complementarity.logging.trajectory import utc_now


def stratum_order(tasks: dict[str, Task], subset: str, seed: int) -> list[str]:
    ids = sorted(t.instance_id for t in tasks.values() if t.subset == subset)
    random.Random(f"{seed}:{subset}").shuffle(ids)
    return ids


def select_stratum(order: list[str], n: int, gate: Callable[[str], dict[str, Any]], parallel: int = 1) -> tuple[list[str], list[dict]]:
    """First ``n`` ids in ``order`` that pass ``gate``. Gates run ``parallel`` at a time, in order; the result is
    identical to a sequential walk because only a prefix of ``order`` is ever considered."""
    selected: list[str] = []
    verdicts: list[dict] = []
    i = 0
    while len(selected) < n and i < len(order):
        window = order[i : i + max(1, min(parallel, n - len(selected)))]
        with ThreadPoolExecutor(len(window)) as ex:
            results = list(ex.map(gate, window))
        for tid, r in zip(window, results):
            verdicts.append({"instance_id": tid, "passed": bool(r.get("passed")), "reason": r.get("reason")})
            if r.get("passed") and len(selected) < n:
                selected.append(tid)
        i += len(window)
    if len(selected) < n:
        raise RuntimeError(f"only {len(selected)} of {n} tasks passed the gate")
    return selected, verdicts


def select_tasks(tasks: dict[str, Task], *, seed: int, n_hard: int, n_nonhard: int,
                 gate: Callable[[str], dict[str, Any]], parallel: int = 1) -> dict[str, Any]:
    record: dict[str, Any] = {"rule": "D-011", "seed": seed, "created_at": utc_now(), "strata": {}}
    for subset, n in (("hard", n_hard), ("nonhard", n_nonhard)):
        order = stratum_order(tasks, subset, seed)
        selected, verdicts = select_stratum(order, n, gate, parallel)
        record["strata"][subset] = {"n": n, "order": order, "gate_verdicts": verdicts, "selected": selected}
    record["task_ids"] = [t for s in ("hard", "nonhard") for t in record["strata"][s]["selected"]]
    return record
