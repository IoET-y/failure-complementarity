# Recovery table — `validation_v1`

Generated 2026-10-07T16:46:47.832+00:00. Primary failure definition: `unsolved_any_exit`. Rates over valid branches (infra failures excluded and counted).

| Primary failure | Same-model rescue | Cross-model rescue | Repo0 control |
|---|---|---|---|
| qwen failed (N=2) | qwen: 0 / 2 | devstral: 0 / 2 | devstral: 0 / 2 |
| devstral failed (N=2) | devstral: 0 / 2 | qwen: 0 / 2 | qwen: 0 / 2 |

| quantity | estimate | paired n | 2×2 (x✓y✓, x✓y✗, x✗y✓, x✗y✗) | exact McNemar p |
|---|---|---|---|---|
| R_qwen->qwen | 0% [0%, 66%] | 2 | | |
| R_qwen->devstral | 0% [0%, 66%] | 2 | | |
| R_devstral->qwen | 0% [0%, 66%] | 2 | | |
| R_devstral->devstral | 0% [0%, 66%] | 2 | | |
| HRG_qwen->devstral | +0.00 | 2 | (0, 0, 0, 2) | 1 |
| FTV_qwen->devstral | +0.00 | 2 | (0, 0, 0, 2) | 1 |
| HRG_devstral->qwen | +0.00 | 2 | (0, 0, 0, 2) | 1 |
| FTV_devstral->qwen | +0.00 | 2 | (0, 0, 0, 2) | 1 |

HRG_{A→B} = R_{A→B} − R_{A→A} (x = cross-model, y = same-model); FTV_{A→B} = P(B✓|Repo_t^A) − P(B✓|Repo_0) (x = rescue on failed workspace, y = Repo_0 control). Small-sample pilot: report counts, not claims.
