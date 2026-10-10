# Recovery table — `pilot_v2`

Generated 2026-10-09T07:50:07.037+00:00. Primary failure definition: `unsolved_any_exit`. Rates over valid branches (infra failures excluded and counted).

| Primary failure | Same-model rescue | Cross-model rescue | Repo0 control |
|---|---|---|---|
| devstral failed (N=23) | devstral: 5 / 23 | glm47flash: 2 / 23 | glm47flash: 4 / 23 |
| glm47flash failed (N=25) | glm47flash: 1 / 25 | devstral: 7 / 25 | devstral: 8 / 25 |

| quantity | estimate | paired n | 2×2 (x✓y✓, x✓y✗, x✗y✓, x✗y✗) | exact McNemar p |
|---|---|---|---|---|
| R_devstral->devstral | 22% [10%, 42%] | 23 | | |
| R_devstral->glm47flash | 9% [2%, 27%] | 23 | | |
| R_glm47flash->devstral | 28% [14%, 48%] | 25 | | |
| R_glm47flash->glm47flash | 4% [1%, 20%] | 25 | | |
| HRG_devstral->glm47flash | -0.13 | 23 | (2, 0, 3, 18) | 0.25 |
| FTV_devstral->glm47flash | -0.09 | 23 | (2, 0, 2, 19) | 0.5 |
| HRG_glm47flash->devstral | +0.24 | 25 | (1, 6, 0, 18) | 0.0312 |
| FTV_glm47flash->devstral | -0.04 | 25 | (3, 4, 5, 13) | 1 |

HRG_{A→B} = R_{A→B} − R_{A→A} (x = cross-model, y = same-model); FTV_{A→B} = P(B✓|Repo_t^A) − P(B✓|Repo_0) (x = rescue on failed workspace, y = Repo_0 control). Small-sample pilot: report counts, not claims.
