"""Create a WorkspaceCheckpoint from a stopped branch rootfs (decision D-006)."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from failure_complementarity.checkpoint.manifest import TreeManifest, build_manifest
from failure_complementarity.config import sha256_file
from failure_complementarity.fsutil import NS_ROOT
from failure_complementarity.logging.trajectory import utc_now

ARCHIVE = "workspace.tar.zst"
FILE_MANIFEST = "file_manifest.jsonl"
METADATA = "metadata.json"


class CheckpointError(RuntimeError):
    pass


@dataclass
class WorkspaceCheckpoint:
    task_id: str
    base_commit: str
    repo_dir: str
    workspace_archive: Path
    git_diff: Path
    git_status: Path
    file_manifest: Path
    tree_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: (str(v) if isinstance(v, Path) else v) for k, v in d.items()}

    @classmethod
    def load(cls, ckpt_dir: Path) -> "WorkspaceCheckpoint":
        meta = json.loads((ckpt_dir / METADATA).read_text())
        return cls(task_id=meta["task_id"], base_commit=meta["base_commit"], repo_dir=meta["repo_dir"],
                   workspace_archive=ckpt_dir / ARCHIVE, git_diff=ckpt_dir / "git_diff.patch",
                   git_status=ckpt_dir / "git_status.txt", file_manifest=ckpt_dir / FILE_MANIFEST,
                   tree_hash=meta["tree_hash"], metadata=meta)


def _tar_create(rootfs: Path, archive: Path, threads: int) -> str:
    """tar the whole rootfs (numeric ids, permissions, hard links) piped through zstd. Returns tar stderr."""
    tmp = archive.with_name(archive.name + ".partial")
    with open(tmp, "wb") as out:
        tar = subprocess.Popen([*NS_ROOT, "tar", "-C", str(rootfs), "--numeric-owner", "-cpf", "-", "."],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        zst = subprocess.Popen(["zstd", "-q", f"-T{threads}", "-3", "-c"], stdin=tar.stdout, stdout=out)
        tar.stdout.close()
        _, tar_err = tar.communicate()
        zst.wait()
    err = tar_err.decode(errors="replace")
    # GNU tar exits 1 for "socket ignored"; anything else is fatal
    unexpected = [l for l in err.splitlines() if l.strip() and "socket ignored" not in l]
    if zst.returncode != 0 or tar.returncode not in (0, 1) or (tar.returncode == 1 and unexpected):
        tmp.unlink(missing_ok=True)
        raise CheckpointError(f"archive failed: tar={tar.returncode} zstd={zst.returncode}: {err[-2000:]}")
    tmp.replace(archive)
    return err


def create_checkpoint(
    rootfs: Path, out_dir: Path, *, task_id: str, base_commit: str, repo_dir: str,
    git_diff: bytes, git_status: str, extra: dict[str, Any] | None = None, threads: int = 4,
) -> WorkspaceCheckpoint:
    """Archive ``rootfs`` exactly as it is. The caller guarantees nothing is running on it."""
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    manifest = build_manifest(rootfs)
    manifest.write(out_dir / FILE_MANIFEST)
    tar_warnings = _tar_create(rootfs, out_dir / ARCHIVE, threads)
    (out_dir / "git_diff.patch").write_bytes(git_diff)
    (out_dir / "git_status.txt").write_text(git_status)
    meta = {
        "task_id": task_id, "base_commit": base_commit, "repo_dir": repo_dir, "tree_hash": manifest.tree_hash,
        "n_entries": len(manifest.entries), "skipped_sockets": manifest.skipped_sockets,
        "archive_sha256": sha256_file(out_dir / ARCHIVE), "archive_bytes": (out_dir / ARCHIVE).stat().st_size,
        "tar_warnings": tar_warnings[-2000:], "created_at": utc_now(), "seconds": round(time.monotonic() - t0, 1),
        **(extra or {}),
    }
    (out_dir / METADATA).write_text(json.dumps(meta, indent=2))
    return WorkspaceCheckpoint.load(out_dir)
