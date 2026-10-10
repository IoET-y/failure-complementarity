# Calibration report — `pilot_v1`

Generated 2026-10-08T06:15:49.767+00:00 from `runs/pilot_v1`. Tasks: 40 (frozen list `/path/to/scratch/failure-complementarity/configs/tasks/calibration_v1.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| qwen | hard | 0 / 0 | n/a | n/a | 0 |
| qwen | nonhard | 9 / 40 | 22% | [12%, 38%] | 0 |
| qwen | all | 9 / 40 | 22% | [12%, 38%] | 0 |
| devstral | hard | 0 / 0 | n/a | n/a | 0 |
| devstral | nonhard | 24 / 40 | 60% | [45%, 74%] | 0 |
| devstral | all | 24 / 40 | 60% | [45%, 74%] | 0 |

## Exit reasons and primary-failure counts

- **qwen**: statuses {'UNSOLVED': 31, 'SOLVED': 9}; exit reasons {'SUBMITTED': 39, 'FORMAT_ERROR_LIMIT': 1}; primary failures (`unsolved_any_exit`): 31
- **devstral**: statuses {'UNSOLVED': 16, 'SOLVED': 24}; exit reasons {'SUBMITTED': 39, 'STEP_LIMIT': 1}; primary failures (`unsolved_any_exit`): 16

## Paired outcomes (qwen vs devstral)

| | devstral ✓ | devstral ✗ |
|---|---|---|
| **qwen ✓** | 9 | 0 |
| **qwen ✗** | 15 | 16 |

Exact McNemar p = 6.1e-05 (n = 40). Calibration is not meant to rank models (protocol §3).

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| qwen | 48 | 93.8 | 719446 | 0 | 0 |
| devstral | 67 | 371.7 | 1642455 | 1 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
