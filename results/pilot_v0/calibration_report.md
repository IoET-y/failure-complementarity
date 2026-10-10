# Calibration report — `pilot_v0`

Generated 2026-10-07T05:26:33.949+00:00 from `runs/pilot_v0`. Tasks: 20 (frozen list `/path/to/scratch/failure-complementarity/configs/tasks/calibration_v0.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| qwen | hard | 0 / 10 | 0% | [0%, 28%] | 0 |
| qwen | nonhard | 0 / 10 | 0% | [0%, 28%] | 0 |
| qwen | all | 0 / 20 | 0% | [0%, 16%] | 0 |
| devstral | hard | 0 / 10 | 0% | [0%, 28%] | 0 |
| devstral | nonhard | 4 / 10 | 40% | [17%, 69%] | 0 |
| devstral | all | 4 / 20 | 20% | [8%, 42%] | 0 |

## Exit reasons and primary-failure counts

- **qwen**: statuses {'UNSOLVED': 20}; exit reasons {'SUBMITTED': 20}; primary failures (`budget_exhausted_and_unsolved`): 0
- **devstral**: statuses {'UNSOLVED': 16, 'SOLVED': 4}; exit reasons {'SUBMITTED': 20}; primary failures (`budget_exhausted_and_unsolved`): 0

## Paired outcomes (qwen vs devstral)

| | devstral ✓ | devstral ✗ |
|---|---|---|
| **qwen ✓** | 0 | 0 |
| **qwen ✗** | 4 | 16 |

Exact McNemar p = 0.125 (n = 20). Calibration is not meant to rank models (protocol §3).

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| qwen | 61 | 86.3 | 1110197 | 0 | 0 |
| devstral | 62 | 338.1 | 1286107 | 0 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
