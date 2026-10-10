"""SWE-bench Pro V2: checkout verification and task loading (Harbor task directories)."""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from failure_complementarity.config import BenchmarkSpec, sha256_file


class BenchmarkPinError(RuntimeError):
    pass


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def verify_checksums(repo: Path, spec: BenchmarkSpec) -> int:
    """Verify every entry of v2/SHA256SUMS; return number of files checked."""
    sums = repo / spec.checksums_file
    base = sums.parent
    n, bad = 0, []
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        rel = rel.lstrip("*")
        h = hashlib.sha256((base / rel).read_bytes()).hexdigest() if (base / rel).is_file() else None
        if h != digest:
            bad.append(rel)
        n += 1
    if bad:
        raise BenchmarkPinError(f"{len(bad)} files fail {spec.checksums_file}, e.g. {bad[:5]}")
    return n


def verify_benchmark_repo(repo: Path, spec: BenchmarkSpec, *, checksums: bool = True) -> dict[str, Any]:
    """Fail loudly unless the local checkout is exactly the pinned release."""
    if not (repo / ".git").exists():
        raise BenchmarkPinError(f"benchmark repo not found at {repo} (clone {spec.repo_url})")
    head = _git(repo, "rev-parse", "HEAD")
    if head != spec.repo_commit:
        raise BenchmarkPinError(f"benchmark repo at {head}, expected pinned {spec.repo_commit}")
    dirty = _git(repo, "status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise BenchmarkPinError(f"benchmark repo has local modifications:\n{dirty[:2000]}")
    tasks = sorted(p.name for p in (repo / spec.tasks_subdir).iterdir() if p.is_dir())
    hard = [l.strip() for l in (repo / spec.hard_ids_file).read_text().splitlines() if l.strip()]
    if not set(hard) <= set(tasks):
        raise BenchmarkPinError("HARD ids not all present in task directory")
    info = {
        "repo_path": str(repo),
        "commit": head,
        "release_tag": spec.release_tag,
        "n_tasks": len(tasks),
        "n_hard": len(hard),
        "hard_ids_sha256": sha256_file(repo / spec.hard_ids_file),
        "official_mini_config_sha256": sha256_file(repo / spec.official_mini_config),
    }
    if checksums:
        info["checksummed_files"] = verify_checksums(repo, spec)
    return info


# --------------------------------------------------------------------------- tasks


@dataclass(frozen=True)
class Task:
    instance_id: str
    subset: str               # "hard" (HARD-51) or "nonhard"
    task_dir: Path
    image: str                # tag reference from task.toml (resolved to a digest when the SIF is built)
    agent_timeout_sec: float
    verifier_timeout_sec: float

    @property
    def instruction(self) -> str:
        """Exactly what the official harness gives the agent (instruction.md)."""
        return (self.task_dir / "instruction.md").read_text()

    @property
    def tests_dir(self) -> Path:
        return self.task_dir / "tests"

    @property
    def gold_patch(self) -> Path:
        """Reference solution. Only the runtime gate may read this, never an agent."""
        return self.task_dir / "solution" / "gold_patch.diff"

    @property
    def repo_name(self) -> str:
        return self.instance_id.removeprefix("instance_").split("__")[0]

    def to_dict(self) -> dict[str, Any]:
        return {"instance_id": self.instance_id, "subset": self.subset, "task_dir": str(self.task_dir),
                "image": self.image, "agent_timeout_sec": self.agent_timeout_sec,
                "verifier_timeout_sec": self.verifier_timeout_sec,
                "instruction_sha256": hashlib.sha256(self.instruction.encode()).hexdigest()}


def load_tasks(repo: Path, spec: BenchmarkSpec) -> dict[str, Task]:
    hard = {l.strip() for l in (repo / spec.hard_ids_file).read_text().splitlines() if l.strip()}
    tasks: dict[str, Task] = {}
    for d in sorted((repo / spec.tasks_subdir).iterdir()):
        if not d.is_dir():
            continue
        meta = tomllib.loads((d / "task.toml").read_text())
        image = meta["environment"]["docker_image"]
        expected = spec.image_template.format(instance_id=d.name)
        if image != expected:
            raise BenchmarkPinError(f"{d.name}: task.toml image {image!r} != expected {expected!r}")
        if meta["agent"]["network_mode"] != "no-network":
            raise BenchmarkPinError(f"{d.name}: unexpected agent network mode {meta['agent']['network_mode']!r}")
        tasks[d.name] = Task(
            instance_id=d.name,
            subset="hard" if d.name in hard else "nonhard",
            task_dir=d,
            image=image,
            agent_timeout_sec=float(meta["agent"]["timeout_sec"]),
            verifier_timeout_sec=float(meta["verifier"]["timeout_sec"]),
        )
    return tasks
