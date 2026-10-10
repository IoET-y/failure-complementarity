#!/usr/bin/env python3
"""Pool replicate experiments of the same recovery design (D-036) and compare conditions at the task level.

For every primary failure set F_A and every condition, each task has one outcome per replicate. Rates are
reported per replicate and pooled; contrasts are computed on per-task means (paired by task), with a bootstrap
over tasks (tasks are the unit; replicates of a task are not independent units) and an exact sign test on the
tasks whose per-task mean differs.

    python scripts/analyze_replicates.py --base pilot_v2 --replicates pilot_v2_r2 pilot_v2_r3 \
        --tasks configs/tasks/calibration_v2.json [--subset hard|nonhard] [--out results/pilot_v2_pooled]
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from failure_complementarity.analysis.metrics import load_final_results, solved

ROOT = Path(__file__).resolve().parents[1]


def sign_test(pos: int, neg: int) -> float:
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def boot_ci(diffs: list[float], b: int = 10000, seed: int = 0) -> tuple[float, float]:
    if not diffs:
        return (math.nan, math.nan)
    rng = random.Random(seed)
    n = len(diffs)
    ms = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(b))
    return ms[int(0.025 * b)], ms[int(0.975 * b) - 1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--replicates", nargs="*", default=[])
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--subset", choices=["hard", "nonhard"])
    ap.add_argument("--agents", nargs=2, default=["devstral", "glm47flash"])
    ap.add_argument("--out")
    args = ap.parse_args()
    runs = ROOT / "runs"
    exps = [args.base, *args.replicates]
    res = {e: load_final_results(runs / e) for e in exps}
    base = res[args.base]
    ids = json.loads((ROOT / args.tasks).read_text())["task_ids"]
    if args.subset:
        ids = [t for t in ids if json.loads((runs / args.base / t / "task.json").read_text())["subset"] == args.subset]
    A = args.agents
    out: dict = {"experiments": exps, "subset": args.subset, "sets": {}}
    L = [f"# Pooled replicates — {', '.join(exps)}" + (f" ({args.subset})" if args.subset else ""), "",
         f"{len(exps)} replicate(s) per task × condition on identical failed workspaces and notes. Rates: per replicate and "
         "pooled. Contrasts: per-task mean difference, bootstrap 95% CI over tasks, exact sign test over tasks.", ""]

    def outcomes(t: str, branch: str) -> list[bool]:
        return [v for e in exps if (v := solved(res[e].get((t, branch)))) is not None]

    for a in A:
        F = [t for t in ids if (base.get((t, f"primary_{a}")) or {}).get("primary_failure")]
        conds = {}
        for b in A:
            same = " (same)" if b == a else ""
            conds[f"V0 {a}→{b}{same}"] = f"recovery_{a}_to_{b}"
            conds[f"note {a}→{b}{same}"] = f"recovery_note_{a}_to_{b}"
            conds[f"Repo0 {b}{same}"] = f"control_{b}_repo0"
        per_task = {name: {t: outcomes(t, br) for t in F} for name, br in conds.items()}
        L += [f"## {a} failed (N = {len(F)} tasks)", "", "| condition | " + " | ".join(exps) + " | pooled |",
              "|---|" + "---|" * (len(exps) + 1)]
        entry: dict = {"n_tasks": len(F), "rates": {}, "contrasts": {}}
        for name, br in conds.items():
            cells = []
            for e in exps:
                v = [x for t in F if (x := solved(res[e].get((t, br)))) is not None]
                cells.append(f"{sum(v)}/{len(v)}" if v else "–")
            allv = [x for t in F for x in per_task[name][t]]
            pooled = sum(allv) / len(allv) if allv else math.nan
            entry["rates"][name] = {"per_replicate": cells, "pooled": pooled, "n_runs": len(allv)}
            L.append(f"| {name} | " + " | ".join(cells) + f" | {100 * pooled:.1f}% ({sum(allv)}/{len(allv)}) |")
        o = [x for x in A if x != a][0]
        contrasts = {
            f"HRG {a}→{o} (V0)": (f"V0 {a}→{o}", f"V0 {a}→{a} (same)"),
            f"HRG {a}→{o} (note)": (f"note {a}→{o}", f"note {a}→{a} (same)"),
            f"FTV {a}→{a} (same)": (f"V0 {a}→{a} (same)", f"Repo0 {a} (same)"),
            f"FTV {a}→{o}": (f"V0 {a}→{o}", f"Repo0 {o}"),
            f"CTV {a}→{a} (same)": (f"note {a}→{a} (same)", f"V0 {a}→{a} (same)"),
            f"CTV {a}→{o}": (f"note {a}→{o}", f"V0 {a}→{o}"),
            f"capability {o} vs {a} on F_{a}": (f"Repo0 {o}", f"Repo0 {a} (same)"),
        }
        L += ["", "| contrast (x − y) | mean per-task diff | 95% bootstrap CI | tasks x>y / x<y | sign-test p | per replicate |",
              "|---|---|---|---|---|---|"]
        for cname, (x, y) in contrasts.items():
            diffs, pos, neg = [], 0, 0
            for t in F:
                vx, vy = per_task[x][t], per_task[y][t]
                if vx and vy:
                    d = sum(vx) / len(vx) - sum(vy) / len(vy)
                    diffs.append(d)
                    pos += d > 0
                    neg += d < 0
            mean = sum(diffs) / len(diffs) if diffs else math.nan
            lo, hi = boot_ci(diffs)
            reps = []
            for e in exps:
                bx, by = conds[x], conds[y]
                pairs = [(solved(res[e].get((t, bx))), solved(res[e].get((t, by)))) for t in F]
                pairs = [(p, q) for p, q in pairs if p is not None and q is not None]
                reps.append(f"{(sum(p for p, _ in pairs) - sum(q for _, q in pairs)) / len(pairs):+.2f}" if pairs else "–")
            p = sign_test(pos, neg)
            entry["contrasts"][cname] = {"mean": mean, "ci95": [lo, hi], "n_tasks": len(diffs), "pos": pos, "neg": neg,
                                         "sign_p": p, "per_replicate": reps}
            L.append(f"| {cname} | {mean:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {pos} / {neg} | {p:.3g} | {', '.join(reps)} |")
        out["sets"][a] = entry
        L.append("")
    L.append("HRG = cross-model − same-model rescue on the same Repo_t^A; FTV = rescue on Repo_t^A − Repo_0 control; "
             "CTV = with handoff note − without. Exploratory; many contrasts are reported, so single p-values are not evidence.")
    dest = Path(args.out) if args.out else ROOT / "results" / f"{args.base}_pooled" / (args.subset or "")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "pooled_table.md").write_text("\n".join(L) + "\n")
    (dest / "pooled.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
