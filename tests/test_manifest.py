import json

import pytest

from failure_complementarity.benchmark.swebench_pro import BenchmarkPinError, verify_benchmark_repo
from failure_complementarity.config import load_experiment
from failure_complementarity.manifest import ManifestMismatch, build_manifest, write_manifest


def test_manifest_contents(cfg):
    m = build_manifest(cfg)
    assert m["experiment_id"] == "pilot_v0"
    assert m["protocol_fingerprint"] == cfg.protocol_fingerprint()
    assert m["environment"]["packages"]["mini-swe-agent"] == "2.4.6"
    assert m["config"]["budgets"]["primary"]["wallclock_minutes"] == cfg.budgets.primary.wallclock_minutes
    assert m["protocol_doc_sha256"] and m["decisions_doc_sha256"]
    json.dumps(m)  # serialisable


def test_manifest_write_once_and_guard(cfg, tmp_path):
    d = tmp_path / "exp"
    p = write_manifest(d, build_manifest(cfg))
    first = p.read_text()
    write_manifest(d, build_manifest(cfg))  # resume with identical protocol: ok, file unchanged
    assert p.read_text() == first
    assert len((d / "manifest_sessions.jsonl").read_text().splitlines()) == 2
    changed = build_manifest(cfg) | {"protocol_fingerprint": "different"}
    with pytest.raises(ManifestMismatch):
        write_manifest(d, changed)


def test_benchmark_pin(cfg):
    repo = cfg.paths.benchmark_repo
    if not (repo / ".git").exists():
        pytest.skip("benchmark checkout not present")
    info = verify_benchmark_repo(repo, cfg.benchmark, checksums=False)
    assert info["n_tasks"] == 642 and info["n_hard"] == 51
    assert info["official_mini_config_sha256"] == cfg.source_files[cfg.prompts.miniswe_config]
    wrong = cfg.benchmark.model_copy(update={"repo_commit": "0" * 40})
    with pytest.raises(BenchmarkPinError):
        verify_benchmark_repo(repo, wrong, checksums=False)


def test_amendment_is_explicit_and_recorded(cfg, tmp_path):
    from failure_complementarity.manifest import amend_manifest
    d = tmp_path / "exp"
    write_manifest(d, build_manifest(cfg))
    changed = build_manifest(cfg) | {"protocol_fingerprint": "new"}
    with pytest.raises(ManifestMismatch):
        write_manifest(d, changed)
    amend_manifest(d, changed, "D-999", "serving capacity only")
    m = json.loads((d / "manifest.json").read_text())
    assert m["protocol_fingerprint"] == "new" and m["amendments"][0]["decision"] == "D-999"
    write_manifest(d, changed)  # accepted after the amendment
