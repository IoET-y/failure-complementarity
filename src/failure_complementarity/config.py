"""Experiment configuration: YAML files -> validated, fingerprinted ExperimentConfig.

Values may reference environment variables as ``${VAR}`` or ``${VAR:-default}`` (defaults may nest).
``FC_PROJECT_ROOT`` defaults to the directory that contains ``configs/``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConfigError(ValueError):
    pass


# --------------------------------------------------------------------------- env expansion


def expand_env(text: str, env: Mapping[str, str]) -> str:
    """Expand ``${VAR}`` and ``${VAR:-default}``; raise ConfigError for an unset VAR without default."""
    out: list[str] = []
    i = 0
    while i < len(text):
        start = text.find("${", i)
        if start < 0:
            out.append(text[i:])
            break
        out.append(text[i:start])
        depth, j = 1, start + 2
        while j < len(text) and depth:
            if text.startswith("${", j):
                depth += 1
                j += 2
                continue
            if text[j] == "}":
                depth -= 1
            j += 1
        if depth:
            raise ConfigError(f"unterminated '${{' in {text!r}")
        name, sep, default = text[start + 2 : j - 1].partition(":-")
        if name in env and env[name] != "":
            out.append(env[name])
        elif sep:
            out.append(expand_env(default, env))
        else:
            raise ConfigError(f"environment variable {name!r} is not set and has no default (in {text!r})")
        i = j
    return "".join(out)


def _expand_tree(obj: Any, env: Mapping[str, str]) -> Any:
    if isinstance(obj, str):
        return expand_env(obj, env)
    if isinstance(obj, list):
        return [_expand_tree(v, env) for v in obj]
    if isinstance(obj, dict):
        return {k: _expand_tree(v, env) for k, v in obj.items()}
    return obj


# --------------------------------------------------------------------------- schema


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ServeSpec(_Strict):
    engine: Literal["vllm"]
    port: int
    tensor_parallel_size: int = 1
    max_model_len: int
    gpu_memory_utilization: float = 0.9
    extra_args: list[str] = []


class AgentSpec(_Strict):
    name: str
    display_name: str
    provider: Literal["openai_compatible"]
    base_url: str
    api_key_env: str | None = None
    model: str
    hf_repo: str | None = None
    hf_revision: str | None = None
    sampling: dict[str, float] = {}
    serve: ServeSpec | None = None

    def api_key(self) -> str:
        return (os.environ.get(self.api_key_env) if self.api_key_env else None) or "EMPTY"


class BenchmarkSpec(_Strict):
    name: Literal["swe_bench_pro_v2"]
    release_tag: str
    repo_url: str
    repo_commit: str
    tasks_subdir: str
    hard_ids_file: str
    checksums_file: str
    official_mini_config: str
    image_template: str
    hf_dataset: str
    hf_revision: str


class PhaseBudget(_Strict):
    wallclock_minutes: float = Field(gt=0)
    step_limit: int = Field(default=0, ge=0)


class Budgets(_Strict):
    primary: PhaseBudget
    recovery: PhaseBudget
    command_timeout_seconds: int = Field(gt=0)
    max_tokens_per_response: int = Field(gt=0)
    model_request_timeout_seconds: int = Field(gt=0)
    hard_kill_grace_seconds: int = Field(ge=0)
    evaluator_timeout_seconds: int = Field(gt=0)


class Paths(_Strict):
    runs_root: Path
    results_root: Path
    benchmark_repo: Path
    sif_cache: Path
    apptainer_cache: Path
    work_root: Path
    hf_home: Path


class Prompts(_Strict):
    miniswe_config: str
    recovery_preamble: str
    handoff_request: str | None = None          # context transfer (D-026)
    recovery_note_preamble: str | None = None   # context transfer (D-026)


class PrimaryFailure(_Strict):
    definition: Literal["budget_exhausted_and_unsolved", "unsolved_any_exit"]


class TaskSelection(_Strict):
    seed: int
    n_hard: int = Field(ge=0)
    n_nonhard: int = Field(ge=0)
    task_list: str | None = None


class Runtime(_Strict):
    container: Literal["apptainer"]
    agent_network: Literal["none"]
    verifier_network: Literal["public", "none"]
    max_concurrent_per_endpoint: int = Field(ge=1)


class Conditions(_Strict):
    """Which branches are run for each primary failure of A (B ranges over all experiment agents, incl. A)."""
    v0: bool = True                                   # recovery_A_to_B
    note: bool = False                                # recovery_note_A_to_B (D-026)
    controls: Literal["cross", "both"] = "cross"      # control_B_repo0 for B != A only, or also B = A


class ExperimentConfig(_Strict):
    id: str
    description: str = ""
    agents: list[str]
    prompt_version: str
    prompts: Prompts
    primary_failure: PrimaryFailure
    task_selection: TaskSelection
    runtime: Runtime
    infra_retries: int = Field(ge=0)
    primary_source: str | None = None  # reuse primaries/checkpoints of this experiment id (D-026)
    conditions: Conditions | None = None  # None = V0 design (recovery for all B + cross-model controls)
    # loaded from the include files
    agent_specs: dict[str, AgentSpec]
    benchmark: BenchmarkSpec
    budgets: Budgets
    paths: Paths
    config_dir: Path
    source_files: dict[str, str]  # relative path -> sha256 of raw file bytes

    @field_validator("id")
    @classmethod
    def _id_is_path_safe(cls, v: str) -> str:
        if not v or any(c in v for c in "/\\ ") or v.startswith("."):
            raise ValueError(f"experiment id must be a simple directory name, got {v!r}")
        return v

    @model_validator(mode="after")
    def _check_agents(self) -> "ExperimentConfig":
        if len(set(self.agents)) != len(self.agents):
            raise ValueError("duplicate agent in experiment.agents")
        missing = [a for a in self.agents if a not in self.agent_specs]
        if missing:
            raise ValueError(f"experiment.agents references unknown agents {missing}; known: {sorted(self.agent_specs)}")
        return self

    # ---- convenience

    def agent(self, name: str) -> AgentSpec:
        return self.agent_specs[name]

    def rescue_pairs(self) -> list[tuple[str, str]]:
        """All ordered (primary, rescuer) pairs, including same-model pairs."""
        return [(a, b) for a in self.agents for b in self.agents]

    def prompt_path(self, which: str) -> Path:
        rel = getattr(self.prompts, which)
        if rel is None:
            raise ConfigError(f"experiment {self.id!r} defines no prompt {which!r}")
        return self.config_dir / rel

    @property
    def primary_experiment(self) -> str:
        return self.primary_source or self.id

    @property
    def project_root(self) -> Path:
        return find_project_root(self.config_dir)

    def resolved_dict(self) -> dict[str, Any]:
        return json.loads(self.model_dump_json())

    def protocol_dict(self) -> dict[str, Any]:
        """Everything that defines the *science*: excludes storage paths and endpoint locations."""
        d = self.resolved_dict()
        for k in ("paths", "config_dir", "source_files", "description"):
            d.pop(k, None)
        # optional fields added later are omitted when unset, so older experiments keep their fingerprint
        for opt in ("primary_source", "conditions"):
            if d.get(opt) is None:
                d.pop(opt, None)
        d["prompts"] = {k: v for k, v in d["prompts"].items() if v is not None}
        # only the models this experiment uses define it (adding a model to agents.yaml must not change others)
        d["agent_specs"] = {k: v for k, v in d["agent_specs"].items() if k in self.agents}
        for spec in d["agent_specs"].values():
            spec.pop("base_url", None)
            spec.pop("api_key_env", None)
        for name, rel in self.prompts.model_dump().items():
            if rel is not None:
                d["prompts"][f"{name}_sha256"] = self.source_files[rel]
        return d

    def protocol_fingerprint(self) -> str:
        return sha256_json(self.protocol_dict())


# --------------------------------------------------------------------------- loading


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping")
    return data


def _single_key(data: dict[str, Any], key: str, path: Path) -> Any:
    if set(data) != {key}:
        raise ConfigError(f"{path} must have exactly one top-level key {key!r}, got {sorted(data)}")
    return data[key]


def find_project_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "pyproject.toml").is_file() and (d / "configs").is_dir():
            return d
    raise ConfigError(f"no project root (pyproject.toml + configs/) above {start}")


def load_experiment(path: str | Path, env: Mapping[str, str] | None = None) -> ExperimentConfig:
    path = Path(path).resolve()
    config_dir = path.parent
    env = dict(os.environ if env is None else env)
    env.setdefault("FC_PROJECT_ROOT", str(find_project_root(config_dir)))

    raw = _read_yaml(path)
    exp = copy.deepcopy(_single_key(raw, "experiment", path))
    include = exp.pop("include", None) or {}
    required = {"agents", "benchmark", "budgets", "paths"}
    if set(include) != required:
        raise ConfigError(f"experiment.include must name exactly {sorted(required)}, got {sorted(include)}")

    files = {"experiment": path} | {k: config_dir / v for k, v in include.items()}
    loaded = {k: _read_yaml(p) for k, p in files.items() if k != "experiment"}

    agents_raw = _single_key(loaded["agents"], "agents", files["agents"])
    agent_specs = {name: {"name": name, **_expand_tree(spec, env)} for name, spec in agents_raw.items()}
    for name, spec in agent_specs.items():  # per-job endpoint (dynamic port on a shared node); not part of the protocol
        override = env.get(f"FC_ENDPOINT_{name.upper()}")
        if override:
            spec["base_url"] = override
    benchmark = _single_key(loaded["benchmark"], "benchmark", files["benchmark"])
    paths = _expand_tree(_single_key(loaded["paths"], "paths", files["paths"]), env)

    prompts = exp.get("prompts", {})
    prompt_files = {v: config_dir / v for v in prompts.values() if v} if isinstance(prompts, dict) else {}
    for rel, p in prompt_files.items():
        if not p.is_file():
            raise ConfigError(f"prompt file not found: {p}")

    source_files = {os.path.relpath(p, config_dir): sha256_file(p) for p in [*files.values(), *prompt_files.values()]}

    try:
        return ExperimentConfig(
            **exp,
            agent_specs=agent_specs,
            benchmark=benchmark,
            budgets=loaded["budgets"],
            paths=paths,
            config_dir=config_dir,
            source_files=source_files,
        )
    except ConfigError:
        raise
    except Exception as e:  # pydantic ValidationError -> one error type for callers
        raise ConfigError(f"invalid experiment config {path}:\n{e}") from e
