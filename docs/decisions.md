# Decision Log

Every protocol binding or change is recorded here with date and reason (integrity rule 10).
Status: **ACCEPTED** (in force), **OPEN** (needs PI decision; current default stated), **SUPERSEDED**.

---

## D-001 — Benchmark version pin (2026-10-06, ACCEPTED)

SWE-bench Pro V2 = release **v2.0.0** of `https://github.com/scaleapi/SWE-bench_Pro-os`,
commit `66f92766bba642462d4bbe5479e83f91f9211862` (tag `v2.0.0`, 2026-09-22). 642 tasks / 11 repos; HARD-51
from `v2/hard51_ids.txt`. Tasks are read from `v2/tasks/<instance_id>/` (Harbor format: `instruction.md`,
`task.toml`, `tests/`, `solution/`) because that is exactly what the official verifier consumes;
`v2/SHA256SUMS` is verified at load time. The HF mirror `ScaleAI/SWE-bench_Pro` (config `default` = V2,
`hard` = HARD-51) was at revision `2d52cb3df914a3fcf80c7f66738b3a88ae37fc50` on 2026-10-06; it is recorded
for reference only.

*Reason:* the spec requires the official benchmark and pinned versions.

## D-002 — Apptainer instead of Docker/Modal (2026-10-06, ACCEPTED)

The cluster (Purdue Anvil) has no Docker daemon and no Modal access; Apptainer 1.5.3 is available.
V2 images `ghcr.io/scaleapi/swe-bench_pro-v2:<instance_id>` are converted once to SIF (cached, digest
recorded). Each branch runs in a private **writable sandbox directory** unpacked from the SIF onto node-local
disk, with `--fakeroot` (uid 0 inside, like Docker), `--containall --cleanenv --no-home --no-mount tmp`.

Verified on 2026-10-06 with `instance_NodeBB__NodeBB-8168c6c4…`:
uid 0; `/app` mutable; deletions and `/tmp` writes persist inside the rootfs; background processes persist
across commands within an instance; image environment variables preserved; `--net --network none` blocks
network; the pristine base is untouched.

Rejected alternatives (tested):
* SIF + `--overlay` (dir or ext3 image) with `--fakeroot`: copy-up of existing files fails
  (`EOVERFLOW`/`EACCES`, squashfuse uid mapping). Without `--fakeroot` it works but runs as non-root, which
  differs from the official (root) environment.
* Directory overlay as checkpoint: kernel whiteouts are char devices `0:0` that an unprivileged process cannot
  recreate on restore.

*Risk:* subtle runtime differences from Docker. Mitigated by D-003.

## D-003 — Runtime validity gate (2026-10-06, ACCEPTED)

Before any model is run on a task, the task must reproduce the official release gate **under our runtime**:
gold patch → `SOLVED`, empty patch → `UNSOLVED`. Tasks failing the gate are excluded and listed with the
reason. The gate is outcome-blind (no model has been run), so it cannot bias selection toward either model.

Verified on 2026-10-06 for `instance_NodeBB__NodeBB-8168c6c4…`: gold → reward 1 (311/311 required tests),
empty → reward 0 (307/311).

## D-004 — Harness binding (2026-10-06, ACCEPTED)

mini-SWE-agent **2.4.6** (PyPI, latest on 2026-10-06), `DefaultAgent` + `LitellmModel` (tool-calling, single
`bash` tool). The LLM loop runs on the host; each bash action is executed inside the branch's persistent
Apptainer instance (`apptainer exec instance://…`). This mirrors the official
`v2/tooling/host_mini_swe.py` and gives the sandbox **no network** (V2 locked protocol: agent phase offline
except for the model endpoint).

Prompt: the official V2 `v2/tooling/configs/mini_toolcall.yaml` (system/instance/observation/format-error
templates), copied verbatim to `configs/miniswe/` with its SHA-256 checked against the pinned benchmark repo.
The V2 file sets `model_kwargs.reasoning_effort: high` and `cost_limit: 3.0`; these are provider-specific
(Anthropic/OpenAI pricing) and are not applied to local open-weight models (cost is 0; `reasoning_effort` is
ignored/dropped). The budget is governed by D-007.

## D-005 — Evaluation binding (2026-10-06, ACCEPTED)

Following the V2 locked protocol (`patch_replay.py`), the evaluator never runs in the agent's sandbox:
the final diff is captured and applied to a **fresh pristine** rootfs, then the unchanged `tests/test.sh` runs
with network enabled (verifier phase `network_mode = "public"`). Reward file `/logs/verifier/reward.txt`
∈ {0,1}.

Two deliberate strengthenings of the capture command (`git add -A && git diff --cached`):
1. the diff is taken against the **recorded base commit** of `Repo_0`, not `HEAD`, so commits made by an
   agent are not silently dropped;
2. `--binary` is used so binary-file changes survive.
For agents that never commit and change only text files the result is byte-identical to the official capture.

Consequence for rescue branches: a rescue run is graded on the full diff of its final workspace vs `Repo_0`'s
base commit, i.e. on the final repository state regardless of who made which edit.

## D-006 — Checkpoint format (2026-10-06, ACCEPTED)

`Repo_t^A` := the **entire root filesystem** of A's branch sandbox at the moment the primary run ends
(after the agent process is stopped, before anything else touches it). That is a superset of the workspace:
it includes `/app` (tracked, untracked, ignored, deleted files, `.git`), `/tmp`, and any other change.
Stored as `workspace.tar.zst` + `git_diff.patch` + `git_status.txt` + `file_manifest.jsonl` (path, type,
mode, size, sha256, link target) + `metadata.json`. Restores are verified by recomputing the file manifest.
Disk cost is accepted for V0 (correctness over efficiency).

## D-007 — Budgets (2026-10-06, ACCEPTED — PI approved 2026-10-06)

Identical for all models and phases; values from `configs/budgets.yaml`:

* wall-clock: `primary 30 min`, `recovery 30 min` (spec example; the official V2 protocol uses 50 min — PI kept
  30 min for the pilot);
* **step cap: 250 model calls per run, both phases, both models** (PI asked for a "reasonable" uniform cap on
  2026-10-06). 250 is mini-SWE-agent's own SWE-bench default (`config/benchmarks/swebench.yaml`, `step_limit:
  250`), i.e. the standard interaction budget of this harness. It was fixed before any model outcome was seen and
  is not tuned on outcomes. Whichever of wall-clock / step cap is hit first ends the run; the exit reason records
  which one (`*_TIMEOUT` or `STEP_LIMIT`; both count as "budget reached" for §4).
  Rationale: Qwen3-Coder-30B-A3B (≈3B active) decodes much faster than dense Devstral-24B, so under a pure
  wall-clock budget it would get many more interaction steps; a step cap bounds that asymmetry while staying
  loose enough not to truncate normal trajectories (typical successful mini-SWE-agent trajectories on SWE-bench
  use well under 100 steps). How often each limit binds is reported per model after calibration; the cap is not
  changed mid-experiment.
* per-command timeout 60 s (mini-SWE-agent SWE-bench default; official host-side V2 runner default);
* per-response `max_tokens` 16384 (identical; bounds a degenerate generation; a truncated response becomes a
  normal mini-SWE-agent format-error observation).

## D-008 — Sampling parameters (2026-10-06, ACCEPTED — PI approved 2026-10-06)

Each model uses its vendor-recommended sampling (from the model cards / `generation_config.json`):
Qwen3-Coder `temperature 0.7, top_p 0.8, top_k 20, repetition_penalty 1.05`; Devstral Small 2 `temperature
0.15`. Both models are served with the same `max_model_len`. Treating sampling as part of "the model" keeps
each model at its intended operating point; forcing one temperature on both would disadvantage one of them.

## D-009 — Early-submission failures (2026-10-06, ACCEPTED — PI kept the literal definition 2026-10-06)

The spec defines a primary failure as "budget reached **and** unsolved". Agents frequently *submit* an
incorrect fix before the budget runs out. Read literally, such runs are not primary failures and would be
excluded from the recovery set.
Current implementation: every run records its exit reason (`SUBMITTED`, `PRIMARY_TIMEOUT`, …) and its
evaluator result. The failure-set definition is the config switch
`primary_failure.definition` ∈ {`budget_exhausted_and_unsolved` (literal spec, **default**),
`unsolved_any_exit`}. The PI kept the literal default on 2026-10-06. Runs ending by submission while unsolved are therefore not entered into the recovery set, but are kept, evaluated and reported.

## D-010 — Prompt for the Repo_0 control (2026-10-06, ACCEPTED)

Condition C starts from the pristine repository, so the "previous agent attempted this task" sentence would be
false. Condition C therefore uses the primary prompt, i.e. it is exactly an independent primary run of B.
Note: the spec's calibration runs (Repo_0 → B) are distributionally identical to condition C, but condition C
is still executed as its own branch per failed task (fresh run), so it is not reused from calibration.

## D-011 — Task selection rule (2026-10-06, ACCEPTED)

Outcome-blind, seeded sampling fixed before any model is run: shuffle HARD-51 and non-HARD V2 (591 tasks)
with a recorded seed; walk each list in order, keep tasks that pass the runtime gate (D-003) until 10 per
stratum. The resulting ID list is committed to `configs/` before calibration starts. If calibration shows the
mix is outside the target solve-rate range, the HARD fraction is changed as the spec allows, and that change is
logged here.

## D-012 — Infrastructure-failure retries (2026-10-06, ACCEPTED)

A run classified `INFRA_FAILURE` (`MODEL_ERROR`, `HARNESS_ERROR`, `CONTAINER_ERROR`, `EVALUATOR_ERROR`) may be
retried; the same retry policy applies to every model and condition; every attempt is kept in
`attempt_<k>/`. A `TASK_FAILURE` is never retried. Context-window overflow and repeated malformed tool calls
are model behaviour under a fixed serving configuration and are recorded as task failures with their own exit
reason (`CONTEXT_LIMIT`, `FORMAT_ERROR_LIMIT`), so they can be inspected separately.

## D-013 — Fixed per-endpoint concurrency (2026-10-06, ACCEPTED)

Agent speed — and therefore what a wall-clock budget buys — depends on how many agents share an inference
server. Each model gets its own server on identical hardware (2× H100, TP=2), and the runner enforces the same
maximum number of concurrent agents per endpoint (`runtime.max_concurrent_per_endpoint`) for every model.
Per-run decode throughput (output tokens / model-call seconds) is recorded so load effects can be checked.

## D-014 — Model-endpoint errors during a run (2026-10-06, ACCEPTED)

mini-SWE-agent retries failed model calls up to 10 times with exponential back-off (minutes). Time lost to an
unhealthy server would silently shrink the agent's budget. Therefore any connection error, timeout or 5xx from the
endpoint during a run marks the run `MODEL_ERROR` (infrastructure; retried per D-012), even if a later retry
succeeded. Requests rejected because the prompt exceeds the context window are `CONTEXT_LIMIT` (task failure,
D-012) and are not retried.

## D-015 — Verifier timeout (2026-10-06, ACCEPTED)

The verifier runs with the task's official timeout (3000 s). A timeout is classified `UNSOLVED` with
`verifier_timed_out=true` (the official harness also yields no reward), because every gated task's gold and
empty-patch verifications complete far inside the limit (D-003), so a timeout is attributable to the patch
(e.g. an infinite loop). Any other verifier malfunction (no reward file, container failure) is
`EVALUATOR_ERROR`.

## D-016 — Pre-registered rule for starting the recovery stage (2026-10-06, ACCEPTED)

Written before any real model run. After the Phase-0 calibration primaries finish, the recovery stage (§5) starts
automatically **only if** for each model: (i) at most 2 of the 20 primary runs are infrastructure failures,
(ii) its solve rate on the valid runs lies in the protocol's target range **[20%, 70%]**, and (iii) it has at
least **3 primary failures** under the §4 definition. Otherwise the job stops, and the task mix is revised
as §3 allows (HARD fraction up or down), with a new decision entry and a new frozen task list, **before** any
recovery branch is run. The rule uses only primary (calibration) outcomes, never rescue outcomes.

## D-017 — Validation runs are separate from the experiment (2026-10-06, ACCEPTED)

Milestones 2 and 4 with real models run as experiment `validation_v0` on held-out HARD tasks that are not in the
calibration list (NodeBB `8168c6c4…` plus the last task of the seeded HARD order). Their results are only used to
check the pipeline (start-state hashes, isolation, evaluation) and are never pooled with `pilot_v0`.

## D-018 — Processes are not part of a checkpoint (2026-10-06, ACCEPTED)

`Repo_t^A` is the complete *filesystem* state of A's container. Processes A started (servers, background jobs)
are stopped before the checkpoint and do not exist in rescue branches; a rescuer has to restart anything it needs,
as any fresh agent would. Verified with a scripted agent: a background `sleep` and `redis-server` running at the
end of the primary are absent in the rescue containers, while every file (incl. a mode-000 file in /tmp) is present.
Repo_0 is also stored as an archive (`pristine/`), so Repo_0 and Repo_t^A branches use the same verified-restore
path (unpacking the SIF per branch is not byte-reproducible: Apptainer stamps a build date into
`/.singularity.d/labels.json`).

## D-019 — One 2-GPU job per model; H100 only (2026-10-06, ACCEPTED)

Whole 4-GPU nodes are rarely free on the `ai` partition. Every branch needs exactly one model (recovery A→B and
control B need only B; `Repo_t^A` is a file archive), so the work is split into one job per model: its server on
2× H100 with TP=2 (unchanged from D-013) plus a worker that runs only that model's branches, stage by stage, with
barriers on the other model's progress (validation primaries → validation recovery → validation check →
calibration primaries → D-016 → calibration recovery). Per-endpoint concurrency stays identical. Every job
verifies that its GPUs are H100 and refuses to run otherwise, so the two models never run on different hardware
(the allocation has no A100 access anyway: the association is restricted to partition `ai`).

## D-020 — One H100 per model; official FP8 checkpoints for both (2026-10-06, ACCEPTED — PI asked for smaller jobs)

Supersedes the TP=2 part of D-013/D-019 and the Qwen checkpoint of D-001-era configs (no experiment run had used
them). Each model is served on **one H100 (TP=1)**, with 16 CPU cores and 128 GB RAM per job.
* Devstral Small 2: the official release `mistralai/Devstral-Small-2-24B-Instruct-2512` is itself **FP8**
  (`quant_method: fp8`, 25.8 GB) — unchanged.
* Qwen3-Coder: the BF16 checkpoint (61 GB) leaves only ~8 GB of KV cache on one H100, less than one 131k-token
  context. We therefore use Qwen's **official FP8 release** `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` @
  `dcaee4d4dfc5ee71ad501f01f530e5652438fde0` (fine-grained block-128 FP8, published by Qwen; same architecture,
  tokenizer, chat template and tool parser).
Both models now run at their vendors' own FP8 precision on identical hardware, with the same `max_model_len`
(131072) and per-endpoint concurrency (4). KV-cache capacity at 0.90 memory utilisation: ≈400k tokens (Qwen),
≈280k tokens (Devstral) — each holds ≥2 full-length contexts.

## D-021 — Primary failure = unsolved at the end of the primary run, whatever the exit (2026-10-07, ACCEPTED — PI approved)

Supersedes the D-009 default. Observation from `validation_v0` and `pilot_v0` calibration (all primaries so far):
every run ended because the agent **submitted** (Qwen median ≈61 steps / 86 s; Devstral ≈45–65 steps / ≈5 min),
none reached the 30 min / 250-step budget. Under the literal definition ("budget reached and unsolved") the
recovery set would be empty and the study could not be run. The workspace left by an agent that submitted a
wrong fix is exactly the failed workspace the research question is about, and §4's purpose (a deterministic
definition without a learned stagnation detector) is kept: a run is a primary failure iff it ends — by
submission, budget, step cap, format-error limit or context limit — and the official evaluator marks it
unsolved. Infrastructure failures remain excluded. Config: `primary_failure.definition: unsolved_any_exit`.
Exit reasons stay recorded, so the budget-exhausted subset can still be reported separately.
Applied through new experiment ids (`validation_v1`, `pilot_v1`); `pilot_v0` and `validation_v0` are kept
unchanged as records of the earlier definition.

## D-022 — v1 task mix: non-HARD V2 only, 40 tasks (2026-10-07, ACCEPTED — delegated by PI)

`pilot_v0` calibration (official mini-SWE-agent setup, 30 min / 250 steps): HARD-51 0/10 for Qwen and 0/10 for
Devstral; non-HARD 0/10 for Qwen, 3/6 for Devstral at the time of the decision (6 runs still finishing). §3:
"If HARD-51 is nearly impossible for both models, move toward easier V2 tasks." The v1 set therefore uses only
the non-HARD stratum — the easiest pool V2 offers. Because solve rates are low, more tasks are needed for usable
failure/rescue counts; `pilot_v1` takes the first **40** non-HARD tasks of the same seeded order
(seed 20261006) that pass the runtime gate. Selection remains outcome-blind: the order was fixed before any run,
and the 10 non-HARD tasks already run in `pilot_v0` are the first 10 of that order, not chosen for their outcomes.
Final `pilot_v0` calibration (all 40 runs ended by submission): Qwen 0/10 HARD, 0/10 non-HARD; Devstral 0/10 HARD,
4/10 non-HARD.

## D-023 — Recovery start rule for v1 (2026-10-07, ACCEPTED — before any v1 run)

D-016's solve-rate window [20%, 70%] cannot be met by Qwen on any V2 subset (0/20 in `pilot_v0`, incl. 0/10
non-HARD), and the only adjustment §3 provides (the HARD fraction) is already at 0. The window is therefore no
longer a stop condition for `pilot_v1`; solve rates are reported. Recovery starts iff for each model:
(i) infrastructure failures ≤ 10% of its primary runs and (ii) at least 5 primary failures (D-021 definition).
Implemented as `scripts/check_calibration_gate.py --rule v1`.

## D-024 — Diffs are taken relative to Repo_0's tree, not HEAD (2026-10-07, ACCEPTED)

Some V2 images ship untracked state inside the repository (e.g. NodeBB `397835a0…` has a redis `appendonlydir/`
created at image build time). That state is part of Repo_0. A HEAD-relative capture (the official
`git add -A && git diff --cached`) would include it in every model patch, and replaying such a patch on the pristine
image — which already contains those files — fails to apply. The capture now builds T0 = base commit + the
image's own uncommitted state (stored once per task as `pristine/git_diff.patch`, usually empty) and
T1 = final worktree, and records `git diff --binary T0 T1`: exactly the agent's change relative to Repo_0.
For images with no uncommitted state (all tasks run before this date) the result is byte-identical to the
previous capture. Verified on the NodeBB image: untouched Repo_0 → empty diff; an edit + new file + deletion →
exactly those three files; the evaluator applies it cleanly (apply rc 0). The earlier sanity check that refused
such tasks was what stopped the v1 jobs on 2026-10-07 10:24; no run was affected.

## D-025 — Host SIGKILL (OOM) of an agent command or verifier is an infrastructure failure (2026-10-07, ACCEPTED)

The Devstral job of 2026-10-07 (21163811, 128 GB) recorded 2 cgroup OOM-kill events. Audit of every run in all
experiments: exactly one trace — `pilot_v1` element-web `53a9b644…` `recovery_qwen_to_devstral`, step 33: a plain
`cat > file <<EOF` command returned rc −9 after 34.6 s (no timeout), while three Devstral branches of that same
element-web task were running Jest concurrently. No verifier log and no Qwen run shows a kill signal; the two
events are consistent with one incident (the `apptainer exec` client and its starter process).
Rule (uniform, all models): returncode −9 on the host side without our own timeout ⇒ `CONTAINER_ERROR` (agent
command) or `EVALUATOR_ERROR` (verifier) ⇒ retried under D-012. Applied retroactively with
`scripts/apply_d025.py` (original fields kept under `reclassified.original`); the affected branch is rerun as
attempt 2. Prevention: model jobs now request 240 GB (a quarter of a node's RAM, matching one of four GPUs).

## D-026 — Context-transfer pilot and same-model Repo_0 control (2026-10-07, ACCEPTED — PI approved, runs in parallel with D-027)

`pilot_v1` result: HRG_{Q→D} = +0.27 (McNemar p ≈ 0.008) but FTV_{Q→D} ≈ −0.03 (95% paired CI ≈ [−0.23, +0.16]):
the cross-model gain is largely the rescuer's capability, not the failed workspace. Spec §7/§23 deferred
context transfer; the PI approved starting it now, in parallel with the search for a matched pair (D-027).
Experiment `ctx_v1` reuses the `pilot_v1` primaries and checkpoints (same Repo_t^A, so all comparisons with
`pilot_v1` branches are paired by task) and adds, for every `pilot_v1` primary failure of A:
* **handoff note**: A (fresh request to A's own model, given A's final primary conversation) writes a short
  handoff note (prompt `prompts/handoff_request_v1.md`); the note is generated once per (task, A);
* `recovery_note_<A>_to_<B>` for every B (incl. A): B on Repo_t^A with recovery prompt + note
  (`prompts/recovery_note_v1.md`); everything else as in V0;
* `control_<A>_repo0` (same-model Repo_0 control, "condition D"): fresh A on Repo_0, primary prompt, recovery
  budget. With it, HRG_{A→B} = [P(B✓|Repo_0) − P(A✓|Repo_0)] + [FTV_{A→B} − FTV_{A→A}] on A's failures.
The note contains no chain-of-thought (only the model's answer to the handoff request). `ctx_v1` reuses the
`pilot_v1` Repo_0 archives byte-for-byte (hard links), so all conditions start from identical bytes.

## D-027 — Screening for a capability-matched pair (2026-10-07, ACCEPTED — PI asked for comparable models)

The Qwen3-Coder-30B/Devstral pair is unbalanced (22.5% vs 60%; calibration 2×2 has 0 tasks solved by Qwen
only), which confounds HRG with capability and leaves the weak→strong direction at the floor. Candidates that
fit 2× H100, verified on Hugging Face and supported natively by vLLM 0.31.0 (architecture + tool parser):
`Qwen/Qwen3-Coder-Next-FP8` @ `da6e2ed2…` (parser `qwen3_coder`), `openai/gpt-oss-120b` @ `b5c939de…`
(MXFP4, parser `openai`, default reasoning effort), `zai-org/GLM-4.7-Flash` @ `7dd20894…` (BF16, parser `glm47`,
reasoning parser `glm45`). Each is served on 2× H100 (TP=2) with its vendor sampling settings, same harness,
prompts, budgets, max_model_len and concurrency, and runs the 40 `pilot_v1` primaries in experiment
`screen_v1`. A pair is then chosen for (i) close solve rates and (ii) non-empty discordant cells in the paired
2×2. The chosen pair's main experiment re-runs its primaries fresh (avoids selecting on the same noisy runs).
Note: hardware per model is then 2 GPUs (vs 1 for Devstral/Qwen3-Coder-30B); runs almost never reach the
wall-clock budget (0 of 80 in `pilot_v1`), so this does not change effective budgets; the final pair will be run
on identical hardware.

## D-028 — Screening restricted to single-H100 models (2026-10-07, ACCEPTED — PI: 2-GPU jobs queue too long)

Amends D-027 before any screening run. 2-GPU jobs wait much longer on the `ai` partition, so every candidate is
served on **one H100** like Devstral/Qwen3-Coder-30B (identical hardware for any pair drawn from the pool).
Dropped: Qwen3-Coder-Next-FP8 (80 GB, does not fit one H100). Kept on one GPU: GLM-4.7-Flash (62 GB BF16, MLA KV
≈54 KB/token; memory utilisation 0.92) and gpt-oss-120b (65 GB MXFP4; 0.95). Added, verified on Hugging Face and
in vLLM 0.31.0 (architecture, tool parser, reasoning parser):
`Qwen/Qwen3.6-35B-A3B-FP8` @ `95a723d0…`, `Qwen/Qwen3.6-27B-FP8` @ `e89b16eb…` (thinking models, default
mode, `--reasoning-parser qwen3`, `--language-model-only`, card SWE-bench sampling T=1.0/top_p 0.95/top_k 20),
`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` @ `9bee1944…` (`--reasoning-parser nemotron_v3`, card tool-calling
sampling T=0.6/top_p 0.95). Vendor-reported SWE-bench numbers come from their own scaffolds and are not used for
selection; selection uses only our `screen_v1` primaries. Reasoning content is never passed to another agent
(rescuers receive no trajectory; handoff notes strip it).

## D-029 — Job size (2026-10-07, ACCEPTED)

Model jobs request 8 CPU cores (was 16). Memory cannot be lowered: the `ai` partition enforces 240 GB per GPU
(`JobDefaults=DefMemPerGPU=240000`, applied by the site's submit plugin even when `--mem` is smaller). Per-endpoint
concurrency therefore stays at 4 (D-013) in every experiment; a brief edit to 2 in `screen_v1`/`ctx_v1` was
reverted before any run. Queue waits are due to node memory being fully allocated on nodes with idle GPUs.

## D-030 — Dynamic endpoint port per job (2026-10-07, ACCEPTED)

GPU nodes are shared; the Qwen3.6-35B-A3B screening job (21176560) failed at start with `Address already in use`
on its fixed port. Each model job now binds a free port at start, serves the model there, and exports
`FC_ENDPOINT_<AGENT>`, which overrides that agent's `base_url` for every process of the job. Endpoint locations are
not part of the protocol fingerprint, so no experiment definition changes. The failed job produced no run.

## D-031 — `screen_v1` amendment: `--max-num-seqs 64` for the Qwen3.6 models (2026-10-07, ACCEPTED)

Qwen3.6-27B (hybrid attention) cannot start with vLLM's default `max_num_seqs=1024` on one H100 (only 801 Mamba
cache blocks). Both Qwen3.6 entries now pass `--max-num-seqs 64`; our endpoints never carry more than 4 concurrent
requests, so model outputs are unaffected. Because serve settings are part of the fingerprint, the `screen_v1`
manifest (created at 22:37 by the Nemotron job) refused the next job. The change is applied as an explicit,
recorded amendment (`manifest.amend_manifest`, kept under `amendments` with old/new fingerprints); no Qwen3.6 run
existed before it. New mechanism: a fingerprint change for an existing experiment is accepted only through such a
recorded amendment that names a decision entry.

## D-032 — Exceptions while executing an agent command become observations (2026-10-08, ACCEPTED)

Harness bug: a NUL byte in an agent's command made `subprocess` raise `ValueError: embedded null byte`, which our
`ApptainerEnvironment` let escape, ending the run as `HARNESS_ERROR`. mini-SWE-agent's own environments convert
any exception during execution into an observation (`returncode -1`, `exception_info`), so the agent can continue;
ours now does the same (container failures still raise `SandboxError` → `CONTAINER_ERROR`). Affected: 4 attempts in
`ctx_v1` (3 branches; 2 recovered on the D-012 retry, 1 — qutebrowser `ed19d7f5…` `recovery_note_qwen_to_devstral`
— failed twice) and 1 attempt in `pilot_v0` (recovered on retry). Because the failures were caused by our bug, the
two attempts of the remaining branch are archived as `superseded_D-032_attempt_k` (files kept) and the branch is
rerun with the fix. `pilot_v1`, `validation_v1` and `screen_v1` contain no affected run.

## D-033 — Python environment drift detected and locked down (2026-10-08, ACCEPTED)

Between 01:41 and 05:02 on 2026-10-08 something outside this project upgraded `pip`, `packaging` (left half-installed)
and `wheel` in **both** conda envs (`fc`, `fc-vllm`), at identical times, while jobs were running. Running processes
had already imported their modules and all jobs finished normally; afterwards both envs failed to import. Repair:
`packaging==26.3` reinstalled in both, `setuptools` reinstalled in `fc`; all experiment-relevant versions are unchanged
(mini-swe-agent 2.4.6, litellm 1.104.0, openai 2.54.0, pydantic 2.13.5; vLLM 0.31.0, torch 2.13.0, transformers
5.17.0, mistral_common 1.12.0). Both environments are now frozen in `env/fc.lock.txt` and `env/fc-vllm.lock.txt`,
and every model job runs `scripts/check_env.sh` first and refuses to start on any difference.

## D-034 — Main pair experiment `pilot_v2`: Devstral + GLM-4.7-Flash, HARD tasks, context transfer (2026-10-08, ACCEPTED — PI decision)

PI chose the pair Devstral Small 2 + GLM-4.7-Flash from `screen_v1` (60% vs 45% on the 40 non-HARD tasks, McNemar
p = 0.11; paired 2×2 16/8/2/14, i.e. both discordant cells non-empty; different vendors), asked to include HARD
tasks, and to include the context-transfer setting. Design (all fixed before any `pilot_v2` run):
* tasks `configs/tasks/calibration_v2.json`: the 40 non-HARD tasks of v1 plus the first 20 HARD-51 tasks of the
  same seeded order (seed 20261006) that pass the runtime gate; analyses are also reported per stratum;
* both models on one H100 each, same harness/prompts/budgets/concurrency as before; primaries re-run fresh
  (screening runs are not reused);
* for every primary failure of A (D-021) and every B ∈ {Devstral, GLM}: `recovery_A_to_B` (V0),
  `recovery_note_A_to_B` (A's handoff note, D-026), and Repo_0 controls `control_B_repo0` for B = A and B ≠ A
  (one control per task and model);
* first `validation_v2` on the two held-out tasks with the same conditions (`check_validation` must pass);
* recovery starts under rule D-023 (≤10% infra, ≥5 primary failures per model).

## D-035 — Several workers per model; per-branch cluster-wide lock (2026-10-08, ACCEPTED)

`pilot_v2` recovery branches on HARD tasks take ~9–13 min (median), so 448 branches would need ~18 h with one
job per model. Each branch is now protected by a POSIX lock on `<branch>/.running.lock` (cluster-wide on GPFS,
released if the holder dies); a worker that finds a branch locked skips it and the stage barrier waits for it.
Several jobs per model can therefore share one plan without ever running a branch twice. Each job has its own
server on its own H100 with the usual 4 concurrent agents, so per-endpoint load is unchanged (D-013).
The jobs that were already running use the previous code (no locks); the additional jobs are submitted with
`--dependency=afterany:<running job>` so that lock-less and locking workers never overlap.

## D-036 — Replicates of the `pilot_v2` recovery stage (2026-10-09, ACCEPTED — PI decision)

PI: run replicates first, interpret afterwards (no pre-registered hypothesis). Experiments `pilot_v2_r2` and
`pilot_v2_r3` (`primary_source: pilot_v2`) rerun all 448 recovery/control branches of `pilot_v2` with fresh sampling on
the identical inputs: the same primaries and failure sets, the same Repo_t^A checkpoints and Repo_0 archives
(hard links), and the same handoff notes (hard links; no note is regenerated). What varies is only the rescuer's
own sampling, so per-task outcomes can be pooled across `pilot_v2`, `r2` and `r3` (3 runs per task × condition).
Replicates skip their own primaries and start rule; summaries read primaries from the source experiment and all
recovery/control branches from the replicate itself.
