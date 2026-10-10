# Recovery table — `pilot_v2`

Generated 2026-10-09T07:49:29.993+00:00. Primary failure definition: `unsolved_any_exit`. Rates over valid branches (infra failures excluded and counted).

| Primary failure | Same-model rescue | Cross-model rescue | Repo0 control |
|---|---|---|---|
| devstral failed (N=43) | devstral: 7 / 43 | glm47flash: 3 / 43 | glm47flash: 5 / 43 |
| glm47flash failed (N=44) | glm47flash: 1 / 44 | devstral: 8 / 44 | devstral: 9 / 44 |

| quantity | estimate | paired n | 2×2 (x✓y✓, x✓y✗, x✗y✓, x✗y✗) | exact McNemar p |
|---|---|---|---|---|
| R_devstral->devstral | 16% [8%, 30%] | 43 | | |
| R_devstral->glm47flash | 7% [2%, 19%] | 43 | | |
| R_glm47flash->devstral | 18% [10%, 32%] | 44 | | |
| R_glm47flash->glm47flash | 2% [0%, 12%] | 44 | | |
| HRG_devstral->glm47flash | -0.09 | 43 | (2, 1, 5, 35) | 0.219 |
| FTV_devstral->glm47flash | -0.05 | 43 | (2, 1, 3, 37) | 0.625 |
| HRG_glm47flash->devstral | +0.16 | 44 | (1, 7, 0, 36) | 0.0156 |
| FTV_glm47flash->devstral | -0.02 | 44 | (3, 5, 6, 30) | 1 |

HRG_{A→B} = R_{A→B} − R_{A→A} (x = cross-model, y = same-model); FTV_{A→B} = P(B✓|Repo_t^A) − P(B✓|Repo_0) (x = rescue on failed workspace, y = Repo_0 control). Small-sample pilot: report counts, not claims.
