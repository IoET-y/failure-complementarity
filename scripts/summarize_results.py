#!/usr/bin/env python3
"""Write calibration.csv / calibration_report.md and (if recovery ran) recovery_table.md + recovery.json.

    python scripts/summarize_results.py --config configs/pilot.yaml --tasks configs/tasks/calibration_v0.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter

from failure_complementarity.analysis.metrics import (
    calibration_rows,
    load_final_results,
    paired,
    recovery_analysis,
    solved,
    wilson,
)
from failure_complementarity.config import load_experiment
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.runner.orchestrate import load_task_list


def pct(x: float) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.0f}%"


def ci(t) -> str:
    return "n/a" if any(math.isnan(v) for v in t) else f"[{100 * t[0]:.0f}%, {100 * t[1]:.0f}%]"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--subset", choices=["hard", "nonhard"], help="restrict to one benchmark stratum")
    args = ap.parse_args()
    cfg = load_experiment(args.config)
    exp_dir = cfg.paths.runs_root / cfg.id
    out_dir = cfg.paths.results_root / cfg.id
    out_dir.mkdir(parents=True, exist_ok=True)
    task_ids = load_task_list(args.tasks)
    if args.subset:
        task_ids = [t for t in task_ids if json.loads((exp_dir / t / "task.json").read_text())["subset"] == args.subset]
        out_dir = out_dir / args.subset
        out_dir.mkdir(parents=True, exist_ok=True)
    meta = {t: json.loads((exp_dir / t / "task.json").read_text()) for t in task_ids if (exp_dir / t / "task.json").exists()}
    if cfg.primary_source:
        # recovery tables must only use this experiment's branches; drop the source's non-primary branches
        own_keys = set(load_final_results(exp_dir))
        results = {k: v for k, v in results.items() if k in own_keys or k[1].startswith("primary_")}
    results = load_final_results(exp_dir)
    if cfg.primary_source:  # replicate: primaries live in the source experiment
        results = load_final_results(cfg.paths.runs_root / cfg.primary_source) | results
    A = cfg.agents

    # ---- calibration
    rows = calibration_rows(results, meta, A)
    with open(out_dir / "calibration.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    L = [f"# Calibration report — `{cfg.id}`", "", f"Generated {utc_now()} from `runs/{cfg.id}`. Tasks: {len(task_ids)} "
         f"(frozen list `{args.tasks}`). Budget: {cfg.budgets.primary.wallclock_minutes:g} min / "
         f"{cfg.budgets.primary.step_limit} steps per run. All runs reported; none removed.", "",
         "## Solve rates (primary runs from Repo_0)", "", "| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |",
         "|---|---|---|---|---|---|"]
    for a in A:
        for sub in ("hard", "nonhard", "all"):
            ts = [t for t in meta if sub == "all" or meta[t]["subset"] == sub]
            vals = [solved(results.get((t, f"primary_{a}"))) for t in ts]
            v = [x for x in vals if x is not None]
            L.append(f"| {a} | {sub} | {sum(v)} / {len(v)} | {pct(sum(v) / len(v) if v else math.nan)} | "
                     f"{ci(wilson(sum(v), len(v)))} | {len(ts) - len(v)} |")
    L += ["", "## Exit reasons and primary-failure counts", ""]
    for a in A:
        rs = [results.get((t, f"primary_{a}")) or {} for t in meta]
        L.append(f"- **{a}**: statuses {dict(Counter(r.get('status', 'MISSING') for r in rs))}; exit reasons "
                 f"{dict(Counter(r.get('exit_reason', 'MISSING') for r in rs))}; primary failures "
                 f"(`{cfg.primary_failure.definition}`): {sum(bool(r.get('primary_failure')) for r in rs)}")
    if len(A) == 2:
        x, y = A
        p = paired({t: solved(results.get((t, f'primary_{x}'))) for t in meta},
                   {t: solved(results.get((t, f'primary_{y}'))) for t in meta})
        L += ["", f"## Paired outcomes ({x} vs {y})", "", f"| | {y} ✓ | {y} ✗ |", "|---|---|---|",
              f"| **{x} ✓** | {p.both} | {p.only_x} |", f"| **{x} ✗** | {p.only_y} | {p.neither} |", "",
              f"Exact McNemar p = {p.mcnemar_p:.3g} (n = {p.n}). Calibration is not meant to rank models (protocol §3)."]
    L += ["", "## Steps, time, tokens (median over valid runs)", "", "| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |", "|---|---|---|---|---|---|"]
    for a in A:
        rs = [r for t in meta if (r := results.get((t, f"primary_{a}"))) and solved(r) is not None]
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else "n/a"  # noqa: E731
        L.append(f"| {a} | {med([r['stats']['n_steps'] for r in rs])} | {med([r['agent_seconds'] for r in rs])} | "
                 f"{med([r['usage']['total_tokens'] for r in rs if r.get('usage')])} | "
                 f"{sum(r['exit_reason'] == 'STEP_LIMIT' for r in rs)} | {sum(r['exit_reason'] == 'PRIMARY_TIMEOUT' for r in rs)} |")
    L += ["", "Target from the protocol: each model solves roughly 20%–70% of the tasks (§3)."]
    (out_dir / "calibration_report.md").write_text("\n".join(L) + "\n")

    # ---- recovery (if any recovery branch exists)
    if any(b.startswith("recovery_") for (_, b) in results):
        rec = recovery_analysis(results, task_ids, A)
        (out_dir / "recovery.json").write_text(json.dumps(rec, indent=2, default=str))
        T = [f"# Recovery table — `{cfg.id}`", "", f"Generated {utc_now()}. Primary failure definition: "
             f"`{cfg.primary_failure.definition}`. Rates over valid branches (infra failures excluded and counted).", "",
             "| Primary failure | Same-model rescue | Cross-model rescue | Repo0 control |", "|---|---|---|---|"]
        for a in A:
            for b in A:
                if b == a:
                    continue
                same, cross = rec["pairs"][f"{a}->{a}"], rec["pairs"][f"{a}->{b}"]
                c = cross["control_repo0"]
                T.append(f"| {a} failed (N={len(rec[f'failed_{a}'])}) | {a}: {same['R']['k']} / {same['R']['n']} | "
                         f"{b}: {cross['R']['k']} / {cross['R']['n']} | {b}: {c['k']} / {c['n']} |")
        T += ["", "| quantity | estimate | paired n | 2×2 (x✓y✓, x✓y✗, x✗y✓, x✗y✗) | exact McNemar p |", "|---|---|---|---|---|"]
        for k, e in rec["pairs"].items():
            T.append(f"| R_{k} | {pct(e['R']['rate'])} {ci(e['R']['ci95_wilson'])} | {e['R']['n']} | | |")
        for k, e in rec["pairs"].items():
            for q in ("HRG", "FTV"):
                if q in e:
                    d = e[q]
                    T.append(f"| {q}_{k} | {d['diff']:+.2f} | {d['n']} | ({d['x_and_y']}, {d['x_only']}, {d['y_only']}, {d['neither']}) | {d['mcnemar_exact_p']:.3g} |")
        T += ["", "HRG_{A→B} = R_{A→B} − R_{A→A} (x = cross-model, y = same-model); FTV_{A→B} = P(B✓|Repo_t^A) − P(B✓|Repo_0) "
              "(x = rescue on failed workspace, y = Repo_0 control). Small-sample pilot: report counts, not claims."]
        (out_dir / "recovery_table.md").write_text("\n".join(T) + "\n")
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
