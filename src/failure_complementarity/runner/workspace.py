"""Capture the final repository state of a (stopped) branch rootfs: diff vs the base commit, and git status.

Decision D-005: ``git add -A`` + ``git diff --cached --binary <base_commit>`` — the official capture, but against
Repo_0's tree (agent commits are not lost; uncommitted state shipped in the image is not re-applied) and
binary-safe. Nothing in the rootfs is modified.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from failure_complementarity.fsutil import remove_tree
from failure_complementarity.runner.sandbox import SandboxError, run_oneshot

_STATUS = "git -c core.quotepath=off status --porcelain=v1 --untracked-files=all"
# New objects and temporary indexes go to a host scratch dir bound at /fc_capture; the rootfs is mounted
# read-only, so capturing cannot change the workspace (or a checkpoint taken from it).
# T0 = tree of Repo_0 (base commit + the image's own uncommitted state, /fc_capture/base.patch; usually empty),
# T1 = tree of the final worktree (git add -A semantics). The captured diff is T0 -> T1, i.e. exactly what the
# agent changed relative to Repo_0, so it applies cleanly to a fresh pristine rootfs (decision D-024).
_DIFF = (
    "set -e; export GIT_OBJECT_DIRECTORY=/fc_capture/objects "
    "GIT_ALTERNATE_OBJECT_DIRECTORIES=$(git rev-parse --absolute-git-dir)/objects; mkdir -p $GIT_OBJECT_DIRECTORY; "
    "GIT_INDEX_FILE=/fc_capture/base_index git read-tree {base}; "
    "if [ -s /fc_capture/base.patch ]; then GIT_INDEX_FILE=/fc_capture/base_index git apply --cached --binary /fc_capture/base.patch; fi; "
    "T0=$(GIT_INDEX_FILE=/fc_capture/base_index git write-tree); "
    "cp .git/index /fc_capture/index 2>/dev/null || true; "
    "GIT_INDEX_FILE=/fc_capture/index git add -A >/dev/null 2>&1; "
    "T1=$(GIT_INDEX_FILE=/fc_capture/index git write-tree); "
    "git diff --binary $T0 $T1"
)


@dataclass
class CapturedState:
    diff: bytes
    status: str
    head: str


def git_head(rootfs: Path, repo_dir: str) -> str:
    rc, out, err, _, _ = run_oneshot(rootfs, "git rev-parse HEAD", network=False, writable=False, cwd=repo_dir,
                                     timeout=120, merge_stderr=False)
    head = out.decode().strip()
    if rc != 0 or len(head) != 40:
        raise SandboxError(f"cannot read HEAD in {rootfs}:{repo_dir}: {out[-300:]!r} {err[-500:]!r}")
    return head


def capture_state(rootfs: Path, repo_dir: str, base_commit: str, scratch: Path, base_patch: bytes = b"") -> CapturedState:
    """Read-only capture of git status and of the diff from Repo_0 (``base_commit`` + ``base_patch``) to the final
    worktree (D-005, D-024)."""
    remove_tree(scratch)
    scratch.mkdir(parents=True)
    (scratch / "base.patch").write_bytes(base_patch)
    try:
        rc, status, err, _, _ = run_oneshot(rootfs, _STATUS, network=False, writable=False, cwd=repo_dir,
                                            timeout=600, merge_stderr=False)
        if rc != 0:
            raise SandboxError(f"git status failed: {err[-1000:]!r}")
        rc, diff, err, _, _ = run_oneshot(rootfs, _DIFF.format(base=base_commit), network=False, writable=False,
                                          binds=[f"{scratch}:/fc_capture"], cwd=repo_dir, timeout=600,
                                          merge_stderr=False)
        if rc != 0:
            raise SandboxError(f"git diff failed (rc={rc}): {err[-1000:]!r}")
        head = git_head(rootfs, repo_dir)
    finally:
        remove_tree(scratch)
    return CapturedState(diff=diff, status=status.decode("utf-8", errors="replace"), head=head)
