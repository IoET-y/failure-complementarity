import shutil

import pytest
import yaml

from failure_complementarity.config import ConfigError, expand_env, load_experiment


def test_expand_env_plain_default_and_nested():
    env = {"A": "x", "ROOT": "/r"}
    assert expand_env("${A}/y", env) == "x/y"
    assert expand_env("${B:-dflt}", env) == "dflt"
    assert expand_env("${B:-${ROOT}/runs}", env) == "/r/runs"
    assert expand_env("${A:-${ROOT}/runs}", env) == "x"
    assert expand_env("no vars", env) == "no vars"


def test_expand_env_empty_value_uses_default():
    assert expand_env("${A:-d}", {"A": ""}) == "d"


def test_expand_env_unset_without_default_is_error():
    with pytest.raises(ConfigError):
        expand_env("${NOPE}", {})
    with pytest.raises(ConfigError):
        expand_env("${UNTERMINATED", {})


def test_pilot_config_loads(cfg):
    assert cfg.id == "pilot_v0"
    assert cfg.agents == ["qwen", "devstral"]
    assert cfg.agent("qwen").model == "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8"
    assert cfg.agent("devstral").model == "mistralai/Devstral-Small-2-24B-Instruct-2512"
    assert cfg.rescue_pairs() == [("qwen", "qwen"), ("qwen", "devstral"),
                                  ("devstral", "qwen"), ("devstral", "devstral")]
    assert cfg.prompt_path("recovery_preamble").is_file()
    assert set(cfg.source_files) >= {"pilot.yaml", "agents.yaml", "budgets.yaml", "prompts/recovery_v0.md"}


def test_budgets_are_shared_not_per_model(cfg):
    # Budgets live in one file and are not attached to agents: a model cannot get its own budget.
    assert "budget" not in str(cfg.agent_specs).lower()
    assert cfg.budgets.primary.wallclock_minutes > 0 and cfg.budgets.recovery.wallclock_minutes > 0


def test_models_share_max_context(cfg):
    lens = {cfg.agent(a).serve.max_model_len for a in cfg.agents}
    assert len(lens) == 1, "comparable inference budgets require one max_model_len (D-008)"


def test_fingerprint_ignores_paths_and_endpoints(pilot_path, tmp_path):
    a = load_experiment(pilot_path, env={"FC_RUNS_ROOT": str(tmp_path / "a")})
    b = load_experiment(pilot_path, env={"FC_RUNS_ROOT": str(tmp_path / "b"),
                                         "FC_QWEN_BASE_URL": "http://otherhost:9/v1"})
    assert a.paths.runs_root != b.paths.runs_root
    assert a.protocol_fingerprint() == b.protocol_fingerprint()


def _copy_configs(tmp_path, pilot_path):
    dst = tmp_path / "configs"
    shutil.copytree(pilot_path.parent, dst)
    (tmp_path / "pyproject.toml").write_text("")  # marks the project root
    return dst


def test_fingerprint_changes_with_budget_and_prompt(tmp_path, pilot_path):
    base = load_experiment(pilot_path).protocol_fingerprint()
    d = _copy_configs(tmp_path, pilot_path)
    budgets = yaml.safe_load((d / "budgets.yaml").read_text())
    budgets["primary"]["wallclock_minutes"] = 31
    (d / "budgets.yaml").write_text(yaml.safe_dump(budgets))
    assert load_experiment(d / "pilot.yaml").protocol_fingerprint() != base

    d2 = _copy_configs(tmp_path / "x", pilot_path)
    (d2 / "prompts" / "recovery_v0.md").write_text("changed prompt")
    assert load_experiment(d2 / "pilot.yaml").protocol_fingerprint() != base


def test_unknown_field_and_unknown_agent_rejected(tmp_path, pilot_path):
    d = _copy_configs(tmp_path, pilot_path)
    pilot = yaml.safe_load((d / "pilot.yaml").read_text())
    pilot["experiment"]["agents"] = ["qwen", "gpt_unknown"]
    (d / "pilot.yaml").write_text(yaml.safe_dump(pilot))
    with pytest.raises(ConfigError, match="unknown agents"):
        load_experiment(d / "pilot.yaml")

    d2 = _copy_configs(tmp_path / "y", pilot_path)
    budgets = yaml.safe_load((d2 / "budgets.yaml").read_text())
    budgets["primary"]["wallclock_minuets"] = 30  # typo must not be silently ignored
    (d2 / "budgets.yaml").write_text(yaml.safe_dump(budgets))
    with pytest.raises(ConfigError):
        load_experiment(d2 / "pilot.yaml")


def test_third_model_needs_only_config(tmp_path, pilot_path):
    d = _copy_configs(tmp_path, pilot_path)
    agents = yaml.safe_load((d / "agents.yaml").read_text())
    agents["agents"]["third"] = dict(agents["agents"]["devstral"], display_name="Third", model="org/third",
                                     base_url="http://127.0.0.1:8003/v1")
    (d / "agents.yaml").write_text(yaml.safe_dump(agents))
    pilot = yaml.safe_load((d / "pilot.yaml").read_text())
    pilot["experiment"]["agents"].append("third")
    (d / "pilot.yaml").write_text(yaml.safe_dump(pilot))
    cfg = load_experiment(d / "pilot.yaml")
    assert len(cfg.rescue_pairs()) == 9


def test_api_key_default(cfg, monkeypatch):
    monkeypatch.delenv("FC_QWEN_API_KEY", raising=False)
    assert cfg.agent("qwen").api_key() == "EMPTY"
    monkeypatch.setenv("FC_QWEN_API_KEY", "k")
    assert cfg.agent("qwen").api_key() == "k"


def test_adding_unused_agent_keeps_fingerprint(tmp_path, pilot_path):
    base = load_experiment(pilot_path).protocol_fingerprint()
    d = _copy_configs(tmp_path, pilot_path)
    agents = yaml.safe_load((d / "agents.yaml").read_text())
    agents["agents"]["unused"] = dict(agents["agents"]["devstral"], model="org/unused")
    (d / "agents.yaml").write_text(yaml.safe_dump(agents))
    assert load_experiment(d / "pilot.yaml").protocol_fingerprint() == base


def test_endpoint_override_env(pilot_path):
    c = load_experiment(pilot_path, env={"FC_ENDPOINT_QWEN": "http://127.0.0.1:43210/v1"})
    assert c.agent("qwen").base_url == "http://127.0.0.1:43210/v1"
    assert c.protocol_fingerprint() == load_experiment(pilot_path, env={}).protocol_fingerprint()
