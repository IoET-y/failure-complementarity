# Recovery table — `pilot_v2`

Generated 2026-10-09T07:49:49.004+00:00. Primary failure definition: `unsolved_any_exit`. Rates over valid branches (infra failures excluded and counted).

| Primary failure | Same-model rescue | Cross-model rescue | Repo0 control |
|---|---|---|---|
| devstral failed (N=20) | devstral: 2 / 20 | glm47flash: 1 / 20 | glm47flash: 1 / 20 |
| glm47flash failed (N=19) | glm47flash: 0 / 19 | devstral: 1 / 19 | devstral: 1 / 19 |

| quantity | estimate | paired n | 2×2 (x✓y✓, x✓y✗, x✗y✓, x✗y✗) | exact McNemar p |
|---|---|---|---|---|
| R_devstral->devstral | 10% [3%, 30%] | 20 | | |
| R_devstral->glm47flash | 5% [1%, 24%] | 20 | | |
| R_glm47flash->devstral | 5% [1%, 25%] | 19 | | |
| R_glm47flash->glm47flash | 0% [0%, 17%] | 19 | | |
| HRG_devstral->glm47flash | -0.05 | 20 | (0, 1, 2, 17) | 1 |
| FTV_devstral->glm47flash | +0.00 | 20 | (0, 1, 1, 18) | 1 |
| HRG_glm47flash->devstral | +0.05 | 19 | (0, 1, 0, 18) | 1 |
| FTV_glm47flash->devstral | +0.00 | 19 | (0, 1, 1, 17) | 1 |

HRG_{A→B} = R_{A→B} − R_{A→A} (x = cross-model, y = same-model); FTV_{A→B} = P(B✓|Repo_t^A) − P(B✓|Repo_0) (x = rescue on failed workspace, y = Repo_0 control). Small-sample pilot: report counts, not claims.
