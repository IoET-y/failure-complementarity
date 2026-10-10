"""Milestone 3 (structural part): exact snapshot/restore of a workspace incl. state git diff would miss."""

import os
import subprocess

import pytest

from failure_complementarity.checkpoint.manifest import build_manifest, diff_manifests
from failure_complementarity.checkpoint.restore import restore_checkpoint
from failure_complementarity.checkpoint.snapshot import CheckpointError, create_checkpoint


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))


@pytest.fixture
def failed_rootfs(tmp_path):
    """A fake container rootfs after a failed agent run."""
    root = tmp_path / "rootfs"
    app = root / "app"
    app.mkdir(parents=True)
    (app / "keep.py").write_text("x = 1\n")
    (app / "delete_me.py").write_text("y = 2\n")
    (app / ".gitignore").write_text("build/\n")
    _git(app, "init", "-q")
    _git(app, "add", "-A")
    _git(app, "commit", "-qm", "base")
    (app / "keep.py").write_text("x = 1  # modified by agent\n")          # tracked modification
    (app / "delete_me.py").unlink()                                        # deletion
    (app / "new_untracked.py").write_text("z = 3\n")                       # untracked file
    (app / "build").mkdir(); (app / "build" / "gen.cfg").write_text("generated")  # ignored, generated config
    (app / "run.sh").write_text("#!/bin/sh\necho hi\n"); os.chmod(app / "run.sh", 0o755)  # exec bit
    (app / "link").symlink_to("keep.py")                                   # symlink
    os.link(app / "new_untracked.py", app / "hard")                        # hard link
    (app / "empty_dir").mkdir()                                            # empty dir
    os.mkfifo(app / "fifo")                                                # fifo
    (app / "secret").write_text("s"); os.chmod(app / "secret", 0o000)      # unreadable file
    (app / "locked").mkdir(); (app / "locked" / "f").write_text("f"); os.chmod(app / "locked", 0o000)  # untraversable dir
    (root / "tmp").mkdir(); (root / "tmp" / "repro.py").write_text("print('repro')")  # outside the repo
    (root / "usr" / "local").mkdir(parents=True); (root / "usr" / "local" / "shim").write_text("x")
    return root


def _ckpt(rootfs, out):
    return create_checkpoint(rootfs, out, task_id="t", base_commit="0" * 40, repo_dir="/app",
                             git_diff=b"diff", git_status=" M keep.py\n", threads=1)


def test_restore_twice_identical_and_equal_to_original(failed_rootfs, tmp_path):
    original = build_manifest(failed_rootfs)
    ck = _ckpt(failed_rootfs, tmp_path / "ckpt")
    assert ck.tree_hash == original.tree_hash
    ha = restore_checkpoint(ck, tmp_path / "restore_A")
    hb = restore_checkpoint(ck, tmp_path / "restore_B")
    assert ha == hb == original.tree_hash
    a = tmp_path / "restore_A"
    assert not (a / "app" / "delete_me.py").exists()
    assert (a / "app" / "new_untracked.py").read_text() == "z = 3\n"
    assert (a / "app" / "build" / "gen.cfg").exists() and (a / "tmp" / "repro.py").exists()
    assert os.readlink(a / "app" / "link") == "keep.py"
    assert os.stat(a / "app" / "hard").st_ino == os.stat(a / "app" / "new_untracked.py").st_ino
    assert os.stat(a / "app" / "run.sh").st_mode & 0o777 == 0o755
    assert os.stat(a / "app" / "secret").st_mode & 0o777 == 0o000
    assert (a / "app" / "empty_dir").is_dir()
    assert os.stat(failed_rootfs / "app" / "secret").st_mode & 0o777 == 0o000  # hashing left the mode intact
    assert os.stat(a / "app" / "locked").st_mode & 0o777 == 0o000
    assert any(e["path"] == "app/locked/f" for e in build_manifest(a).entries)


def test_mutating_one_restore_does_not_affect_the_other(failed_rootfs, tmp_path):
    ck = _ckpt(failed_rootfs, tmp_path / "ckpt")
    a, b = tmp_path / "A", tmp_path / "B"
    restore_checkpoint(ck, a)
    restore_checkpoint(ck, b)
    (a / "app" / "keep.py").write_text("changed by branch A\n")
    (a / "app" / "new_untracked.py").unlink()
    (a / "app" / "branch_a_only.txt").write_text("a")
    assert build_manifest(a).tree_hash != ck.tree_hash
    assert build_manifest(b).tree_hash == ck.tree_hash
    assert diff_manifests(build_manifest(b), build_manifest(failed_rootfs)) == []
    # and a third restore after the mutation is still pristine
    assert restore_checkpoint(ck, tmp_path / "C") == ck.tree_hash


def test_corrupted_archive_and_existing_target_rejected(failed_rootfs, tmp_path):
    ck = _ckpt(failed_rootfs, tmp_path / "ckpt")
    with pytest.raises(CheckpointError, match="already exists"):
        restore_checkpoint(ck, failed_rootfs)
    with open(ck.workspace_archive, "r+b") as f:
        f.seek(100)
        f.write(b"\x00\x01\x02")
    with pytest.raises(CheckpointError, match="checksum"):
        restore_checkpoint(ck, tmp_path / "X")


def test_manifest_detects_content_and_mode_changes(failed_rootfs):
    m0 = build_manifest(failed_rootfs)
    os.chmod(failed_rootfs / "app" / "run.sh", 0o644)
    m1 = build_manifest(failed_rootfs)
    assert m0.tree_hash != m1.tree_hash
    assert diff_manifests(m0, m1) == ["differs: app/run.sh"]
