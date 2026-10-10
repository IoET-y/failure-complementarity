"""Handoff-note stage (D-026): A's own model writes one note per primary failure of A, before any note branch runs."""

from __future__ import annotations

import hashlib
import json
import os
import logging
import time
import traceback
from pathlib import Path

from failure_complementarity.agents.handoff import generate_note
from failure_complementarity.config import ExperimentConfig
from failure_complementarity.logging.trajectory import utc_now
from failure_complementarity.runner.branch import TaskContext, handoff_dir, primary_dir


def note_path(ctx: TaskContext, primary_agent: str) -> Path:
    return handoff_dir(ctx, primary_agent) / "note.md"


def generate_notes(cfg: ExperimentConfig, ctxs: dict[str, TaskContext], failures: list[tuple[str, str]],
                   agent: str, log: logging.Logger) -> None:
    """Notes for this agent's own failures (needs this agent's endpoint). Idempotent."""
    request = cfg.prompt_path("handoff_request").read_text().strip()
    spec = cfg.agent(agent)
    mine = [(t, a) for t, a in failures if a == agent]
    log.info(f"[{cfg.id}] handoff notes for {agent}: {len(mine)} (of {len(failures)} failures)")
    for tid, a in mine:
        out = handoff_dir(ctxs[tid], a)
        if (out / "note.md").exists():
            continue
        src = cfg.paths.runs_root / cfg.primary_experiment / tid / out.name
        if cfg.primary_source and (src / "note.md").exists():  # replicate: same note as the source experiment
            out.mkdir(parents=True, exist_ok=True)
            for f in ("note.json", "note.md"):
                if not (out / f).exists():
                    os.link(src / f, out / f)
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
                   request_sha256=hashlib.sha256(request.encode()).hexdigest(), created_at=utc_now())
        (out / "note.json").write_text(json.dumps(rec, indent=2))
        (out / "note.md").write_text(rec["note"] + "\n")
        log.info(f"note {tid[:50]} {a}: {len(rec['note'])} chars, dropped_steps={rec['dropped_steps']}")


def wait_for_notes(ctxs: dict[str, TaskContext], failures: list[tuple[str, str]], poll: int = 60) -> None:
    while not all(note_path(ctxs[t], a).exists() for t, a in failures):
        time.sleep(poll)
