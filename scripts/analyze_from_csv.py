#!/usr/bin/env python3
"""Recompute every headline number of the write-up from ``results/data/branches.csv`` (no raw runs needed).

    python scripts/analyze_from_csv.py [--csv results/data/branches.csv] [--json results/data/headline_numbers.json]
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ("devstral", "glm47flash")
REPS = ("pilot_v2", "pilot_v2_r2", "pilot_v2_r3")
SCREEN_MODELS = {"qwen": "pilot_v1", "devstral": "pilot_v1", "qwen36moe": "screen_v1", "qwen36dense": "screen_v1",
                 "glm47flash": "screen_v1", "gptoss120b": "screen_v1", "nemotron3nano": "screen_v1"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar(b: int, c: int) -> float:
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def cluster_bootstrap(by_task: dict[str, list[float]], b: int = 5000, seed: int = 0) -> tuple[float, float, float]:
    """Mean over all observations; 95% CI resampling *tasks* (the unit of analysis) with replacement."""
    tasks = sorted(by_task)
    stat = lambda ts: sum(d for t in ts for d in by_task[t]) / sum(len(by_task[t]) for t in ts)  # noqa: E731
    rng = random.Random(seed)
    bs = sorted(stat([rng.choice(tasks) for _ in tasks]) for _ in tasks and range(b))
    return stat(tasks), bs[int(0.025 * b)], bs[int(0.975 * b) - 1]


def load(path: Path):
    rows = list(csv.DictReader(open(path)))
    solved = {}
    for r in rows:
        if r["outcome_class"] in ("SUCCESS", "TASK_FAILURE"):
            solved[(r["experiment"], r["task_id"], r["branch"])] = r["outcome_class"] == "SUCCESS"
    return rows, solved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "results/data/branches.csv"))
    ap.add_argument("--json", default=str(ROOT / "results/data/headline_numbers.json"))
    args = ap.parse_args()
    rows, S = load(Path(args.csv))
    out: dict = {}

    # ---- 1. screening: 40 non-HARD tasks, primary runs
    v1_tasks = sorted({r["task_id"] for r in rows if r["experiment"] == "screen_v1"})
    prim = {m: {t: S.get((e, t, f"primary_{m}")) for t in v1_tasks} for m, e in SCREEN_MODELS.items()}
    out["screening"] = {}
    for m, d in prim.items():
        v = [x for x in d.values() if x is not None]
        lo, hi = wilson(sum(v), len(v))
        out["screening"][m] = {"solved": sum(v), "n": len(v), "ci95": [lo, hi]}
    out["screening_pairs"] = {}
    for a, b in itertools.combinations(["qwen", "devstral", "qwen36moe", "qwen36dense", "glm47flash"], 2):
        T = [t for t in v1_tasks if prim[a][t] is not None and prim[b][t] is not None]
        n10 = sum(prim[a][t] and not prim[b][t] for t in T)
        n01 = sum(prim[b][t] and not prim[a][t] for t in T)
        n11 = sum(prim[a][t] and prim[b][t] for t in T)
        out["screening_pairs"][f"{a}|{b}"] = {"n": len(T), "both": n11, "only_a": n10, "only_b": n01,
                                              "neither": len(T) - n11 - n10 - n01, "mcnemar_p": mcnemar(n10, n01)}

    # ---- 2. pilot_v2 primaries by stratum
    sub = {r["task_id"]: r["subset"] for r in rows if r["experiment"] == "pilot_v2"}
    ids = sorted(sub)
    out["pilot_v2_primary"] = {}
    for a in A:
        d = {t: S.get(("pilot_v2", t, f"primary_{a}")) for t in ids}
        out["pilot_v2_primary"][a] = {
            s: [sum(bool(d[t]) for t in ids if (s == "all" or sub[t] == s)), sum(1 for t in ids if s == "all" or sub[t] == s)]
            for s in ("all", "hard", "nonhard")}
    prim_fail = {a: [t for t in ids if (t_ := S.get(("pilot_v2", t, f"primary_{a}"))) is not None and not t_] for a in A}
    out["pilot_v2_failures"] = {a: len(v) for a, v in prim_fail.items()}
    both = {t: [S.get(("pilot_v2", t, f"primary_{a}")) for a in A] for t in ids}
    out["pilot_v2_pair_2x2"] = {"both": sum(all(v) for v in both.values()),
                                "only_devstral": sum(v[0] and not v[1] for v in both.values()),
                                "only_glm": sum(v[1] and not v[0] for v in both.values()),
                                "neither": sum(not v[0] and not v[1] for v in both.values())}

    # ---- 3. pooled recovery table
    def per_task(branch: str, tasks: list[str], subset: str | None = None) -> dict[str, float]:
        res = {}
        for t in tasks:
            if subset and sub[t] != subset:
                continue
            v = [S[(e, t, branch)] for e in REPS if (e, t, branch) in S]
            if v:
                res[t] = sum(v) / len(v)
        return res

    out["pilot_v2_pooled"] = {}
    for subset in (None, "hard", "nonhard"):
        key = subset or "all"
        out["pilot_v2_pooled"][key] = {}
        for a in A:
            o = [x for x in A if x != a][0]
            F = prim_fail[a]
            conds = {}
            for b in A:
                conds[f"V0 {a}->{b}"] = f"recovery_{a}_to_{b}"
                conds[f"note {a}->{b}"] = f"recovery_note_{a}_to_{b}"
                conds[f"Repo0 {b}"] = f"control_{b}_repo0"
            tab = {}
            for name, br in conds.items():
                runs = [S[(e, t, br)] for t in F if (not subset or sub[t] == subset) for e in REPS if (e, t, br) in S]
                per_rep = []
                for e in REPS:
                    v = [S[(e, t, br)] for t in F if (not subset or sub[t] == subset) and (e, t, br) in S]
                    per_rep.append([sum(v), len(v)])
                lo, hi = wilson(sum(runs), len(runs))
                tab[name] = {"k": sum(runs), "n": len(runs), "rate": sum(runs) / len(runs) if runs else math.nan,
                             "per_replicate": per_rep}
            out["pilot_v2_pooled"][key][a] = {"n_failed_tasks": len([t for t in F if not subset or sub[t] == subset]), "table": tab}

    # ---- 4. contrasts (per-task means over replicates, cluster bootstrap over tasks)
    out["contrasts"] = {}
    for subset in (None, "hard", "nonhard"):
        key = subset or "all"
        comb = {"FTV": defaultdict(list), "CTV": defaultdict(list), "HRG_V0": defaultdict(list), "HRG_note": defaultdict(list)}
        res = {}
        for a in A:
            o = [x for x in A if x != a][0]
            F = prim_fail[a]
            P = lambda br: per_task(br, F, subset)  # noqa: E731
            V0 = {b: P(f"recovery_{a}_to_{b}") for b in A}
            NT = {b: P(f"recovery_note_{a}_to_{b}") for b in A}
            C = {b: P(f"control_{b}_repo0") for b in A}

            def diff(x: dict, y: dict) -> dict[str, list[float]]:
                return {t: [x[t] - y[t]] for t in x if t in y}
            sets = {
                f"HRG_V0 {a}->{o}": diff(V0[o], V0[a]), f"HRG_note {a}->{o}": diff(NT[o], NT[a]),
                f"FTV {a}->{a}": diff(V0[a], C[a]), f"FTV {a}->{o}": diff(V0[o], C[o]),
                f"CTV {a}->{a}": diff(NT[a], V0[a]), f"CTV {a}->{o}": diff(NT[o], V0[o]),
            }
            for name, d in sets.items():
                if not d:
                    continue
                m, lo, hi = cluster_bootstrap(d)
                pos, neg = sum(v[0] > 0 for v in d.values()), sum(v[0] < 0 for v in d.values())
                res[name] = {"mean": m, "ci95": [lo, hi], "n_tasks": len(d), "tasks_pos": pos, "tasks_neg": neg,
                             "sign_test_p": mcnemar(pos, neg)}
            for b in A:
                for t, v in diff(V0[b], C[b]).items():
                    comb["FTV"][t] += v
                for t, v in diff(NT[b], V0[b]).items():
                    comb["CTV"][t] += v
            for t, v in diff(V0[o], V0[a]).items():
                comb["HRG_V0"][t] += v
            for t, v in diff(NT[o], NT[a]).items():
                comb["HRG_note"][t] += v
        for name, d in comb.items():
            if d:
                m, lo, hi = cluster_bootstrap(dict(d))
                res[f"COMBINED {name}"] = {"mean": m, "ci95": [lo, hi], "n_tasks": len(d)}
        out["contrasts"][key] = res

    # ---- 5. earlier experiments (pilot_v1: Qwen3-Coder-30B vs Devstral; ctx_v1)
    v1 = {}
    qt = sorted({r["task_id"] for r in rows if r["experiment"] == "pilot_v1"})
    for a in ("qwen", "devstral"):
        F = [t for t in qt if S.get(("pilot_v1", t, f"primary_{a}")) is False]
        o = "devstral" if a == "qwen" else "qwen"
        g = lambda br: [S.get(("pilot_v1", t, br)) for t in F]  # noqa: E731
        cnt = lambda xs: [sum(bool(x) for x in xs if x is not None), sum(x is not None for x in xs)]  # noqa: E731
        v1[a] = {"n_failed": len(F), f"V0 {a}->{a}": cnt(g(f"recovery_{a}_to_{a}")), f"V0 {a}->{o}": cnt(g(f"recovery_{a}_to_{o}")),
                 f"Repo0 {o}": cnt(g(f"control_{o}_repo0"))}
    out["pilot_v1"] = v1

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("screening", "pilot_v2_primary", "pilot_v2_failures", "pilot_v2_pair_2x2")}, indent=1))
    for k in ("COMBINED FTV", "COMBINED CTV", "COMBINED HRG_V0", "COMBINED HRG_note"):
        c = out["contrasts"]["all"][k]
        print(f"{k:20s} {c['mean']:+.3f}  [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]  ({c['n_tasks']} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
