"""One experimental branch = one fresh agent on one start state, evaluated by the official protocol.

Branches of a task (protocol §5):
    primary_<A>                     A on Repo_0, primary prompt, primary budget
    recovery_<A>_to_<B>             B on Repo_t^A (restored checkpoint), recovery prompt, recovery budget (B may be A)
    recovery_note_<A>_to_<B>        as above + A's handoff note (context transfer, D-026)
    control_<B>_repo0               B on Repo_0, primary prompt, recovery budget (decision D-010; B = A allowed, D-026)

Every attempt starts from a freshly materialised, hash-verified start state in its own directory and container;
nothing is shared between branches except the read-only SIF and the read-only checkpoint archive.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import logging
import socket
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from failure_complementarity.agents.miniswe import (
    ApptainerEnvironment,
    ContextLimitExceeded,
    ModelEndpointError,
    RecordingAgent,
    build_model,
    load_miniswe_config,
)
from failure_complementarity.analysis.run_stats import compute_run_stats
from failure_complementarity.benchmark.gate import gate_dir
from failure_complementarity.benchmark.images import ensure_sif
from failure_complementarity.benchmark.swebench_pro import Task
from failure_complementarity.checkpoint.restore import restore_checkpoint
from failure_complementarity.checkpoint.snapshot import WorkspaceCheckpoint, create_checkpoint
from failure_complementarity.config import ExperimentConfig, sha256_file
from failure_complementarity.fsutil import remove_tree
from failure_complementarity.logging.schema import (
    EvalStatus,
    EventType,
    ExitReason,
    OutcomeClass,
    Phase,
    classify,
    is_primary_failure,
)
from failure_complementarity.logging.structured import JsonFormatter
from failure_complementarity.logging.trajectory import TrajectoryWriter, read_trajectory, utc_now
from failure_complementarity.manifest import git_info, package_versions
from failure_complementarity.runner.evaluator import evaluate_patch
from failure_complementarity.runner.sandbox import Instance, SandboxError, detect_repo_dir, unpack_sif
from failure_complementarity.runner.workspace import capture_state, git_head

CHECKPOINT_SUBDIR = "checkpoint"


# --------------------------------------------------------------------------- branch definitions


@dataclass(frozen=True)
class BranchSpec:
    name: str
    phase: Phase
    agent: str
    primary_agent: str | None = None   # whose failed workspace (recovery) / whose failure triggered it (control)
    context: str = "none"              # "none" (V0) or "note" (handoff note, D-026)

    @property
    def from_checkpoint(self) -> bool:
        return self.phase is Phase.RECOVERY

    @property
    def prompt_kind(self) -> str:
        if self.phase is not Phase.RECOVERY:
            return "primary"
        return "recovery_note" if self.context == "note" else "recovery"


def primary_branch(agent: str) -> BranchSpec:
    return BranchSpec(f"primary_{agent}", Phase.PRIMARY, agent)


def recovery_branch(primary_agent: str, rescuer: str) -> BranchSpec:
    return BranchSpec(f"recovery_{primary_agent}_to_{rescuer}", Phase.RECOVERY, rescuer, primary_agent)


def recovery_note_branch(primary_agent: str, rescuer: str) -> BranchSpec:
    return BranchSpec(f"recovery_note_{primary_agent}_to_{rescuer}", Phase.RECOVERY, rescuer, primary_agent, "note")


def control_branch(rescuer: str, primary_agent: str) -> BranchSpec:
    return BranchSpec(f"control_{rescuer}_repo0", Phase.CONTROL, rescuer, primary_agent)


def handoff_dir(ctx: "TaskContext", primary_agent: str) -> Path:
    return ctx.task_dir / f"handoff_{primary_agent}"


# --------------------------------------------------------------------------- task context


class TaskNotEligible(RuntimeError):
    pass


@dataclass
class TaskContext:
    cfg: ExperimentConfig
    task: Task
    sif: Path
    image_info: dict[str, Any]
    task_dir: Path
    pristine: dict[str, Any]


def prepare_task(cfg: ExperimentConfig, task: Task) -> TaskContext:
    """Image + Repo_0 facts (base commit, repo dir, tree hash). Refuses tasks that did not pass the gate."""
    gate_file = gate_dir(cfg) / task.instance_id / "gate.json"
    if not gate_file.exists() or not json.loads(gate_file.read_text()).get("passed"):
        raise TaskNotEligible(f"{task.instance_id} has not passed the runtime gate (D-003)")
    sif, image_info = ensure_sif(task.image, task.instance_id, cfg.paths.sif_cache, cfg.paths.apptainer_cache)
    task_dir = cfg.paths.runs_root / cfg.id / task.instance_id
    task_dir.mkdir(parents=True, exist_ok=True)
    if not (task_dir / "task.json").exists():
        (task_dir / "task.json").write_text(json.dumps(task.to_dict(), indent=2))
    pristine_dir = task_dir / "pristine"
    meta_file = pristine_dir / "metadata.json"
    with open(task_dir / ".prepare.lock", "w") as lock:  # several per-model jobs may prepare the same task
        fcntl.lockf(lock, fcntl.LOCK_EX)  # POSIX lock: cluster-wide on GPFS
        pristine = _ensure_pristine(cfg, task, sif, image_info, task_dir, pristine_dir, meta_file)
    if cfg.primary_source:  # D-026: this experiment's Repo_0 must be exactly the source experiment's Repo_0
        src = json.loads((cfg.paths.runs_root / cfg.primary_source / task.instance_id / "pristine" / "metadata.json").read_text())
        if src["tree_hash"] != pristine["tree_hash"] or src["base_commit"] != pristine["base_commit"]:
            raise TaskNotEligible(f"{task.instance_id}: Repo_0 differs from {cfg.primary_source}")
    return TaskContext(cfg, task, sif, image_info, task_dir, pristine)


def _ensure_pristine(cfg, task, sif, image_info, task_dir, pristine_dir, meta_file) -> dict[str, Any]:
    if not meta_file.exists() and cfg.primary_source:
        # D-026: reuse the source experiment's Repo_0 archive byte-for-byte (hard links, no copy)
        src = cfg.paths.runs_root / cfg.primary_source / task.instance_id / "pristine"
        if not (src / "metadata.json").exists():
            raise TaskNotEligible(f"{task.instance_id}: no Repo_0 archive in {cfg.primary_source}")
        remove_tree(pristine_dir)
        shutil.copytree(src, pristine_dir, copy_function=os.link)
    if meta_file.exists():
        pristine = json.loads(meta_file.read_text())
        if pristine["image_digest"] != image_info["digest"]:
            raise TaskNotEligible(f"{task.instance_id}: image digest changed since this task was started")
    else:
        # Repo_0 is materialised ONCE and archived; every Repo_0 branch restores this exact archive (unpacking the
        # SIF per branch is not byte-reproducible: apptainer stamps a build date into /.singularity.d/labels.json).
        probe = cfg.paths.work_root / cfg.id / task.instance_id / "pristine_probe"
        remove_tree(probe)
        remove_tree(pristine_dir)
        try:
            unpack_sif(sif, probe)
            repo_dir = detect_repo_dir(probe)
            base_commit = git_head(probe, repo_dir)
            # P0: uncommitted state the image itself ships (e.g. a redis appendonlydir/ in /app); part of Repo_0 (D-024)
            cap = capture_state(probe, repo_dir, base_commit, probe.parent / "pristine_capture")
            create_checkpoint(probe, pristine_dir, task_id=task.instance_id, base_commit=base_commit,
                              repo_dir=repo_dir, git_diff=cap.diff, git_status=cap.status,
                              extra={"kind": "Repo_0", "image": task.image, "image_digest": image_info["digest"],
                                     "sif_sha256": image_info["sif_sha256"], "base_patch_bytes": len(cap.diff)})
        finally:
            remove_tree(probe)
        pristine = json.loads(meta_file.read_text())
    return pristine


def build_task_text(cfg: ExperimentConfig, task: Task, kind: str, note: str | None = None) -> str:
    """The text substituted for {{task}} in the official instance template. Same for every model."""
    instruction = task.instruction
    if kind == "primary":
        return instruction
    if kind == "recovery_note":
        if note is None:
            raise ValueError("recovery_note prompt needs the handoff note")
        preamble = cfg.prompt_path("recovery_note_preamble").read_text().strip()
        return (f"{preamble}\n\n## Handoff note from the previous agent\n\n<handoff_note>\n{note}\n</handoff_note>"
                f"\n\n## Original task\n\n{instruction}")
    preamble = cfg.prompt_path("recovery_preamble").read_text().strip()
    return f"{preamble}\n\n## Original task\n\n{instruction}"


# --------------------------------------------------------------------------- running


def _branch_logger(path: Path, name: str) -> logging.Logger:
    log = logging.getLogger(f"fc.branch.{name}.{id(path)}")
    log.setLevel(logging.INFO)
    log.propagate = True
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(JsonFormatter())
    log.addHandler(fh)
    return log


def _server_version(base_url: str) -> str | None:
    root = base_url.rstrip("/").removesuffix("/v1")
    try:
        r = httpx.get(f"{root}/version", timeout=10)
        return r.json().get("version") if r.status_code == 200 else None
    except Exception:
        return None


def _exit_reason(phase: Phase, extra: dict | None, exc: BaseException | None, watchdog: bool) -> ExitReason:
    timeout = ExitReason.PRIMARY_TIMEOUT if phase is Phase.PRIMARY else ExitReason.RECOVERY_TIMEOUT
    if watchdog:
        return timeout
    if exc is not None:
        if isinstance(exc, ContextLimitExceeded):
            return ExitReason.CONTEXT_LIMIT
        if isinstance(exc, ModelEndpointError):
            return ExitReason.MODEL_ERROR
        if isinstance(exc, SandboxError):
            return ExitReason.CONTAINER_ERROR
        return ExitReason.HARNESS_ERROR
    return {
        "Submitted": ExitReason.SUBMITTED,
        "TimeExceeded": timeout,
        "LimitsExceeded": ExitReason.STEP_LIMIT,
        "RepeatedFormatError": ExitReason.FORMAT_ERROR_LIMIT,
    }.get((extra or {}).get("exit_status"), ExitReason.HARNESS_ERROR)


def primary_dir(ctx: TaskContext, primary_agent: str) -> Path:
    """A's primary branch directory (in the primary-source experiment if one is configured, D-026)."""
    return ctx.cfg.paths.runs_root / ctx.cfg.primary_experiment / ctx.task.instance_id / primary_branch(primary_agent).name


def checkpoint_dir(ctx: TaskContext, primary_agent: str) -> Path:
    """Repo_t^A: the checkpoint of A's final primary attempt."""
    res = json.loads((primary_dir(ctx, primary_agent) / "result.json").read_text())
    return primary_dir(ctx, primary_agent) / res["final_attempt"] / CHECKPOINT_SUBDIR


class BranchBusy(RuntimeError):
    """Another worker (possibly on another node) is running this branch right now."""


def run_branch(ctx: TaskContext, spec: BranchSpec) -> dict[str, Any]:
    """Resumable: a branch with a final result.json is never rerun. INFRA failures are retried (D-012).

    A cluster-wide POSIX lock on the branch directory lets several workers of the same model share a plan
    without ever running the same branch twice (D-035); the lock disappears if its holder dies."""
    bdir = ctx.task_dir / spec.name
    final = bdir / "result.json"
    if final.exists():
        return json.loads(final.read_text())
    bdir.mkdir(parents=True, exist_ok=True)
    lock = open(bdir / ".running.lock", "w")
    try:
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise BranchBusy(f"{spec.name} is being run by another worker")
    try:
        if final.exists():  # finished by another worker between the check and the lock
            return json.loads(final.read_text())
        return _run_branch_locked(ctx, spec, bdir, final)
    finally:
        lock.close()


def _run_branch_locked(ctx: TaskContext, spec: BranchSpec, bdir: Path, final: Path) -> dict[str, Any]:
    max_attempts = 1 + ctx.cfg.infra_retries
    while True:
        attempts = sorted(bdir.glob("attempt_*"), key=lambda p: int(p.name.split("_")[1]))
        for a in attempts:  # an attempt without result.json was interrupted (e.g. job killed): infra, keep it
            if not (a / "result.json").exists():
                (a / "result.json").write_text(json.dumps({
                    "run_id": f"{ctx.cfg.id}/{ctx.task.instance_id}/{spec.name}/{a.name}", "attempt": int(a.name.split("_")[1]),
                    "exit_reason": ExitReason.HARNESS_ERROR.value, "eval_status": EvalStatus.NOT_EVALUATED.value,
                    "outcome_class": OutcomeClass.INFRA_FAILURE.value, "status": ExitReason.HARNESS_ERROR.value,
                    "exception": {"type": "Interrupted", "message": "attempt directory without result (runner died)"},
                    "recorded_at": utc_now()}, indent=2))
                remove_tree(ctx.cfg.paths.work_root / ctx.cfg.id / ctx.task.instance_id / spec.name / a.name)
        if attempts:
            last = json.loads((attempts[-1] / "result.json").read_text())
            if last["outcome_class"] != OutcomeClass.INFRA_FAILURE.value or len(attempts) >= max_attempts:
                last["final_attempt"] = attempts[-1].name
                last["n_attempts"] = len(attempts)
                final.write_text(json.dumps(last, indent=2))
                return last
        run_attempt(ctx, spec, bdir / f"attempt_{len(attempts) + 1}")


def run_attempt(ctx: TaskContext, spec: BranchSpec, adir: Path) -> dict[str, Any]:
    cfg, task = ctx.cfg, ctx.task
    adir.mkdir(parents=True)
    work = cfg.paths.work_root / cfg.id / task.instance_id / spec.name / adir.name
    rootfs = work / "rootfs"
    log = _branch_logger(adir / "stdout.log", spec.name)
    agent_spec = cfg.agent(spec.agent)
    budget = cfg.budgets.primary if spec.phase is Phase.PRIMARY else cfg.budgets.recovery
    run_id = f"{cfg.id}/{task.instance_id}/{spec.name}/{adir.name}"
    miniswe_path = cfg.prompt_path("miniswe_config")
    note = (handoff_dir(ctx, spec.primary_agent) / "note.md").read_text() if spec.context == "note" else None
    task_text = build_task_text(cfg, task, spec.prompt_kind, note=note)
    (adir / "task_prompt.md").write_text(task_text)
    result: dict[str, Any] = {
        "run_id": run_id, "experiment_id": cfg.id, "task_id": task.instance_id, "subset": task.subset,
        "branch": spec.name, "phase": spec.phase.value, "agent": spec.agent, "primary_agent": spec.primary_agent,
        "context": spec.context, "primary_source": cfg.primary_experiment,
        "model": agent_spec.model, "model_revision": agent_spec.hf_revision, "attempt": int(adir.name.split("_")[1]),
        "harness": {"mini_swe_agent": package_versions().get("mini-swe-agent"),
                    "project_git": git_info(cfg.project_root)},
        "inference_server_version": _server_version(agent_spec.base_url),
        "prompt_version": cfg.prompt_version, "prompt_kind": spec.prompt_kind,
        "prompt_sha256": {"miniswe_config": sha256_file(miniswe_path), "task_text": sha256_file(adir / "task_prompt.md")},
        "protocol_fingerprint": cfg.protocol_fingerprint(),
        "budget": {"wallclock_seconds": budget.wallclock_minutes * 60, "step_limit": budget.step_limit,
                   "command_timeout_seconds": cfg.budgets.command_timeout_seconds,
                   "max_tokens_per_response": cfg.budgets.max_tokens_per_response},
        "image_digest": ctx.image_info["digest"], "base_commit": ctx.pristine["base_commit"],
        "repo_dir": ctx.pristine["repo_dir"], "work_dir": str(work), "host": socket.gethostname(),
    }
    extra: dict | None = None
    exc: BaseException | None = None
    watchdog = False
    agent: RecordingAgent | None = None
    instance: Instance | None = None
    traj = TrajectoryWriter(adir / "trajectory.jsonl", run_id=run_id, task_id=task.instance_id, agent=spec.agent)
    try:
        # ---- 1. start state (fresh, verified)
        remove_tree(work)
        work.mkdir(parents=True)
        if spec.from_checkpoint:
            ckpt = WorkspaceCheckpoint.load(checkpoint_dir(ctx, spec.primary_agent))
            start_hash = restore_checkpoint(ckpt, rootfs)
            result["start_state"] = {"kind": "checkpoint", "tree_hash": start_hash, "checkpoint": str(ckpt.workspace_archive.parent)}
        else:
            start_hash = restore_checkpoint(WorkspaceCheckpoint.load(ctx.task_dir / "pristine"), rootfs)
            result["start_state"] = {"kind": "pristine", "tree_hash": start_hash}
        repo_dir = ctx.pristine["repo_dir"]
        # ---- 2. agent phase (no network)
        miniswe_cfg = load_miniswe_config(miniswe_path)
        instance = Instance(rootfs, env=miniswe_cfg.get("environment", {}).get("env", {}))
        instance.start()
        env = ApptainerEnvironment(instance, cwd=repo_dir, timeout=cfg.budgets.command_timeout_seconds)
        model = build_model(agent_spec, miniswe_cfg, max_tokens=cfg.budgets.max_tokens_per_response,
                            request_timeout=cfg.budgets.model_request_timeout_seconds)
        agent_cfg = {k: v for k, v in miniswe_cfg["agent"].items() if k not in ("mode", "cost_limit", "step_limit")}
        agent_cfg.update(step_limit=budget.step_limit, cost_limit=0.0,
                         wall_time_limit_seconds=int(budget.wallclock_minutes * 60),
                         output_path=adir / "mini_trajectory.json")
        traj.emit(EventType.RUN_START, metadata={k: result[k] for k in ("branch", "phase", "model", "budget", "start_state")})
        result["started_at"] = utc_now()
        t0 = time.monotonic()
        agent = RecordingAgent(model, env, traj=traj, **agent_cfg)
        box: dict[str, Any] = {}

        def _target() -> None:
            try:
                box["extra"] = agent.run(task_text)
            except BaseException as e:  # noqa: BLE001 - classified below
                box["exc"], box["tb"] = e, traceback.format_exc()

        th = threading.Thread(target=_target, name=f"agent-{spec.name}", daemon=True)
        th.start()
        th.join(budget.wallclock_minutes * 60 + cfg.budgets.hard_kill_grace_seconds)
        if th.is_alive():  # a single command/model call overran the between-steps wall-clock check
            watchdog = True
            log.warning("hard wall-clock limit reached; stopping the sandbox")
            instance.stop()
            th.join(cfg.budgets.model_request_timeout_seconds + 120)
        result["agent_seconds"] = round(time.monotonic() - t0, 1)
        result["agent_ended_at"] = utc_now()
        extra, exc = box.get("extra"), box.get("exc")
        if exc is not None:
            result["exception"] = {"type": type(exc).__name__, "message": str(exc)[:4000], "traceback": box.get("tb")}
    except BaseException as e:  # noqa: BLE001 - failure before/around the agent
        exc = e
        result["exception"] = {"type": type(e).__name__, "message": str(e)[:4000], "traceback": traceback.format_exc()}
    finally:
        if instance is not None:
            instance.stop()  # kills every process the agent left; the filesystem state is what remains

    exit_reason = _exit_reason(spec.phase, extra, exc, watchdog)
    result["exit_reason"] = exit_reason.value
    result["watchdog_fired"] = watchdog
    if agent is not None:
        result["usage"] = dict(agent.usage)
        call_log = agent.model.call_log
        (adir / "usage.json").write_text(json.dumps({"totals": agent.usage, "calls": call_log}, indent=1))

    # ---- 3. capture, checkpoint (primary), evaluate
    eval_status = EvalStatus.NOT_EVALUATED
    diff = b""
    try:
        if rootfs.exists() and (rootfs / ctx.pristine["repo_dir"].lstrip("/")).exists():
            cap = capture_state(rootfs, ctx.pristine["repo_dir"], ctx.pristine["base_commit"], work / "capture",
                                base_patch=(ctx.task_dir / "pristine" / "git_diff.patch").read_bytes())
            diff = cap.diff
            (adir / "final.diff").write_bytes(cap.diff)
            (adir / "git_status.txt").write_text(cap.status)
            result.update(final_diff_bytes=len(cap.diff), final_diff_sha256=hashlib.sha256(cap.diff).hexdigest(),
                          head_after=cap.head)
            infra = exit_reason in (ExitReason.MODEL_ERROR, ExitReason.HARNESS_ERROR, ExitReason.CONTAINER_ERROR)
            if spec.phase is Phase.PRIMARY and not infra:
                ck = create_checkpoint(rootfs, adir / CHECKPOINT_SUBDIR, task_id=task.instance_id,
                                       base_commit=ctx.pristine["base_commit"], repo_dir=ctx.pristine["repo_dir"],
                                       git_diff=cap.diff, git_status=cap.status,
                                       extra={"source_run_id": run_id, "image_digest": ctx.image_info["digest"]})
                result["checkpoint"] = {"tree_hash": ck.tree_hash, "archive_bytes": ck.metadata["archive_bytes"]}
            if not infra:
                ev = evaluate_patch(task, cap.diff, ctx.sif, adir / "eval", work / "eval",
                                    cfg.budgets.evaluator_timeout_seconds)
                eval_status = EvalStatus(ev.status)
                result["eval"] = ev.to_dict()
    except BaseException as e:  # noqa: BLE001
        log.error(f"post-run step failed: {e}")
        result["post_run_exception"] = {"type": type(e).__name__, "message": str(e)[:4000],
                                        "traceback": traceback.format_exc()}
        if eval_status is EvalStatus.NOT_EVALUATED and exit_reason not in (ExitReason.MODEL_ERROR, ExitReason.HARNESS_ERROR, ExitReason.CONTAINER_ERROR):
            eval_status = EvalStatus.EVALUATOR_ERROR

    outcome, status = classify(exit_reason, eval_status)
    result.update(eval_status=eval_status.value, outcome_class=outcome.value, status=status,
                  solved=(eval_status is EvalStatus.SOLVED) if outcome is not OutcomeClass.INFRA_FAILURE else None)
    if spec.phase is Phase.PRIMARY:
        result["primary_failure"] = is_primary_failure(exit_reason, eval_status, cfg.primary_failure.definition)
    traj.emit(EventType.RUN_END, content={k: result[k] for k in ("exit_reason", "eval_status", "outcome_class", "status")})
    traj.close()
    try:
        result["stats"] = compute_run_stats(read_trajectory(adir / "trajectory.jsonl"), diff)
        result["stats"]["n_steps"] = agent.n_calls if agent is not None else 0
        if agent is not None and result["stats"]["model_seconds"]:
            result["stats"]["output_tokens_per_model_second"] = round(
                agent.usage["completion_tokens"] / result["stats"]["model_seconds"], 2)
    except Exception as e:  # noqa: BLE001
        result["stats_error"] = str(e)
    result["ended_at"] = utc_now()
    (adir / "result.json").write_text(json.dumps(result, indent=2, default=str))
    log.info(f"{spec.name} {adir.name}: {status} ({exit_reason.value}, {eval_status.value})")
    for h in list(log.handlers):
        h.close()
        log.removeHandler(h)
    remove_tree(work)  # everything needed for analysis/debugging is already in the attempt directory
    return result
