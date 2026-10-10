# Recovery table — `validation_v2`

Generated 2026-10-08T15:25:17.685+00:00. Primary failure definition: `unsolved_any_exit`. Rates over valid branches (infra failures excluded and counted).

| Primary failure | Same-model rescue | Cross-model rescue | Repo0 control |
|---|---|---|---|
| devstral failed (N=2) | devstral: 0 / 2 | glm47flash: 0 / 2 | glm47flash: 0 / 2 |
| glm47flash failed (N=2) | glm47flash: 0 / 2 | devstral: 0 / 2 | devstral: 0 / 2 |

| quantity | estimate | paired n | 2×2 (x✓y✓, x✓y✗, x✗y✓, x✗y✗) | exact McNemar p |
|---|---|---|---|---|
| R_devstral->devstral | 0% [0%, 66%] | 2 | | |
| R_devstral->glm47flash | 0% [0%, 66%] | 2 | | |
| R_glm47flash->devstral | 0% [0%, 66%] | 2 | | |
| R_glm47flash->glm47flash | 0% [0%, 66%] | 2 | | |
| HRG_devstral->glm47flash | +0.00 | 2 | (0, 0, 0, 2) | 1 |
| FTV_devstral->glm47flash | +0.00 | 2 | (0, 0, 0, 2) | 1 |
| HRG_glm47flash->devstral | +0.00 | 2 | (0, 0, 0, 2) | 1 |
| FTV_glm47flash->devstral | +0.00 | 2 | (0, 0, 0, 2) | 1 |

HRG_{A→B} = R_{A→B} − R_{A→A} (x = cross-model, y = same-model); FTV_{A→B} = P(B✓|Repo_t^A) − P(B✓|Repo_0) (x = rescue on failed workspace, y = Repo_0 control). Small-sample pilot: report counts, not claims.
