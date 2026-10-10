"""Protocol §9 metrics from final branch results. The task is the unit; all comparisons are paired by task.

Only branches with a valid outcome (SUCCESS / TASK_FAILURE) enter rates; INFRA_FAILURE branches are counted and
reported separately, never as failures (integrity rule 8). A paired comparison uses the tasks where BOTH branches
are valid.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID = {"SUCCESS", "TASK_FAILURE"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b (x✓y✗) and c (x✗y✓)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def load_final_results(exp_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """(task_id, branch) -> final result.json."""
    out = {}
    for f in sorted(Path(exp_dir).glob("*/*/result.json")):
        r = json.loads(f.read_text())
        out[(f.parent.parent.name, f.parent.name)] = r
    return out


def solved(r: dict[str, Any] | None) -> bool | None:
    if r is None or r.get("outcome_class") not in VALID:
        return None
    return r["outcome_class"] == "SUCCESS"


@dataclass
class Paired:
    n: int
    both: int
    only_x: int
    only_y: int
    neither: int

    @property
    def rate_x(self) -> float:
        return (self.both + self.only_x) / self.n if self.n else math.nan

    @property
    def rate_y(self) -> float:
        return (self.both + self.only_y) / self.n if self.n else math.nan

    @property
    def diff(self) -> float:
        return self.rate_x - self.rate_y

    def diff_ci(self, z: float = 1.96) -> tuple[float, float]:
        """Wald CI for a paired difference of proportions (rough at small n; reported for orientation only)."""
        if not self.n:
            return (math.nan, math.nan)
        n, b, c = self.n, self.only_x, self.only_y
        d = (b - c) / n
        se = math.sqrt(max(0.0, (b + c) / n - d * d) / n)
        return (d - z * se, d + z * se)

    @property
    def mcnemar_p(self) -> float:
        return mcnemar_exact(self.only_x, self.only_y)

    def to_dict(self) -> dict[str, Any]:
        return {"n": self.n, "x_and_y": self.both, "x_only": self.only_x, "y_only": self.only_y,
                "neither": self.neither, "rate_x": self.rate_x, "rate_y": self.rate_y, "diff": self.diff,
                "diff_ci95_wald": self.diff_ci(), "mcnemar_exact_p": self.mcnemar_p}


def paired(xs: dict[str, bool | None], ys: dict[str, bool | None]) -> Paired:
    tasks = [t for t in xs if t in ys and xs[t] is not None and ys[t] is not None]
    return Paired(
        n=len(tasks),
        both=sum(xs[t] and ys[t] for t in tasks),
        only_x=sum(xs[t] and not ys[t] for t in tasks),
        only_y=sum((not xs[t]) and ys[t] for t in tasks),
        neither=sum((not xs[t]) and (not ys[t]) for t in tasks),
    )


# --------------------------------------------------------------------------- calibration


def calibration_rows(results: dict, task_meta: dict[str, dict], agents: list[str]) -> list[dict[str, Any]]:
    rows = []
    for tid, meta in task_meta.items():
        row: dict[str, Any] = {"task_id": tid, "subset": meta["subset"]}
        for a in agents:
            r = results.get((tid, f"primary_{a}"))
            s = solved(r)
            row[f"{a}_solved"] = "" if s is None else int(s)
            row[f"{a}_time"] = (r or {}).get("agent_seconds", "")
            row[f"{a}_tokens"] = ((r or {}).get("usage") or {}).get("total_tokens", "")
            row[f"{a}_steps"] = ((r or {}).get("stats") or {}).get("n_steps", "")
            row[f"{a}_status"] = (r or {}).get("status", "MISSING")
            row[f"{a}_exit_reason"] = (r or {}).get("exit_reason", "")
            row[f"{a}_primary_failure"] = "" if r is None or r.get("primary_failure") is None else int(r["primary_failure"])
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- recovery


def recovery_analysis(results: dict, task_ids: list[str], agents: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"pairs": {}}
    for a in agents:
        failed = [t for t in task_ids if (results.get((t, f"primary_{a}")) or {}).get("primary_failure")]
        out[f"failed_{a}"] = failed
        rec = {b: {t: solved(results.get((t, f"recovery_{a}_to_{b}"))) for t in failed} for b in agents}
        for b in agents:
            entry: dict[str, Any] = {"primary": a, "rescuer": b, "n_failed": len(failed)}
            vals = [v for v in rec[b].values() if v is not None]
            k = sum(vals)
            entry["R"] = {"k": k, "n": len(vals), "rate": k / len(vals) if vals else math.nan,
                          "ci95_wilson": wilson(k, len(vals)), "n_infra_or_missing": len(failed) - len(vals)}
            if b != a:
                entry["HRG"] = paired(rec[b], rec[a]).to_dict()        # x = cross-model, y = same-model restart
                ctrl = {t: solved(results.get((t, f"control_{b}_repo0"))) for t in failed}
                cv = [v for v in ctrl.values() if v is not None]
                entry["control_repo0"] = {"k": sum(cv), "n": len(cv), "rate": sum(cv) / len(cv) if cv else math.nan,
                                          "ci95_wilson": wilson(sum(cv), len(cv))}
                entry["FTV"] = paired(rec[b], ctrl).to_dict()          # x = B on Repo_t^A, y = B on Repo_0
            out["pairs"][f"{a}->{b}"] = entry
    return out
