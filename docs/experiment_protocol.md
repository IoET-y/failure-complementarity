# Experiment Protocol — Failure-Conditioned Recovery and Failure Complementarity

**Status:** V0 protocol, created 2026-10-06 from the project specification.
**This document is the scientific source of truth.** Implementation must conform to it.
Simplifying the implementation is not a valid reason to change it.

Sections 1–12 restate the specification. Section 13 lists the binding of the protocol to concrete tooling.

---

## 1. Research question

> When one repository-level coding agent fails, is a fresh heterogeneous agent better at recovering the
> failed workspace than a fresh instance of the same agent?

The quantity of interest is not ordinary task success $P(B \text{ succeeds} \mid Task)$ but

$$
P(B \text{ recovers} \mid A \text{ failed},\ Repo_t^A)
$$

where $A$ is the primary agent/model, $B$ the rescue agent/model, and $Repo_t^A$ the actual repository state
left by $A$ after failure. The long-term deliverable is a **pairwise rescue matrix** across agents/models.

## 2. Controlled factor

For the initial study the harness is fixed and **only the model varies**: $Harness_A = Harness_B$.
All agents use the same mini-SWE-agent version, the same system/task prompt template, the same repository
environment, network policy, benchmark evaluator and recovery information, and comparable inference budgets.
Other harnesses (OpenHands, Claude Code, Codex, …) are excluded from the main controlled experiment and
reserved for later external-validity studies.

Initial stack: mini-SWE-agent; SWE-bench Pro V2; models served behind OpenAI-compatible endpoints (vLLM);
models Qwen3-Coder-30B-A3B and Devstral Small 2 24B. The framework must allow adding further models by
configuration only.

## 3. Phase 0 — calibration

* Select ≈10 tasks from SWE-bench Pro V2 HARD-51 and ≈10 tasks from non-HARD V2 ($N \approx 20$).
* Run both models independently from the pristine state: $Repo_0 \to Qwen$, $Repo_0 \to Devstral$.
* Goal: check that the task distribution gives each model both successes and failures (target solve rate
  roughly 20%–70%), **not** to rank models.
* If HARD-51 is near-impossible for both, move toward easier V2 tasks; if normal V2 is saturated, increase
  the HARD fraction.
* No cherry-picking: tasks must not be selected based on knowledge of which model solves them. The task set
  is fixed before rescue performance is compared.

## 4. Primary failure (V0 definition)

No learned stagnation detector. A fixed primary execution budget is used. A task is a **primary failure** if

1. the agent reaches the configured resource/time budget, **and**
2. the official benchmark evaluator does not mark the task solved.

The definition is deterministic. Budgets are configurable (e.g. `primary.wallclock_minutes`,
`recovery.wallclock_minutes`) and must never be changed silently or per model.

> **Amended 2026-10-07 (D-021, PI-approved):** agents almost always end by *submitting* before the budget is
> reached, so condition 1 is replaced by "the primary run has ended (submission, budget, step cap, format-error
> or context limit)". A primary failure is any such run the official evaluator marks unsolved. Exit reasons are
> recorded, so the budget-exhausted subset remains reportable.

## 5. Core recovery experiment

For each primary agent $A$ and task where $A$ fails, freeze the exact workspace $Repo_t^A$ and create three
**independent** branches:

| Condition | Start state | Agent | Purpose |
|---|---|---|---|
| A — same-model restart | $Repo_t^A$ | fresh $A$ | $R_{A\to A}$ |
| B — heterogeneous rescue | $Repo_t^A$ | fresh $B$ | $R_{A\to B}$ |
| C — original-state control | $Repo_0$ | fresh $B$ | baseline for $FTV_{A\to B}$ |

Fresh agents never receive the previous conversation/trajectory. The design is run in both directions
(Qwen-primary and Devstral-primary). **The $Repo_0$ control and the isolated failed-workspace branches must
not be simplified away.**

## 6. Recovery information

Every fresh rescue agent (conditions A and B) receives the same standardized recovery prompt, conceptually:

> A previous coding agent attempted this task but did not solve it.
> Independently inspect the current repository state and complete the original task.
> Existing modifications may be correct, partially correct, or incorrect. You may keep, modify, or revert them.
> Do not assume the previous agent's approach or hypotheses were correct.
> Run the relevant tests and make whatever repository changes are necessary.

It must **not** include previous chain-of-thought, the trajectory, a summary of previous reasoning, or the
previous model's hypotheses. In V0, rescue agents get only: the original task specification, the current
workspace, the observable repository state, and tests/errors obtainable by running the repository.
The exact text is versioned in `configs/prompts/` (prompt version recorded with every run).

Condition C (Repo_0 control) uses the **primary** prompt, since there is no previous attempt to describe.

## 7. Exact checkpointing

Recovery branches must start from **exactly** the same failed workspace. `git diff` alone is insufficient
(untracked files, deletions, generated config, modified scripts, other workspace state). The checkpoint
captures the full workspace state, can be restored any number of times into isolated environments, and is
accompanied by `git diff`, `git status` and metadata. Each recovery branch starts from a **clean copy** of the
same checkpoint; a branch is never started from another branch's result.

## 8. Isolation

Every branch has its own workspace/container. No branch can observe another branch's modifications.
Environment variables, benchmark image/version, network settings and task metadata are identical across
branches.

## 9. Metrics

* **Ordinary success:** `solved ∈ {0,1}` from the official evaluator.
* **Recovery rate:** $R_{A\to B} = P(B \text{ succeeds} \mid A \text{ failed}, Repo_t^A)$.
* **Heterogeneous rescue gain:** $HRG_{A\to B} = R_{A\to B} - R_{A\to A}$.
* **Failure-state transfer value:** $FTV_{A\to B} = P(B \text{ succeeds} \mid Repo_t^A) - P(B \text{ succeeds} \mid Repo_0)$,
  estimated on the same set of $A$-failed tasks. $FTV>0$: failed work was useful to $B$; $FTV<0$: failed
  state was harmful (candidate "failure debt" — terminology not to be baked into conclusions yet).

Primary V0 deliverable:

```text
Primary failure   Same-model rescue    Cross-model rescue    Repo0 control
Qwen failed       Qwen: x / N          Devstral: y / N       Devstral: z / N
Devstral failed   Devstral: a / M      Qwen: b / M           Qwen: c / M
```

with $R_{Q\to Q}, R_{Q\to D}, R_{D\to D}, R_{D\to Q}$, $HRG_{Q\to D}, HRG_{D\to Q}$, $FTV_{Q\to D}, FTV_{D\to Q}$.

## 10. Per-run measurements

task ID; benchmark subset; model; model revision; harness version/commit; inference-server version; prompt
version; start/end timestamps; wall-clock duration; input/output/total tokens; agent steps; tool calls;
shell-command count; test-command count; files read; files edited; final git diff; final git status;
evaluator result; exit reason; exception information on infrastructure failure.

`TASK_FAILURE` and `INFRA_FAILURE` are always distinguished. Infrastructure failures are never counted as
agent failures. Explicit statuses are used (never a generic "failed"):
`SOLVED, UNSOLVED, PRIMARY_TIMEOUT, RECOVERY_TIMEOUT, MODEL_ERROR, HARNESS_ERROR, CONTAINER_ERROR, EVALUATOR_ERROR`.

## 11. Trajectories

Every run has a complete machine-readable JSONL trajectory (fields: timestamp, run_id, task_id, agent, step,
event_type, tool, content, metadata). Raw mini-SWE-agent trajectory artifacts and the raw provider/model
responses are preserved.

## 12. Statistical and integrity rules

Statistics: no claims from tiny samples; report raw counts, paired task-level outcomes, and confidence
intervals where reasonable. The task is the unit of comparison. The full paired 2×2 table
(A✓B✓, A✓B✗, A✗B✓, A✗B✗) is preserved; paired tests (e.g. McNemar) may be used later. Negative results are
valid.

Integrity rules (non-negotiable):

1. Never manually repair benchmark repositories.
2. Never expose reference patches to agents.
3. Never expose hidden benchmark tests during agent execution unless the official protocol allows it.
4. Never rerun selectively only when one model fails.
5. Never change prompts per task.
6. Never silently increase budget for one model.
7. Never discard failed trajectories.
8. Never replace an infra failure with a task failure.
9. Never reuse a modified recovery workspace across conditions.
10. Never change the experimental protocol without recording the change with reason and date.

---

## 13. Implementation binding (V0)

| Protocol element | V0 binding | Item |
|---|---|---|
| Benchmark | SWE-bench Pro V2 **v2.0.0**, repo `scaleapi/SWE-bench_Pro-os` @ `66f92766bba6…`, tasks from `v2/tasks/` (Harbor format), HARD-51 from `v2/hard51_ids.txt` | D-001 |
| Container runtime | Apptainer (no Docker on the cluster); GHCR images converted to SIF, image digest recorded | D-002 |
| Runtime validity gate | a task is eligible only if gold patch → solved and empty patch → unsolved under our runtime; gate is run **before** any model run, outcome-blind | D-003 |
| Harness | mini-SWE-agent (pinned), LLM loop on host, bash actions executed in a persistent per-branch container instance; official V2 `mini_toolcall.yaml` prompt | D-004 |
| Agent phase network | none (model endpoint is reached from the host, not from the sandbox) — matches V2 locked protocol | D-004 |
| Evaluation | V2 locked protocol: capture the diff of the final workspace vs. the task base commit and re-grade it on a **pristine** image with the unchanged official verifier (`tests/test.sh`) | D-005 |
| Checkpoint | full root filesystem of the branch container (not only `/app`), archived as `tar.zst`, plus `git diff`/`git status`/manifest of file hashes | D-006 |
| Budgets | wall-clock budget per phase from `configs/budgets.yaml`, identical for all models; per-command timeout identical | D-007 |
| Sampling | each model's vendor-recommended sampling parameters; same max context length for all models | D-008 |
| Task selection | seeded, outcome-blind random sample (10 HARD-51 + 10 non-HARD) fixed and committed before any model run | D-011 |
| Infra-failure reruns | allowed only for `INFRA_FAILURE`, applied identically to every model/condition, all attempts preserved | D-012 |
