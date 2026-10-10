"""Experiment manifest: resolved config + every version that can affect results.

``runs/<experiment_id>/manifest.json`` is written once. Later sessions (resume) must have the same
protocol fingerprint; otherwise the run refuses to start, so a protocol change cannot slip silently into an
existing experiment (it needs a new experiment id and a decisions.md entry). Every session is appended to
``manifest_sessions.jsonl``.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from failure_complementarity.config import ExperimentConfig, sha256_file
from failure_complementarity.logging.trajectory import utc_now

MANIFEST_SCHEMA = 1
PACKAGES = ["failure-complementarity", "mini-swe-agent", "litellm", "openai", "pydantic", "httpx", "zstandard", "PyYAML"]
SLURM_VARS = ["SLURM_JOB_ID", "SLURM_JOB_NAME", "SLURM_JOB_NODELIST", "SLURM_JOB_PARTITION", "SLURM_JOB_ACCOUNT",
              "SLURM_CPUS_ON_NODE", "SLURM_GPUS_ON_NODE", "CUDA_VISIBLE_DEVICES"]


class ManifestMismatch(RuntimeError):
    pass


def _run(cmd: list[str], cwd: Path | None = None) -> str | None:
    if shutil.which(cmd[0]) is None:
        return None
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    except Exception:
        return None


def git_info(repo: Path) -> dict[str, Any]:
    commit = _run(["git", "-C", str(repo), "rev-parse", "HEAD"])
    status = _run(["git", "-C", str(repo), "status", "--porcelain"])
    return {"commit": commit, "dirty": bool(status) if status is not None else None}


def package_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for p in PACKAGES:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = None
    return out


def gpu_info() -> dict[str, Any] | None:
    q = _run(["nvidia-smi", "--query-gpu=index,name,driver_version,memory.total,uuid", "--format=csv,noheader"])
    if q is None:
        return None
    header = _run(["nvidia-smi"]) or ""
    cuda = next((l.split("CUDA Version:")[1].split()[0] for l in header.splitlines() if "CUDA Version:" in l), None)
    return {"gpus": [l.strip() for l in q.splitlines()], "cuda_driver_api": cuda}


def environment_info() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "cpu_count": os.cpu_count(),
        "packages": package_versions(),
        "apptainer": _run(["apptainer", "--version"]),
        "slurm": {k: os.environ[k] for k in SLURM_VARS if k in os.environ},
        "gpu": gpu_info(),
    }


def build_manifest(
    cfg: ExperimentConfig,
    *,
    benchmark_info: dict[str, Any] | None = None,
    endpoint_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    project_root = cfg.project_root
    return {
        "schema": MANIFEST_SCHEMA,
        "experiment_id": cfg.id,
        "created_at": utc_now(),
        "protocol_fingerprint": cfg.protocol_fingerprint(),
        "protocol_doc_sha256": _sha_or_none(project_root / "docs" / "experiment_protocol.md"),
        "decisions_doc_sha256": _sha_or_none(project_root / "docs" / "decisions.md"),
        "project_git": git_info(project_root),
        "config": cfg.resolved_dict(),
        "environment": environment_info(),
        "benchmark": benchmark_info,
        "endpoints": endpoint_reports,
    }


def _sha_or_none(p: Path) -> str | None:
    return sha256_file(p) if p.is_file() else None


def amend_manifest(experiment_dir: Path, manifest: dict[str, Any], decision: str, reason: str) -> Path:
    """Accept a new protocol fingerprint for an existing experiment, explicitly and on the record.

    Only for changes documented in docs/decisions.md under ``decision``; the previous fingerprint, the decision id
    and the reason are kept in ``amendments``. Runs record the fingerprint they ran under, so analyses can tell
    which runs preceded the amendment.
    """
    path = experiment_dir / "manifest.json"
    existing = json.loads(path.read_text())
    if existing["protocol_fingerprint"] == manifest["protocol_fingerprint"]:
        return path
    existing.setdefault("amendments", []).append({
        "decision": decision, "reason": reason, "at": utc_now(),
        "from": existing["protocol_fingerprint"], "to": manifest["protocol_fingerprint"],
        "config": manifest["config"],
    })
    existing["protocol_fingerprint"] = manifest["protocol_fingerprint"]
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(existing, indent=2, sort_keys=True))
    tmp.replace(path)
    return path


def write_manifest(experiment_dir: Path, manifest: dict[str, Any]) -> Path:
    """Create the manifest, or check the existing one and append a session record."""
    experiment_dir.mkdir(parents=True, exist_ok=True)
    path = experiment_dir / "manifest.json"
    if path.exists():
        existing = json.loads(path.read_text())
        if existing["protocol_fingerprint"] != manifest["protocol_fingerprint"]:
            raise ManifestMismatch(
                f"{path} was created with protocol fingerprint {existing['protocol_fingerprint']}, current config "
                f"has {manifest['protocol_fingerprint']}. Use a new experiment id and record the change in "
                "docs/decisions.md."
            )
    else:
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        tmp.replace(path)
    with open(experiment_dir / "manifest_sessions.jsonl", "a") as f:
        f.write(json.dumps(manifest, sort_keys=True, default=str) + "\n")
    return path
