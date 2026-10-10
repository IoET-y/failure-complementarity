#!/usr/bin/env python3
"""Pre-flight check: config validity, benchmark pin, model endpoints; optionally write the run manifest.

    python scripts/preflight.py --config configs/pilot.yaml                     # config + benchmark only
    python scripts/preflight.py --config configs/pilot.yaml --endpoints         # + health/tool-call probe
    python scripts/preflight.py --config configs/pilot.yaml --endpoints --write-manifest

Exit code 0 only if every requested check passes.
"""

from __future__ import annotations

import argparse
import json
import sys

from failure_complementarity.agents.endpoint import check_endpoint
from failure_complementarity.benchmark.swebench_pro import verify_benchmark_repo
from failure_complementarity.config import load_experiment
from failure_complementarity.logging.structured import setup_logging
from failure_complementarity.manifest import build_manifest, write_manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--endpoints", action="store_true", help="check every experiment agent's endpoint")
    ap.add_argument("--agents", nargs="*", help="restrict the endpoint check to these agents (per-model jobs)")
    ap.add_argument("--no-tool-probe", action="store_true")
    ap.add_argument("--skip-checksums", action="store_true")
    ap.add_argument("--write-manifest", action="store_true")
    args = ap.parse_args()

    log = setup_logging()
    cfg = load_experiment(args.config)
    log.info(f"config ok: experiment={cfg.id} agents={cfg.agents} fingerprint={cfg.protocol_fingerprint()[:16]}")

    ok = True
    bench = verify_benchmark_repo(cfg.paths.benchmark_repo, cfg.benchmark, checksums=not args.skip_checksums)
    log.info(f"benchmark ok: {bench['release_tag']} @ {bench['commit'][:12]}, {bench['n_tasks']} tasks, "
             f"{bench['n_hard']} hard, checksums={bench.get('checksummed_files', 'skipped')}")
    if bench["official_mini_config_sha256"] != cfg.source_files[cfg.prompts.miniswe_config]:
        log.error("configs/miniswe prompt differs from the pinned official V2 mini_toolcall.yaml")
        ok = False

    reports = None
    if args.endpoints:
        reports = []
        for name in (args.agents or cfg.agents):
            rep = check_endpoint(cfg.agent(name), tool_probe=not args.no_tool_probe)
            reports.append(rep.to_dict())
            (log.info if rep.ok else log.error)(f"endpoint {name}: {json.dumps(rep.to_dict(), default=str)}")
            ok &= rep.ok

    if args.write_manifest and args.agents:
        reports = None  # a partial endpoint check is not recorded in the experiment manifest
    if args.write_manifest:
        if not ok:
            log.error("not writing manifest: checks failed")
            return 1
        path = write_manifest(cfg.paths.runs_root / cfg.id, build_manifest(cfg, benchmark_info=bench, endpoint_reports=reports))
        log.info(f"manifest: {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
