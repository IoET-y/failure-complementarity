"""Filesystem helpers that act as *user-namespace root* (``unshare -r``).

Agents run as uid 0 inside their container and may leave files/directories the host user cannot read or
traverse (mode 000). Namespace root has DAC override over files the user owns, so archiving, hashing and
deleting see every file without modifying any permission bits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

NS_ROOT = ["unshare", "-r"]


def ns_root(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([*NS_ROOT, *cmd], **kwargs)


def remove_tree(path: Path) -> None:
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return
    if len(path.resolve().parts) < 4:  # never anything like /, /tmp, /anvil/scratch
        raise ValueError(f"refusing to remove shallow path {path}")
    p = ns_root(["rm", "-rf", "--one-file-system", "--", str(path)], capture_output=True, text=True)
    if p.returncode != 0 or path.exists():
        raise OSError(f"could not remove {path}: {p.stderr[-1000:]}")


def python_as_ns_root(module: str, *args: str) -> subprocess.CompletedProcess:
    return ns_root([sys.executable, "-m", module, *args], capture_output=True, text=True)
