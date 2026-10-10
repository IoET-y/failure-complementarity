# Calibration report — `pilot_v2`

Generated 2026-10-09T07:49:49.001+00:00 from `runs/pilot_v2`. Tasks: 20 (frozen list `configs/tasks/calibration_v2.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| devstral | hard | 0 / 20 | 0% | [0%, 16%] | 0 |
| devstral | nonhard | 0 / 0 | n/a | n/a | 0 |
| devstral | all | 0 / 20 | 0% | [0%, 16%] | 0 |
| glm47flash | hard | 1 / 20 | 5% | [1%, 24%] | 0 |
| glm47flash | nonhard | 0 / 0 | n/a | n/a | 0 |
| glm47flash | all | 1 / 20 | 5% | [1%, 24%] | 0 |

## Exit reasons and primary-failure counts

- **devstral**: statuses {'UNSOLVED': 20}; exit reasons {'SUBMITTED': 18, 'STEP_LIMIT': 2}; primary failures (`unsolved_any_exit`): 20
- **glm47flash**: statuses {'UNSOLVED': 19, 'SOLVED': 1}; exit reasons {'SUBMITTED': 17, 'STEP_LIMIT': 2, 'CONTEXT_LIMIT': 1}; primary failures (`unsolved_any_exit`): 19

## Paired outcomes (devstral vs glm47flash)

| | glm47flash ✓ | glm47flash ✗ |
|---|---|---|
| **devstral ✓** | 0 | 0 |
| **devstral ✗** | 1 | 19 |

Exact McNemar p = 1 (n = 20). Calibration is not meant to rank models (protocol §3).

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| devstral | 79 | 490.6 | 2001902 | 2 | 0 |
| glm47flash | 134 | 551.3 | 6077918 | 2 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
