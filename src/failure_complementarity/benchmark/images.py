"""Task images: resolve the GHCR tag to an immutable digest and build a cached SIF from that digest."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from failure_complementarity.config import sha256_file
from failure_complementarity.logging.trajectory import utc_now

_ACCEPT = ", ".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])


class ImageError(RuntimeError):
    pass


def split_ref(image: str) -> tuple[str, str, str]:
    """'ghcr.io/org/repo:tag' -> ('ghcr.io', 'org/repo', 'tag')."""
    registry, _, rest = image.partition("/")
    repo, _, tag = rest.rpartition(":")
    if not registry or not repo or not tag:
        raise ImageError(f"cannot parse image reference {image!r}")
    return registry, repo, tag


def resolve_digest(image: str, timeout: float = 60.0) -> str:
    """Anonymous registry lookup of the manifest digest behind a tag."""
    registry, repo, tag = split_ref(image)
    with httpx.Client(timeout=timeout) as c:
        tok = c.get(f"https://{registry}/token", params={"scope": f"repository:{repo}:pull"}).json()["token"]
        r = c.head(f"https://{registry}/v2/{repo}/manifests/{tag}",
                   headers={"Authorization": f"Bearer {tok}", "Accept": _ACCEPT})
        r.raise_for_status()
    digest = r.headers.get("docker-content-digest")
    if not digest or not digest.startswith("sha256:"):
        raise ImageError(f"registry returned no digest for {image}")
    return digest


def ensure_sif(image: str, instance_id: str, sif_cache: Path, apptainer_cache: Path) -> tuple[Path, dict[str, Any]]:
    """Return (sif_path, info). Builds once per task; concurrent callers wait on a file lock.

    The SIF is built from ``registry/repo@sha256:…`` so the content is pinned even if the tag moves.
    """
    sif_cache.mkdir(parents=True, exist_ok=True)
    sif = sif_cache / f"{instance_id}.sif"
    info_path = sif_cache / f"{instance_id}.json"
    with open(sif_cache / f".{instance_id}.lock", "w") as lock:
        fcntl.lockf(lock, fcntl.LOCK_EX)  # POSIX lock: cluster-wide on GPFS
        if sif.exists() and info_path.exists():
            return sif, json.loads(info_path.read_text())
        digest = resolve_digest(image)
        registry, repo, _ = split_ref(image)
        source = f"docker://{registry}/{repo}@{digest}"
        tmp = sif.with_suffix(".sif.partial")
        env = dict(os.environ, APPTAINER_CACHEDIR=str(apptainer_cache))
        t0 = time.monotonic()
        proc = subprocess.run(["apptainer", "build", "-F", str(tmp), source], env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            tmp.unlink(missing_ok=True)
            raise ImageError(f"apptainer build failed for {source}:\n{proc.stderr[-3000:]}")
        tmp.replace(sif)
        info = {"image": image, "digest": digest, "source": source, "sif": str(sif),
                "sif_sha256": sha256_file(sif), "sif_bytes": sif.stat().st_size,
                "build_seconds": round(time.monotonic() - t0, 1), "built_at": utc_now()}
        info_path.write_text(json.dumps(info, indent=2))
        return sif, info
