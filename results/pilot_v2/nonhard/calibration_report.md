# Calibration report — `pilot_v2`

Generated 2026-10-09T07:50:07.035+00:00 from `runs/pilot_v2`. Tasks: 40 (frozen list `configs/tasks/calibration_v2.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| devstral | hard | 0 / 0 | n/a | n/a | 0 |
| devstral | nonhard | 17 / 40 | 42% | [29%, 58%] | 0 |
| devstral | all | 17 / 40 | 42% | [29%, 58%] | 0 |
| glm47flash | hard | 0 / 0 | n/a | n/a | 0 |
| glm47flash | nonhard | 15 / 40 | 38% | [24%, 53%] | 0 |
| glm47flash | all | 15 / 40 | 38% | [24%, 53%] | 0 |

## Exit reasons and primary-failure counts

- **devstral**: statuses {'UNSOLVED': 22, 'SOLVED': 17, 'PRIMARY_TIMEOUT': 1}; exit reasons {'SUBMITTED': 39, 'PRIMARY_TIMEOUT': 1}; primary failures (`unsolved_any_exit`): 23
- **glm47flash**: statuses {'UNSOLVED': 25, 'SOLVED': 15}; exit reasons {'SUBMITTED': 37, 'STEP_LIMIT': 2, 'FORMAT_ERROR_LIMIT': 1}; primary failures (`unsolved_any_exit`): 25

## Paired outcomes (devstral vs glm47flash)

| | glm47flash ✓ | glm47flash ✗ |
|---|---|---|
| **devstral ✓** | 10 | 7 |
| **devstral ✗** | 5 | 18 |

Exact McNemar p = 0.774 (n = 40). Calibration is not meant to rank models (protocol §3).

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| devstral | 74 | 347.1 | 1557057 | 0 | 1 |
| glm47flash | 93 | 453.0 | 3186267 | 2 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
