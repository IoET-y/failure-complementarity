# Calibration report — `validation_v2`

Generated 2026-10-08T15:25:17.684+00:00 from `runs/validation_v2`. Tasks: 2 (frozen list `/path/to/scratch/failure-complementarity/configs/tasks/validation_v0.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| devstral | hard | 0 / 2 | 0% | [0%, 66%] | 0 |
| devstral | nonhard | 0 / 0 | n/a | n/a | 0 |
| devstral | all | 0 / 2 | 0% | [0%, 66%] | 0 |
| glm47flash | hard | 0 / 2 | 0% | [0%, 66%] | 0 |
| glm47flash | nonhard | 0 / 0 | n/a | n/a | 0 |
| glm47flash | all | 0 / 2 | 0% | [0%, 66%] | 0 |

## Exit reasons and primary-failure counts

- **devstral**: statuses {'UNSOLVED': 2}; exit reasons {'SUBMITTED': 2}; primary failures (`unsolved_any_exit`): 2
- **glm47flash**: statuses {'UNSOLVED': 2}; exit reasons {'SUBMITTED': 2}; primary failures (`unsolved_any_exit`): 2

## Paired outcomes (devstral vs glm47flash)

| | glm47flash ✓ | glm47flash ✗ |
|---|---|---|
| **devstral ✓** | 0 | 0 |
| **devstral ✗** | 0 | 2 |

Exact McNemar p = 1 (n = 2). Calibration is not meant to rank models (protocol §3).

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| devstral | 36 | 262.3 | 926349 | 0 | 0 |
| glm47flash | 170 | 391.3 | 8753142 | 0 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
