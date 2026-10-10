"""Restore a WorkspaceCheckpoint into a fresh directory and PROVE it equals the snapshot."""

from __future__ import annotations

import subprocess
from pathlib import Path

from failure_complementarity.checkpoint.manifest import TreeManifest, build_manifest, diff_manifests
from failure_complementarity.checkpoint.snapshot import CheckpointError, WorkspaceCheckpoint
from failure_complementarity.config import sha256_file
from failure_complementarity.fsutil import NS_ROOT


def restore_checkpoint(ckpt: WorkspaceCheckpoint, dest: Path, *, verify: bool = True) -> str:
    """Extract into ``dest`` (must not exist). Returns the restored tree hash; raises on any mismatch."""
    if dest.exists():
        raise CheckpointError(f"restore target already exists: {dest}")
    if sha256_file(ckpt.workspace_archive) != ckpt.metadata["archive_sha256"]:
        raise CheckpointError(f"archive checksum mismatch: {ckpt.workspace_archive}")
    dest.mkdir(parents=True)
    zst = subprocess.Popen(["zstd", "-q", "-d", "-c", str(ckpt.workspace_archive)], stdout=subprocess.PIPE)
    tar = subprocess.run([*NS_ROOT, "tar", "-C", str(dest), "--numeric-owner", "-xpf", "-"], stdin=zst.stdout,
                         capture_output=True)
    zst.stdout.close()
    zst.wait()
    if zst.returncode != 0 or tar.returncode != 0:
        raise CheckpointError(f"extract failed: zstd={zst.returncode} tar={tar.returncode}: {tar.stderr[-2000:]!r}")
    if not verify:
        return ""
    restored = build_manifest(dest)
    if restored.tree_hash != ckpt.tree_hash:
        expected = TreeManifest.read(ckpt.file_manifest)
        raise CheckpointError(f"restored tree differs from checkpoint: {diff_manifests(expected, restored)}")
    return restored.tree_hash
