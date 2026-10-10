#!/usr/bin/env python3
"""Per-model worker for the context-transfer experiment (D-026).

    python scripts/worker_ctx.py --agent qwen [--config configs/ctx_v1.yaml --tasks configs/tasks/calibration_v1.json]

1. handoff notes for this model's own source failures (needs this model's endpoint);
2. barrier: notes of all models exist;
3. this model's note-rescue and same-model control branches;
4. barrier: all branches done; summary.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

from failure_complementarity.agents.handoff import generate_note
from failure_complementarity.benchmark.swebench_pro import load_tasks
from failure_complementarity.config import load_experiment
from failure_complementarity.logging.structured import setup_logging
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.manifest import build_manifest, write_manifest
from failure_complementarity.runner.branch import handoff_dir, primary_dir
from failure_complementarity.runner.orchestrate import execute, failures_in_source, load_task_list, plan_ctx, prepare_all

ROOT = Path(__file__).resolve().parents[1]
POLL = 60


def note_path(ctx, a) -> Path:
    return handoff_dir(ctx, a) / "note.md"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", default="configs/ctx_v1.yaml")
    ap.add_argument("--tasks", default="configs/tasks/calibration_v1.json")
    args = ap.parse_args()
    log = setup_logging(ROOT / "runs" / "_slurm" / f"worker_ctx_{args.agent}_{utc_now().replace(':', '')}.log")
    cfg = load_experiment(ROOT / args.config)
    write_manifest(cfg.paths.runs_root / cfg.id, build_manifest(cfg))
    ids = load_task_list(ROOT / args.tasks)
    all_tasks = load_tasks(cfg.paths.benchmark_repo, cfg.benchmark)
    ctxs = prepare_all(cfg, [all_tasks[t] for t in ids])
    failures = failures_in_source(cfg, ctxs, ids)
    request = cfg.prompt_path("handoff_request").read_text().strip()
    spec = cfg.agent(args.agent)

    mine = [(t, a) for t, a in failures if a == args.agent]
    log.info(f"[{cfg.id}] handoff notes for {args.agent}: {len(mine)} (of {len(failures)} failures)")
    for tid, a in mine:
        out = handoff_dir(ctxs[tid], a)
        if (out / "note.md").exists():
            continue
        res = json.loads((primary_dir(ctxs[tid], a) / "result.json").read_text())
        traj = primary_dir(ctxs[tid], a) / res["final_attempt"] / "mini_trajectory.json"
        for attempt in range(1 + cfg.infra_retries):
            try:
                rec = generate_note(spec, traj, request, max_model_len=spec.serve.max_model_len)
                break
            except Exception as e:  # noqa: BLE001 - endpoint problems: retry, then stop loudly
                log.error(f"note {tid} {a} attempt {attempt + 1}: {e}\n{traceback.format_exc()}")
                time.sleep(30)
        else:
            raise RuntimeError(f"could not generate handoff note for {tid} {a}")
        out.mkdir(parents=True, exist_ok=True)
        rec.update(task_id=tid, primary_agent=a, model=spec.model, source_trajectory=str(traj),
                   request_sha256=__import__("hashlib").sha256(request.encode()).hexdigest(), created_at=utc_now())
        (out / "note.json").write_text(json.dumps(rec, indent=2))
        (out / "note.md").write_text(rec["note"] + "\n")
        log.info(f"note {tid[:50]} {a}: {len(rec['note'])} chars, dropped_steps={rec['dropped_steps']}")

    while not all(note_path(ctxs[t], a).exists() for t, a in failures):
        time.sleep(POLL)

    plan = plan_ctx(cfg, ctxs, ids)
    (cfg.paths.runs_root / cfg.id / "ctx_plan.json").write_text(json.dumps(
        {"created_at": utc_now(), "failures": failures, "branches": [[t, s.name] for t, s in plan]}, indent=2))
    own = [(t, s) for t, s in plan if s.agent == args.agent]
    log.info(f"[{cfg.id}] branches for {args.agent}: {len(own)} of {len(plan)}")
    execute(cfg, ctxs, own)
    exp = cfg.paths.runs_root / cfg.id
    while not all((exp / t / s.name / "result.json").exists() for t, s in plan):
        time.sleep(POLL)
    subprocess.run([sys.executable, "scripts/summarize_ctx.py", "--config", args.config, "--tasks", args.tasks], cwd=ROOT)
    log.info("ctx: all stages done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
