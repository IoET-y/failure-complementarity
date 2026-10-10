#!/usr/bin/env python3
"""Milestone 2/4 acceptance checks on a finished validation experiment. Exit 1 on any violated invariant.

Checks: every branch has a valid (non-infra) outcome and a 0/1 evaluator reward; every primary starts from the
Repo_0 tree hash; every recovery branch starts from exactly its primary's checkpoint hash; every control starts
from Repo_0; rescue prompts are exactly the standardized recovery text (no trajectory content); all branches of a
task ran in distinct work directories.
"""

from __future__ import annotations

import argparse
import json
import sys

from failure_complementarity.benchmark.swebench_pro import load_tasks
from failure_complementarity.config import load_experiment
from failure_complementarity.runner.branch import build_task_text
from failure_complementarity.runner.orchestrate import load_task_list


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--tasks", required=True)
    args = ap.parse_args()
    cfg = load_experiment(args.config)
    tasks = load_tasks(cfg.paths.benchmark_repo, cfg.benchmark)
    exp = cfg.paths.runs_root / cfg.id
    problems, notes = [], []
    for tid in load_task_list(args.tasks):
        tdir = exp / tid
        pristine = json.loads((tdir / "pristine" / "metadata.json").read_text())["tree_hash"]
        work_dirs = set()
        for bdir in sorted(p for p in tdir.iterdir() if p.is_dir() and (p / "result.json").exists()):
            r = json.loads((bdir / "result.json").read_text())
            att = bdir / r["final_attempt"]
            tag = f"{tid[:40]}…/{bdir.name}"
            if r["outcome_class"] == "INFRA_FAILURE":
                problems.append(f"{tag}: infra failure {r['status']}: {r.get('exception', {}).get('message', '')[:300]}")
                continue
            if (r.get("eval") or {}).get("reward") not in (0, 1):
                problems.append(f"{tag}: no evaluator reward")
            if r["work_dir"] in work_dirs:
                problems.append(f"{tag}: work dir reused")
            work_dirs.add(r["work_dir"])
            start = r["start_state"]["tree_hash"]
            if bdir.name.startswith(("primary_", "control_")) and start != pristine:
                problems.append(f"{tag}: start hash {start[:12]} != Repo_0 {pristine[:12]}")
            if bdir.name.startswith("recovery_"):
                a = r["primary_agent"]  # (incl. recovery_note_*: same checkpoint, note-bearing prompt)
                pr = json.loads((tdir / f"primary_{a}" / "result.json").read_text())
                ck = pr["checkpoint"]["tree_hash"]
                if start != ck:
                    problems.append(f"{tag}: start hash {start[:12]} != checkpoint {ck[:12]}")
                if start == pristine:
                    notes.append(f"{tag}: failed workspace identical to Repo_0 (primary made no change)")
                if r.get("context") == "note":
                    note = (tdir / f"handoff_{a}" / "note.md").read_text()
                    expected = build_task_text(cfg, tasks[tid], "recovery_note", note=note)
                else:
                    expected = build_task_text(cfg, tasks[tid], "recovery")
                if (att / "task_prompt.md").read_text() != expected:
                    problems.append(f"{tag}: recovery prompt differs from the standardized text")
            notes.append(f"{tag}: {r['status']} exit={r['exit_reason']} steps={r.get('stats', {}).get('n_steps')} "
                         f"tokens={(r.get('usage') or {}).get('total_tokens')} start={start[:12]}")
        recs = [p.name for p in tdir.iterdir() if p.name.startswith("recovery_")]
        notes.append(f"{tid[:40]}…: recovery branches run: {sorted(recs) or 'none (no primary failure)'}")
    print("\n".join(notes))
    if problems:
        print("\nVALIDATION FAILED:\n" + "\n".join(problems))
        return 1
    print("\nVALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
