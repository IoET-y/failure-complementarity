# Calibration report — `screen_v1`

Generated 2026-10-08T13:39:18.473+00:00 from `runs/screen_v1`. Tasks: 40 (frozen list `configs/tasks/calibration_v1.json`). Budget: 30 min / 250 steps per run. All runs reported; none removed.

## Solve rates (primary runs from Repo_0)

| model | subset | solved / valid | rate | 95% Wilson CI | infra / missing |
|---|---|---|---|---|---|
| qwen36moe | hard | 0 / 0 | n/a | n/a | 0 |
| qwen36moe | nonhard | 31 / 40 | 78% | [62%, 88%] | 0 |
| qwen36moe | all | 31 / 40 | 78% | [62%, 88%] | 0 |
| qwen36dense | hard | 0 / 0 | n/a | n/a | 0 |
| qwen36dense | nonhard | 32 / 40 | 80% | [65%, 90%] | 0 |
| qwen36dense | all | 32 / 40 | 80% | [65%, 90%] | 0 |
| nemotron3nano | hard | 0 / 0 | n/a | n/a | 0 |
| nemotron3nano | nonhard | 4 / 40 | 10% | [4%, 23%] | 0 |
| nemotron3nano | all | 4 / 40 | 10% | [4%, 23%] | 0 |
| glm47flash | hard | 0 / 0 | n/a | n/a | 0 |
| glm47flash | nonhard | 18 / 40 | 45% | [31%, 60%] | 0 |
| glm47flash | all | 18 / 40 | 45% | [31%, 60%] | 0 |
| gptoss120b | hard | 0 / 0 | n/a | n/a | 0 |
| gptoss120b | nonhard | 3 / 40 | 8% | [3%, 20%] | 0 |
| gptoss120b | all | 3 / 40 | 8% | [3%, 20%] | 0 |

## Exit reasons and primary-failure counts

- **qwen36moe**: statuses {'SOLVED': 31, 'UNSOLVED': 9}; exit reasons {'SUBMITTED': 40}; primary failures (`unsolved_any_exit`): 9
- **qwen36dense**: statuses {'UNSOLVED': 8, 'SOLVED': 32}; exit reasons {'CONTEXT_LIMIT': 1, 'SUBMITTED': 39}; primary failures (`unsolved_any_exit`): 8
- **nemotron3nano**: statuses {'UNSOLVED': 36, 'SOLVED': 4}; exit reasons {'FORMAT_ERROR_LIMIT': 23, 'SUBMITTED': 15, 'STEP_LIMIT': 2}; primary failures (`unsolved_any_exit`): 36
- **glm47flash**: statuses {'UNSOLVED': 22, 'SOLVED': 18}; exit reasons {'SUBMITTED': 39, 'CONTEXT_LIMIT': 1}; primary failures (`unsolved_any_exit`): 22
- **gptoss120b**: statuses {'UNSOLVED': 37, 'SOLVED': 3}; exit reasons {'FORMAT_ERROR_LIMIT': 40}; primary failures (`unsolved_any_exit`): 37

## Steps, time, tokens (median over valid runs)

| model | median steps | median agent s | median tokens | runs hitting step cap | runs hitting time cap |
|---|---|---|---|---|---|
| qwen36moe | 61 | 165.0 | 1991757 | 0 | 0 |
| qwen36dense | 65 | 350.0 | 1953340 | 0 | 0 |
| nemotron3nano | 11 | 9.6 | 55929 | 2 | 0 |
| glm47flash | 87 | 357.0 | 2812993 | 0 | 0 |
| gptoss120b | 21 | 65.8 | 222979 | 0 | 0 |

Target from the protocol: each model solves roughly 20%–70% of the tasks (§3).
