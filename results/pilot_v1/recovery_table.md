# Recovery table — `pilot_v1`

Generated 2026-10-08T06:15:49.771+00:00. Primary failure definition: `unsolved_any_exit`. Rates over valid branches (infra failures excluded and counted).

| Primary failure | Same-model rescue | Cross-model rescue | Repo0 control |
|---|---|---|---|
| qwen failed (N=31) | qwen: 3 / 31 | devstral: 11 / 31 | devstral: 12 / 31 |
| devstral failed (N=16) | devstral: 1 / 16 | qwen: 0 / 16 | qwen: 0 / 16 |

| quantity | estimate | paired n | 2×2 (x✓y✓, x✓y✗, x✗y✓, x✗y✗) | exact McNemar p |
|---|---|---|---|---|
| R_qwen->qwen | 10% [3%, 25%] | 31 | | |
| R_qwen->devstral | 35% [21%, 53%] | 31 | | |
| R_devstral->qwen | 0% [0%, 19%] | 16 | | |
| R_devstral->devstral | 6% [1%, 28%] | 16 | | |
| HRG_qwen->devstral | +0.26 | 31 | (3, 8, 0, 20) | 0.00781 |
| FTV_qwen->devstral | -0.03 | 31 | (7, 4, 5, 15) | 1 |
| HRG_devstral->qwen | -0.06 | 16 | (0, 0, 1, 15) | 1 |
| FTV_devstral->qwen | +0.00 | 16 | (0, 0, 0, 16) | 1 |

HRG_{A→B} = R_{A→B} − R_{A→A} (x = cross-model, y = same-model); FTV_{A→B} = P(B✓|Repo_t^A) − P(B✓|Repo_0) (x = rescue on failed workspace, y = Repo_0 control). Small-sample pilot: report counts, not claims.
