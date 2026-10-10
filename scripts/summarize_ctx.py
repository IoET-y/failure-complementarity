#!/usr/bin/env python3
"""Context-transfer pilot summary (D-026): joins ctx_v1 with its primary-source experiment by task.

Per primary failure set F_A and rescuer B (incl. B = A), on the same Repo_t^A:
  R0     = P(B✓ | Repo_t^A)            V0 recovery (source experiment)
  Rnote  = P(B✓ | Repo_t^A + note)     note recovery (this experiment)
  C      = P(B✓ | Repo_0)              control: source experiment for B≠A, this experiment for B=A
  CTV    = Rnote − R0                  value of the handoff note
  FTV    = R0 − C,  FTV_note = Rnote − C
HRG decomposition (V0): R0(A→B) − R0(A→A) = [C(B) − C(A)] + [FTV(A→B) − FTV(A→A)], on tasks where all four are valid.

    python scripts/summarize_ctx.py --config configs/ctx_v1.yaml --tasks configs/tasks/calibration_v1.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys

from failure_complementarity.analysis.metrics import load_final_results, paired, solved, wilson
from failure_complementarity.config import load_experiment
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.runner.orchestrate import load_task_list


def rate(xs: dict) -> tuple[int, int]:
    v = [x for x in xs.values() if x is not None]
    return sum(v), len(v)


def fmt_rate(xs: dict) -> str:
    k, n = rate(xs)
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f}%, CI {100 * lo:.0f}–{100 * hi:.0f}%)"


def fmt_pair(p) -> str:
    if not p.n:
        return "n/a"
    lo, hi = p.diff_ci()
    return (f"{p.diff:+.2f} [{lo:+.2f}, {hi:+.2f}] (n={p.n}; x✓y✗={p.only_x}, x✗y✓={p.only_y}; "
            f"McNemar p={p.mcnemar_p:.3g})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--subset", choices=["hard", "nonhard"], help="restrict to one benchmark stratum")
    args = ap.parse_args()
    cfg = load_experiment(args.config)
    own = load_final_results(cfg.paths.runs_root / cfg.id)
    # every branch this experiment ran overrides the source's (replicates run all conditions themselves)
    src = load_final_results(cfg.paths.runs_root / cfg.primary_experiment) | own
    ids = load_task_list(args.tasks)
    if args.subset:
        ids = [t for t in ids if json.loads((cfg.paths.runs_root / cfg.id / t / "task.json").read_text())["subset"] == args.subset]
    A = cfg.agents
    out: dict = {"generated_at": utc_now(), "experiment": cfg.id, "primary_source": cfg.primary_experiment, "sets": {}}
    L = [f"# Context-transfer pilot — `{cfg.id}` (source `{cfg.primary_experiment}`)", "",
         f"Generated {out['generated_at']}. Same Repo_t^A for every condition; comparisons paired by task. "
         "Small pilot: counts and intervals, not claims.", ""]
    for a in A:
        F = [t for t in ids if (src.get((t, f"primary_{a}")) or {}).get("primary_failure")]
        ctrl = {b: {t: solved(src.get((t, f"control_{b}_repo0")) if b != a else own.get((t, f"control_{a}_repo0"))) for t in F} for b in A}
        r0 = {b: {t: solved(src.get((t, f"recovery_{a}_to_{b}"))) for t in F} for b in A}
        rn = {b: {t: solved(own.get((t, f"recovery_note_{a}_to_{b}"))) for t in F} for b in A}
        L += [f"## {a} failed (N = {len(F)})", "", "| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |",
              "|---|---|---|---|"]
        for b in A:
            L.append(f"| {b}{' (same model)' if b == a else ''} | {fmt_rate(r0[b])} | {fmt_rate(rn[b])} | {fmt_rate(ctrl[b])} |")
        L += ["", "| quantity | paired difference [95% Wald CI] |", "|---|---|"]
        entry: dict = {"n_failed": len(F), "tasks": F, "pairs": {}}
        for b in A:
            q = {"CTV": paired(rn[b], r0[b]), "FTV": paired(r0[b], ctrl[b]), "FTV_note": paired(rn[b], ctrl[b])}
            for name, p in q.items():
                L.append(f"| {name}_{a}→{b} | {fmt_pair(p)} |")
            entry["pairs"][b] = {k: v.to_dict() for k, v in q.items()} | {
                "R0": rate(r0[b]), "Rnote": rate(rn[b]), "control": rate(ctrl[b])}
        for b in A:
            if b == a:
                continue
            for label, R in (("V0", r0), ("note", rn)):
                T = [t for t in F if all(x[t] is not None for x in (R[b], R[a], ctrl[b], ctrl[a]))]
                if not T:
                    continue
                m = lambda d: sum(d[t] for t in T) / len(T)  # noqa: E731
                hrg, cap = m(R[b]) - m(R[a]), m(ctrl[b]) - m(ctrl[a])
                state = (m(R[b]) - m(ctrl[b])) - (m(R[a]) - m(ctrl[a]))
                L.append(f"| HRG_{a}→{b} ({label}) = capability/complementarity + state | {hrg:+.2f} = {cap:+.2f} + {state:+.2f} (n={len(T)}) |")
                entry["pairs"][b][f"HRG_decomposition_{label}"] = {"n": len(T), "HRG": hrg, "capability": cap, "state": state}
        out["sets"][a] = entry
        L.append("")
    notes = []
    for t in ids:
        for a in A:
            f = cfg.paths.runs_root / cfg.id / t / f"handoff_{a}" / "note.json"
            if f.exists():
                notes.append(json.loads(f.read_text()))
    if notes:
        L += ["## Handoff notes", "", f"{len(notes)} notes; median length "
              f"{sorted(len(n['note']) for n in notes)[len(notes) // 2]} chars; truncated conversations: "
              f"{sum(n['dropped_steps'] > 0 for n in notes)}; empty notes: {sum(not n['note'] for n in notes)}.", ""]
    L += ["CTV = note rescue − V0 rescue (value of the note); FTV = V0 rescue − Repo_0 control; "
          "FTV_note = note rescue − Repo_0 control. Wald CIs are rough at this n."]
    res_dir = cfg.paths.results_root / cfg.id / (args.subset or "")
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "ctx_table.md").write_text("\n".join(L) + "\n")
    (res_dir / "ctx.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {res_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
