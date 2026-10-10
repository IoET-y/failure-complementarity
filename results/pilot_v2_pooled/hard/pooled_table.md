# Pooled replicates — pilot_v2, pilot_v2_r2, pilot_v2_r3 (hard)

3 replicate(s) per task × condition on identical failed workspaces and notes. Rates: per replicate and pooled. Contrasts: per-task mean difference, bootstrap 95% CI over tasks, exact sign test over tasks.

## devstral failed (N = 20 tasks)

| condition | pilot_v2 | pilot_v2_r2 | pilot_v2_r3 | pooled |
|---|---|---|---|---|
| V0 devstral→devstral (same) | 2/20 | 1/20 | 1/20 | 6.7% (4/60) |
| note devstral→devstral (same) | 1/20 | 2/20 | 1/20 | 6.7% (4/60) |
| Repo0 devstral (same) | 1/20 | 2/20 | 2/20 | 8.3% (5/60) |
| V0 devstral→glm47flash | 1/20 | 0/20 | 1/20 | 3.3% (2/60) |
| note devstral→glm47flash | 0/20 | 0/20 | 1/20 | 1.7% (1/60) |
| Repo0 glm47flash | 1/20 | 2/20 | 1/20 | 6.7% (4/60) |

| contrast (x − y) | mean per-task diff | 95% bootstrap CI | tasks x>y / x<y | sign-test p | per replicate |
|---|---|---|---|---|---|
| HRG devstral→glm47flash (V0) | -0.033 | [-0.083, +0.000] | 0 / 2 | 0.5 | -0.05, -0.05, +0.00 |
| HRG devstral→glm47flash (note) | -0.050 | [-0.167, +0.033] | 1 / 2 | 1 | -0.05, -0.10, +0.00 |
| FTV devstral→devstral (same) | -0.017 | [-0.067, +0.033] | 1 / 2 | 1 | +0.05, -0.05, -0.05 |
| FTV devstral→glm47flash | -0.033 | [-0.100, +0.000] | 0 / 1 | 1 | +0.00, -0.10, +0.00 |
| CTV devstral→devstral (same) | +0.000 | [-0.050, +0.050] | 1 / 1 | 1 | -0.05, +0.05, +0.00 |
| CTV devstral→glm47flash | -0.017 | [-0.050, +0.000] | 0 / 1 | 1 | -0.05, +0.00, +0.00 |
| capability glm47flash vs devstral on F_devstral | -0.017 | [-0.117, +0.083] | 1 / 2 | 1 | +0.00, +0.00, -0.05 |

## glm47flash failed (N = 19 tasks)

| condition | pilot_v2 | pilot_v2_r2 | pilot_v2_r3 | pooled |
|---|---|---|---|---|
| V0 glm47flash→devstral | 1/19 | 1/19 | 2/19 | 7.0% (4/57) |
| note glm47flash→devstral | 0/19 | 0/19 | 2/19 | 3.5% (2/57) |
| Repo0 devstral | 1/19 | 1/19 | 2/19 | 7.0% (4/57) |
| V0 glm47flash→glm47flash (same) | 0/19 | 1/19 | 0/19 | 1.8% (1/57) |
| note glm47flash→glm47flash (same) | 2/19 | 0/19 | 0/19 | 3.5% (2/57) |
| Repo0 glm47flash (same) | 1/19 | 2/19 | 1/19 | 7.0% (4/57) |

| contrast (x − y) | mean per-task diff | 95% bootstrap CI | tasks x>y / x<y | sign-test p | per replicate |
|---|---|---|---|---|---|
| HRG glm47flash→devstral (V0) | +0.053 | [+0.000, +0.140] | 2 / 0 | 0.5 | +0.05, +0.00, +0.11 |
| HRG glm47flash→devstral (note) | +0.000 | [-0.053, +0.053] | 1 / 1 | 1 | -0.11, +0.00, +0.11 |
| FTV glm47flash→glm47flash (same) | -0.053 | [-0.140, +0.000] | 0 / 2 | 0.5 | -0.05, -0.05, -0.05 |
| FTV glm47flash→devstral | +0.000 | [-0.140, +0.123] | 2 / 1 | 1 | +0.00, +0.00, +0.00 |
| CTV glm47flash→glm47flash (same) | +0.018 | [+0.000, +0.053] | 1 / 0 | 1 | +0.11, -0.05, +0.00 |
| CTV glm47flash→devstral | -0.035 | [-0.123, +0.035] | 1 / 2 | 1 | -0.05, -0.05, +0.00 |
| capability devstral vs glm47flash on F_glm47flash | +0.000 | [-0.105, +0.105] | 1 / 1 | 1 | +0.00, -0.05, +0.05 |

HRG = cross-model − same-model rescue on the same Repo_t^A; FTV = rescue on Repo_t^A − Repo_0 control; CTV = with handoff note − without. Exploratory; many contrasts are reported, so single p-values are not evidence.
