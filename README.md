# Failure-conditioned recovery between coding agents

A controlled pilot on SWE-bench Pro V2 — code, protocol, decision log, and data.

**Author:** Di Yang, William & Mary · <dyang06@wm.edu> · write-up: <https://ioet-y.github.io/blog/>

> **Question.** When one repository-level coding agent fails, is a fresh *heterogeneous* agent better at recovering the
> failed workspace than a fresh instance of the *same* agent?

This repository is the complete, reproducible framework behind a small study of that question: the agent harness is held
fixed (mini-SWE-agent 2.4.6, one `bash` tool) and **only the model changes**. For every task where agent *A* fails, the
exact filesystem it left behind is frozen, and three kinds of fresh agent are started from byte-identical copies of it:
*A* again, a different model *B*, and *B* on the pristine repository (the control that separates "B is good at this task" from
"A's leftovers helped B").

**Status: exploratory pilot, not a finished study.** Everything is reported — including the null results and the
mistakes. See the write-up for the interpretation and limitations.

## What we found (short)

| | |
|---|---|
| **HRG** (other model − same model, same failed workspace) | +0.015, 95% CI [−0.042, +0.071] — *no detectable benefit from switching models when the two are matched in strength* |
| **FTV** (failed workspace − pristine control) | −0.059, 95% CI [−0.130, +0.006] — *the failed workspace did not help, and may slightly hurt* |
| **CTV** (with handoff note − without) | 0.000, 95% CI [−0.045, +0.050] — *a self-written handoff note did not help* |
| Replicates | one apparent effect (p = 0.016) in the first run **did not replicate** over two further replicates |

Pair: Devstral Small 2 (24B) and GLM-4.7-Flash, selected from five screened open-weight models; 60 tasks (40 non-HARD +
20 HARD); 87 failed workspaces; 3 replicates × 448 rescue/control runs. Details, caveats and all tables are in the write-up
and in [`results/`](results/).

## Repository layout

```text
src/failure_complementarity/   config, run manifest, sandbox, branch runner, evaluator, checkpoint/restore, analysis
scripts/                       run_stage / worker / select_tasks / summarize_*; slurm/ job scripts; dev/ fake endpoint
configs/                       experiment definitions (pilot_v0 … pilot_v2, replicates), agents, budgets, prompts, frozen task lists
docs/experiment_protocol.md    the scientific protocol (source of truth)
docs/decisions.md              dated decision log D-001 … D-036: every deviation and every bug that touched the data
docs/environment.md            versions, hardware, serving commands;  env/*.lock.txt  exact package locks
results/data/branches.csv      one row per recorded agent run (2,110)
results/data/headline_numbers.json   every number quoted in the write-up
tests/                         unit tests (64 pass, 1 skipped without the benchmark checkout), incl. one that pins the published numbers
```

## Recompute the published numbers (no GPU, no containers)

```bash
pip install -e ".[dev]"
python scripts/analyze_from_csv.py        # screening table, pooled recovery table, HRG / FTV / CTV with intervals
python scripts/make_figures.py            # the four figures in docs/figures/
pytest                                    # 64 pass; tests/test_published_results.py pins the headline numbers
```

## Rerun the experiments

Needs: Apptainer (agents run in `--net none` containers), GPUs able to serve the models with vLLM 0.31.0, and the
official SWE-bench Pro V2 checkout at the pinned commit (see `configs/benchmark.yaml` and `docs/environment.md`).
Paths and the cluster account are placeholders (`/path/to/scratch`, `YOUR_ACCOUNT`) in `configs/paths.yaml` and
`scripts/slurm/*`; adapt them to your site. Outline:

```bash
python scripts/preflight.py --config configs/pilot_v2.yaml                 # pins, prompt checksum
python scripts/select_tasks.py --config configs/pilot_v2.yaml --out configs/tasks/calibration_v2.json   # outcome-blind, gated
sbatch -J fc_v2_devstral   --export=ALL,FC_AGENT=devstral,"FC_WORKER_ARGS=--cal-config configs/pilot_v2.yaml --cal-tasks configs/tasks/calibration_v2.json --val-config configs/validation_v2.yaml" scripts/slurm/model_job.sbatch
sbatch -J fc_v2_glm47flash --export=ALL,FC_AGENT=glm47flash,"FC_WORKER_ARGS=..."  scripts/slurm/model_job.sbatch
```

One job per model serves its model on one H100 and runs every branch that needs it; the two workers synchronise through
result files on a shared filesystem (stage barriers, per-branch POSIX locks), so no model ever calls the other.

## Design guarantees (and where they are enforced)

* **Exact failed workspace.** The whole container root filesystem of the failed run is archived (`tar.zst` + per-file
  SHA-256 manifest); every rescue branch restores it into a fresh directory and the tree hash is checked
  (`checkpoint/`, `runner/branch.py`).
* **Isolation.** One writable container per branch, no network for the agent, no shared state; the unit test
  `tests/test_checkpoint.py` mutates one restore and verifies the other is unaffected.
* **Official grading, never in the agent's sandbox.** The final diff is applied to a pristine image and the unchanged
  benchmark verifier is run (`runner/evaluator.py`); gold/empty-patch sanity checks gate every task (`benchmark/gate.py`).
* **Infrastructure failures are never counted as agent failures** (`logging/schema.py`); they are retried identically for
  all models, and retroactive reclassifications are logged (D-025, D-032).
* **Frozen protocol.** The run manifest fingerprints the science-relevant configuration and refuses to resume under a
  changed one; amendments are explicit and recorded (`manifest.py`).

## Honest limitations (the long version is in the write-up)

One benchmark, one harness (a single `bash` tool), two ~25B open-weight models, 43–44 failed tasks per direction;
mostly non-HARD tasks (HARD tasks were at floor); all failures are "confident wrong submissions" (almost no run hit the
budget); many contrasts were examined, the analysis is exploratory and was not pre-registered; the model pair was chosen
after screening on tasks that overlap with the main experiment (primaries were re-run fresh).

## Open invitation

This was done on a modest academic allocation (about 115 H100-hours). **If you have access to substantial Codex /
Claude Code–class compute and find "cooperation and recovery between agents" interesting, I would be glad to explore
it together** — stronger models, other harnesses, more tasks, and trajectory-level mechanism analysis are the obvious
next steps (see the write-up). Please get in touch: <dyang06@wm.edu>.

## AI assistance

The code, the analysis scripts and the first drafts of the documents were produced with the help of Claude (Anthropic),
working inside Claude Code under my direction. The experimental design, the decisions recorded in `docs/decisions.md`
and the interpretation are mine; I take responsibility for any errors.

## Citation

See [`CITATION.cff`](CITATION.cff). Third-party material: [`NOTICE.md`](NOTICE.md). Licence: MIT.
