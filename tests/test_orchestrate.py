import json

import pytest
from types import SimpleNamespace

from failure_complementarity.runner.branch import control_branch, primary_branch, recovery_branch
from failure_complementarity.runner.orchestrate import plan_primary, plan_recovery


def _write(tdir, branch, **r):
    (tdir / branch).mkdir(parents=True, exist_ok=True)
    (tdir / branch / "result.json").write_text(json.dumps(r))


def test_branch_names():
    assert primary_branch("qwen").name == "primary_qwen"
    assert recovery_branch("qwen", "devstral").name == "recovery_qwen_to_devstral"
    assert control_branch("devstral", "qwen").name == "control_devstral_repo0"
    assert recovery_branch("qwen", "qwen").from_checkpoint and not control_branch("devstral", "qwen").from_checkpoint
    assert recovery_branch("qwen", "qwen").prompt_kind == "recovery" and control_branch("d", "q").prompt_kind == "primary"


def test_plans(cfg, tmp_path):
    assert len(plan_primary(cfg, ["t1", "t2"])) == 4
    import os
    from failure_complementarity.config import load_experiment
    from conftest import PILOT
    cfg = load_experiment(PILOT, env=dict(os.environ, FC_RUNS_ROOT=str(tmp_path / "runs")))
    exp = tmp_path / "runs" / cfg.id
    ctxs = {t: SimpleNamespace(cfg=cfg, task=SimpleNamespace(instance_id=t), task_dir=exp / t) for t in ("t1", "t2", "t3")}
    tmp_path = exp
    _write(tmp_path / "t1", "primary_qwen", outcome_class="TASK_FAILURE", primary_failure=True, status="PRIMARY_TIMEOUT", exit_reason="PRIMARY_TIMEOUT")
    _write(tmp_path / "t1", "primary_devstral", outcome_class="SUCCESS", primary_failure=False, status="SOLVED", exit_reason="SUBMITTED")
    _write(tmp_path / "t2", "primary_qwen", outcome_class="TASK_FAILURE", primary_failure=False, status="UNSOLVED", exit_reason="SUBMITTED")
    _write(tmp_path / "t2", "primary_devstral", outcome_class="INFRA_FAILURE", primary_failure=None, status="MODEL_ERROR", exit_reason="MODEL_ERROR")
    _write(tmp_path / "t3", "primary_qwen", outcome_class="TASK_FAILURE", primary_failure=True, status="PRIMARY_TIMEOUT", exit_reason="PRIMARY_TIMEOUT")
    _write(tmp_path / "t3", "primary_devstral", outcome_class="TASK_FAILURE", primary_failure=True, status="PRIMARY_TIMEOUT", exit_reason="PRIMARY_TIMEOUT")
    plan, notes = plan_recovery(cfg, ctxs, ["t1", "t2", "t3"])
    got = sorted((t, s.name) for t, s in plan)
    assert got == sorted([
        ("t1", "recovery_qwen_to_qwen"), ("t1", "recovery_qwen_to_devstral"), ("t1", "control_devstral_repo0"),
        ("t3", "recovery_qwen_to_qwen"), ("t3", "recovery_qwen_to_devstral"), ("t3", "control_devstral_repo0"),
        ("t3", "recovery_devstral_to_qwen"), ("t3", "recovery_devstral_to_devstral"), ("t3", "control_qwen_repo0"),
    ])
    entered = {(n["task_id"], n["primary_agent"]): n for n in notes}
    assert not entered[("t2", "qwen")]["entered"] and "not a primary failure" in entered[("t2", "qwen")]["reason"]
    assert "infra" in entered[("t2", "devstral")]["reason"]


def test_plan_with_all_conditions(tmp_path):
    import os
    from failure_complementarity.config import load_experiment
    from conftest import PROJECT_ROOT
    cfg = load_experiment(PROJECT_ROOT / "configs" / "pilot_v2.yaml", env=dict(os.environ, FC_RUNS_ROOT=str(tmp_path / "runs")))
    exp = tmp_path / "runs" / cfg.id
    ctxs = {t: SimpleNamespace(cfg=cfg, task=SimpleNamespace(instance_id=t), task_dir=exp / t) for t in ("t1", "t2")}
    _write(exp / "t1", "primary_devstral", outcome_class="TASK_FAILURE", primary_failure=True, status="UNSOLVED", exit_reason="SUBMITTED")
    _write(exp / "t1", "primary_glm47flash", outcome_class="TASK_FAILURE", primary_failure=True, status="UNSOLVED", exit_reason="SUBMITTED")
    _write(exp / "t2", "primary_devstral", outcome_class="SUCCESS", primary_failure=False, status="SOLVED", exit_reason="SUBMITTED")
    _write(exp / "t2", "primary_glm47flash", outcome_class="TASK_FAILURE", primary_failure=True, status="UNSOLVED", exit_reason="SUBMITTED")
    plan, _ = plan_recovery(cfg, ctxs, ["t1", "t2"])
    names = sorted((t, s.name) for t, s in plan)
    t1 = [n for t, n in names if t == "t1"]
    # both failed on t1: 2x2 recovery + 2x2 note recovery + 2 controls (deduplicated)
    assert len(t1) == 10 and t1.count("control_devstral_repo0") == 1 and t1.count("control_glm47flash_repo0") == 1
    t2 = [n for t, n in names if t == "t2"]
    assert sorted(t2) == sorted(["recovery_glm47flash_to_glm47flash", "recovery_glm47flash_to_devstral",
                                  "recovery_note_glm47flash_to_glm47flash", "recovery_note_glm47flash_to_devstral",
                                  "control_glm47flash_repo0", "control_devstral_repo0"])


def test_branch_lock_prevents_double_run(cfg, tmp_path):
    import fcntl
    from failure_complementarity.runner.branch import BranchBusy, run_branch
    ctx = SimpleNamespace(cfg=cfg, task=SimpleNamespace(instance_id="t"), task_dir=tmp_path / "t")
    spec = primary_branch("qwen")
    (tmp_path / "t" / spec.name).mkdir(parents=True)
    import subprocess, sys, time
    holder = subprocess.Popen([sys.executable, "-c",
        "import fcntl,sys,time; f=open(sys.argv[1],'w'); fcntl.lockf(f, fcntl.LOCK_EX); print('locked', flush=True); time.sleep(30)",
        str(tmp_path / "t" / spec.name / ".running.lock")], stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "locked"
    try:
        with pytest.raises(BranchBusy):
            run_branch(ctx, spec)
    finally:
        holder.kill()
    # a finished branch is returned without taking the lock
    (tmp_path / "t" / spec.name / "result.json").write_text('{"status": "SOLVED"}')
    assert run_branch(ctx, spec)["status"] == "SOLVED"
