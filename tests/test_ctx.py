import json
from types import SimpleNamespace

import pytest

from failure_complementarity.agents import handoff
from failure_complementarity.benchmark.swebench_pro import Task
from failure_complementarity.config import load_experiment
from failure_complementarity.runner.branch import build_task_text, recovery_note_branch
from failure_complementarity.runner.orchestrate import plan_ctx


def _traj(tmp_path, n_steps=5, big=0):
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "task"}]
    for i in range(n_steps):
        msgs.append({"role": "assistant", "content": f"think {i}", "reasoning_content": "SECRET",
                     "tool_calls": [{"id": f"c{i}", "type": "function", "function": {"name": "bash", "arguments": "{}"}}],
                     "extra": {"x": 1}})
        msgs.append({"role": "tool", "tool_call_id": f"c{i}", "content": "out" + "x" * big})
    msgs.append({"role": "exit", "content": "", "extra": {"exit_status": "Submitted"}})
    p = tmp_path / "mini_trajectory.json"
    p.write_text(json.dumps({"messages": msgs}))
    return p


def test_load_conversation_drops_exit_extra_and_reasoning(tmp_path):
    msgs = handoff.load_conversation(_traj(tmp_path))
    assert [m["role"] for m in msgs][:4] == ["system", "user", "assistant", "tool"] and msgs[-1]["role"] == "tool"
    assert all("extra" not in m and "reasoning_content" not in m for m in msgs)


def test_truncate_keeps_whole_steps(tmp_path):
    msgs = handoff.load_conversation(_traj(tmp_path, n_steps=10, big=1000))
    out, dropped = handoff.truncate(msgs, 3500)
    assert dropped > 0 and out[0]["role"] == "system" and out[1]["content"] == "task"
    assert "omitted" in out[2]["content"]
    # every tool result follows the assistant turn that issued it
    ids = {tc["id"] for m in out if m["role"] == "assistant" for tc in m["tool_calls"]}
    assert all(m["tool_call_id"] in ids for m in out if m["role"] == "tool")
    same, d0 = handoff.truncate(msgs, 10 ** 9)
    assert d0 == 0 and same == msgs


def test_generate_note_request(tmp_path, monkeypatch, cfg):
    seen = {}

    def fake_completion(**kw):
        seen.update(kw)
        msg = SimpleNamespace(content="  I changed X. Y still fails.  ")
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], usage=None, id="r1")

    monkeypatch.setattr(handoff.litellm, "completion", fake_completion)
    rec = handoff.generate_note(cfg.agent("qwen"), _traj(tmp_path), "WRITE A NOTE", max_model_len=131072)
    assert rec["note"] == "I changed X. Y still fails." and rec["dropped_steps"] == 0
    assert seen["tool_choice"] == "none" and seen["messages"][-1] == {"role": "user", "content": "WRITE A NOTE"}
    assert seen["temperature"] == 0.7 and seen["extra_body"] == {"top_k": 20, "repetition_penalty": 1.05}


@pytest.fixture
def ctx_cfg(tmp_path):
    import os
    from conftest import PROJECT_ROOT
    return load_experiment(PROJECT_ROOT / "configs" / "ctx_v1.yaml", env=dict(os.environ, FC_RUNS_ROOT=str(tmp_path / "runs")))


def test_note_prompt_differs_from_v0_only_by_note(ctx_cfg, tmp_path):
    (tmp_path / "instruction.md").write_text("ORIGINAL TASK")
    task = Task("t", "nonhard", tmp_path, "img", 1.0, 1.0)
    v0 = build_task_text(ctx_cfg, task, "recovery")
    note = build_task_text(ctx_cfg, task, "recovery_note", note="THE NOTE")
    assert "<handoff_note>\nTHE NOTE\n</handoff_note>" in note and "THE NOTE" not in v0
    assert v0.endswith("## Original task\n\nORIGINAL TASK") and note.endswith("## Original task\n\nORIGINAL TASK")
    with pytest.raises(ValueError):
        build_task_text(ctx_cfg, task, "recovery_note")
    assert recovery_note_branch("qwen", "devstral").prompt_kind == "recovery_note"


def test_plan_ctx(ctx_cfg):
    src = ctx_cfg.paths.runs_root / "pilot_v1"
    def w(t, a, **r):
        d = src / t / f"primary_{a}"; d.mkdir(parents=True); (d / "result.json").write_text(json.dumps(r))
    w("t1", "qwen", outcome_class="TASK_FAILURE", primary_failure=True)
    w("t1", "devstral", outcome_class="SUCCESS", primary_failure=False)
    w("t2", "qwen", outcome_class="INFRA_FAILURE", primary_failure=None)
    w("t2", "devstral", outcome_class="TASK_FAILURE", primary_failure=True)
    ctxs = {t: SimpleNamespace(cfg=ctx_cfg, task=SimpleNamespace(instance_id=t)) for t in ("t1", "t2")}
    got = sorted((t, s.name) for t, s in plan_ctx(ctx_cfg, ctxs, ["t1", "t2"]))
    assert got == sorted([("t1", "recovery_note_qwen_to_qwen"), ("t1", "recovery_note_qwen_to_devstral"), ("t1", "control_qwen_repo0"),
                          ("t2", "recovery_note_devstral_to_qwen"), ("t2", "recovery_note_devstral_to_devstral"), ("t2", "control_devstral_repo0")])
