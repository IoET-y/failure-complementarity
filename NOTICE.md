# Third-party material

* `configs/miniswe/mini_toolcall_v2.0.0.yaml` is a **verbatim copy** of `v2/tooling/configs/mini_toolcall.yaml` from
  <https://github.com/scaleapi/SWE-bench_Pro-os> at commit `66f92766bba642462d4bbe5479e83f91f9211862` (tag `v2.0.0`),
  MIT License, Copyright (c) 2026 Scale AI, Inc. Its SHA-256 is checked against the benchmark checkout at start-up
  (`scripts/preflight.py`).
* The task identifiers in `configs/tasks/*.json` refer to SWE-bench Pro V2 tasks. **No benchmark task text, gold patch,
  hidden test or container image is redistributed here**; obtain them from the official repository (pinned in
  `configs/benchmark.yaml`).
* The agent harness is [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) 2.4.6 (MIT), installed as a
  dependency, not vendored.
* Model weights (Qwen, Mistral, Z.ai, NVIDIA, OpenAI checkpoints named in `configs/agents.yaml`) are downloaded from
  Hugging Face at the pinned revisions and are subject to their own licences.
