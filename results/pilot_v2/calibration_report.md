# Calibration report — `pilot_v2`

Generated 2026-10-09T07:49:29.989+00:00 from `runs/pilot_v2`. Tasks: 60 (frozen list `configs/tasks/calibration_v2.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| devstral | hard | 0 / 20 | 0% | [0%, 16%] | 0 |
| devstral | nonhard | 17 / 40 | 42% | [29%, 58%] | 0 |
| devstral | all | 17 / 60 | 28% | [19%, 41%] | 0 |
| glm47flash | hard | 1 / 20 | 5% | [1%, 24%] | 0 |
| glm47flash | nonhard | 15 / 40 | 38% | [24%, 53%] | 0 |
| glm47flash | all | 16 / 60 | 27% | [17%, 39%] | 0 |

## Exit reasons and primary-failure counts

- **devstral**: statuses {'UNSOLVED': 42, 'SOLVED': 17, 'PRIMARY_TIMEOUT': 1}; exit reasons {'SUBMITTED': 57, 'STEP_LIMIT': 2, 'PRIMARY_TIMEOUT': 1}; primary failures (`unsolved_any_exit`): 43
- **glm47flash**: statuses {'UNSOLVED': 44, 'SOLVED': 16}; exit reasons {'SUBMITTED': 54, 'STEP_LIMIT': 4, 'CONTEXT_LIMIT': 1, 'FORMAT_ERROR_LIMIT': 1}; primary failures (`unsolved_any_exit`): 44

## Paired outcomes (devstral vs glm47flash)

| | glm47flash ✓ | glm47flash ✗ |
|---|---|---|
| **devstral ✓** | 10 | 7 |
| **devstral ✗** | 6 | 37 |

Exact McNemar p = 1 (n = 60). Calibration is not meant to rank models (protocol §3).

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| devstral | 74 | 370.0 | 1684069 | 2 | 1 |
| glm47flash | 116 | 500.6 | 4109922 | 4 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
