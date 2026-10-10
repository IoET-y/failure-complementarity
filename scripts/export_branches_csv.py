#!/usr/bin/env python3
"""Export one row per final branch result of the given experiments to a CSV (the raw run directories are too large to
publish: container snapshots, full trajectories). All published analyses can be recomputed from this file.

    python scripts/export_branches_csv.py --out results/data/branches.csv pilot_v0 pilot_v1 ...
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["experiment", "task_id", "subset", "branch", "phase", "agent", "primary_agent", "context", "status",
          "exit_reason", "eval_status", "outcome_class", "primary_failure", "n_attempts", "agent_seconds", "n_steps",
          "n_format_errors", "n_files_edited", "prompt_tokens", "completion_tokens", "total_tokens", "final_diff_bytes"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("experiments", nargs="+")
    args = ap.parse_args()
    rows = []
    for e in args.experiments:
        for f in sorted((ROOT / "runs" / e).glob("*/*/result.json")):
            r = json.loads(f.read_text())
            task = f.parent.parent.name
            meta = json.loads((f.parent.parent / "task.json").read_text())
            st, us = r.get("stats") or {}, r.get("usage") or {}
            rows.append({
                "experiment": e, "task_id": task, "subset": meta["subset"], "branch": r["branch"], "phase": r["phase"],
                "agent": r["agent"], "primary_agent": r.get("primary_agent") or "", "context": r.get("context", "none"),
                "status": r["status"], "exit_reason": r["exit_reason"], "eval_status": r["eval_status"],
                "outcome_class": r["outcome_class"],
                "primary_failure": "" if r.get("primary_failure") is None else int(r["primary_failure"]),
                "n_attempts": r.get("n_attempts", 1), "agent_seconds": r.get("agent_seconds", ""),
                "n_steps": st.get("n_steps", ""), "n_format_errors": st.get("n_format_errors", ""),
                "n_files_edited": len(st.get("files_edited", [])) if st else "",
                "prompt_tokens": us.get("prompt_tokens", ""), "completion_tokens": us.get("completion_tokens", ""),
                "total_tokens": us.get("total_tokens", ""), "final_diff_bytes": r.get("final_diff_bytes", ""),
            })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
