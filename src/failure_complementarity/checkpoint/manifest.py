"""Structural + cryptographic description of a directory tree, used to prove that restores are identical.

One record per entry: relative path, type (f file, d dir, l symlink, p fifo), permission bits, size and SHA-256
(files), link target (symlinks), and a hard-link group id. Timestamps and owners are excluded (owners are always
the invoking user on the host; mtimes do not affect program behaviour we care about and tar restores them anyway).
Sockets cannot be archived and are listed separately.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TreeManifest:
    entries: list[dict] = field(default_factory=list)
    skipped_sockets: list[str] = field(default_factory=list)

    @property
    def tree_hash(self) -> str:
        h = hashlib.sha256()
        for e in self.entries:
            h.update(json.dumps(e, sort_keys=True, separators=(",", ":")).encode())
            h.update(b"\n")
        return h.hexdigest()

    def by_path(self) -> dict[str, dict]:
        return {e["path"]: e for e in self.entries}

    def write(self, path: Path) -> None:
        with open(path, "w") as f:
            for e in self.entries:
                f.write(json.dumps(e, sort_keys=True) + "\n")

    @classmethod
    def read(cls, path: Path) -> "TreeManifest":
        with open(path) as f:
            return cls(entries=[json.loads(l) for l in f if l.strip()])


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _raise(err: OSError) -> None:
    raise err


def _build_manifest_local(root: Path) -> TreeManifest:
    """Walk as the current user (inside ``unshare -r`` this sees every file the user owns)."""
    root = Path(root)
    m = TreeManifest()
    inode_groups: dict[tuple[int, int], str] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False, onerror=_raise):
        dirnames.sort()
        for name in sorted(dirnames + filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            st = os.lstat(full)
            mode = stat.S_IMODE(st.st_mode)
            if stat.S_ISDIR(st.st_mode):
                m.entries.append({"path": rel, "type": "d", "mode": mode})
            elif stat.S_ISLNK(st.st_mode):
                m.entries.append({"path": rel, "type": "l", "target": os.readlink(full)})
            elif stat.S_ISREG(st.st_mode):
                e = {"path": rel, "type": "f", "mode": mode, "size": st.st_size, "sha256": _sha256(full)}
                if st.st_nlink > 1:
                    e["hardlink_group"] = inode_groups.setdefault((st.st_dev, st.st_ino), rel)
                m.entries.append(e)
            elif stat.S_ISFIFO(st.st_mode):
                m.entries.append({"path": rel, "type": "p", "mode": mode})
            elif stat.S_ISSOCK(st.st_mode):
                m.skipped_sockets.append(rel)
            else:  # char/block devices cannot exist in an unprivileged sandbox; fail loudly if they do
                raise ValueError(f"unsupported file type in workspace: {full} (mode {oct(st.st_mode)})")
    m.entries.sort(key=lambda e: e["path"])
    return m


def diff_manifests(a: TreeManifest, b: TreeManifest, limit: int = 20) -> list[str]:
    pa, pb = a.by_path(), b.by_path()
    out = [f"only in first: {p}" for p in sorted(pa.keys() - pb.keys())]
    out += [f"only in second: {p}" for p in sorted(pb.keys() - pa.keys())]
    out += [f"differs: {p}" for p in sorted(pa.keys() & pb.keys()) if pa[p] != pb[p]]
    return out[:limit]


def build_manifest(root: Path) -> TreeManifest:
    """Manifest computed as user-namespace root, so mode-000 files/dirs left by the agent are hashed too."""
    import tempfile

    from failure_complementarity.fsutil import python_as_ns_root

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        p = python_as_ns_root("failure_complementarity.checkpoint.manifest", str(root), str(out))
        if p.returncode != 0:
            raise ValueError(f"manifest of {root} failed: {p.stderr[-3000:]}")
        m = TreeManifest.read(out)
        m.skipped_sockets = json.loads(p.stdout.strip().splitlines()[-1])["skipped_sockets"]
        return m
    finally:
        out.unlink(missing_ok=True)


if __name__ == "__main__":
    _m = _build_manifest_local(Path(sys.argv[1]))
    _m.write(Path(sys.argv[2]))
    print(json.dumps({"skipped_sockets": _m.skipped_sockets}))
