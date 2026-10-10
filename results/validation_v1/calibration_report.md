# Calibration report — `validation_v1`

Generated 2026-10-07T16:46:47.830+00:00 from `runs/validation_v1`. Tasks: 2 (frozen list `/path/to/scratch/failure-complementarity/configs/tasks/validation_v0.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| qwen | hard | 0 / 2 | 0% | [0%, 66%] | 0 |
| qwen | nonhard | 0 / 0 | n/a | n/a | 0 |
| qwen | all | 0 / 2 | 0% | [0%, 66%] | 0 |
| devstral | hard | 0 / 2 | 0% | [0%, 66%] | 0 |
| devstral | nonhard | 0 / 0 | n/a | n/a | 0 |
| devstral | all | 0 / 2 | 0% | [0%, 66%] | 0 |

## Exit reasons and primary-failure counts

- **qwen**: statuses {'UNSOLVED': 2}; exit reasons {'SUBMITTED': 2}; primary failures (`unsolved_any_exit`): 2
- **devstral**: statuses {'UNSOLVED': 2}; exit reasons {'SUBMITTED': 2}; primary failures (`unsolved_any_exit`): 2

## Paired outcomes (qwen vs devstral)

| | devstral ✓ | devstral ✗ |
|---|---|---|
| **qwen ✓** | 0 | 0 |
| **qwen ✗** | 0 | 2 |

Exact McNemar p = 1 (n = 2). Calibration is not meant to rank models (protocol §3).

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| qwen | 41 | 60.2 | 728834 | 0 | 0 |
| devstral | 60 | 303.6 | 1235806 | 0 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
