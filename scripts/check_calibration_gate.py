#!/usr/bin/env python3
"""Pre-registered recovery start rules: D-016 (v0) and D-023 (v1). Exit 0 = start recovery, 3 = stop for review."""

from __future__ import annotations

import argparse
import json
import sys

from failure_complementarity.analysis.metrics import load_final_results, solved
from failure_complementarity.config import load_experiment
from failure_complementarity.runner.orchestrate import load_task_list

MAX_INFRA, LOW, HIGH, MIN_FAILURES = 2, 0.20, 0.70, 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--rule", choices=["v0", "v1"], default="v0")
    args = ap.parse_args()
    cfg = load_experiment(args.config)
    exp = cfg.paths.runs_root / cfg.id
    results = load_final_results(exp)
    tids = load_task_list(args.tasks)
    verdict = {"rule": "D-016" if args.rule == "v0" else "D-023", "models": {}, "proceed": True}
    for a in cfg.agents:
        rs = [results.get((t, f"primary_{a}")) for t in tids]
        vals = [solved(r) for r in rs if r is not None]
        valid = [v for v in vals if v is not None]
        infra = len(tids) - len(valid)
        rate = sum(valid) / len(valid) if valid else 0.0
        fails = sum(bool((r or {}).get("primary_failure")) for r in rs)
        if args.rule == "v0":
            ok = infra <= MAX_INFRA and LOW <= rate <= HIGH and fails >= MIN_FAILURES
        else:  # D-023
            ok = infra <= 0.10 * len(tids) and fails >= 5
        verdict["models"][a] = {"valid": len(valid), "infra_or_missing": infra, "solve_rate": rate,
                                "primary_failures": fails, "ok": ok}
        verdict["proceed"] &= ok
    (exp / "calibration_gate.json").write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["proceed"] else 3


if __name__ == "__main__":
    sys.exit(main())
