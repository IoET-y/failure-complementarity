# Pooled replicates — pilot_v2, pilot_v2_r2, pilot_v2_r3 (nonhard)

3 replicate(s) per task × condition on identical failed workspaces and notes. Rates: per replicate and pooled. Contrasts: per-task mean difference, bootstrap 95% CI over tasks, exact sign test over tasks.

## devstral failed (N = 23 tasks)

| condition | pilot_v2 | pilot_v2_r2 | pilot_v2_r3 | pooled |
|---|---|---|---|---|
| V0 devstral→devstral (same) | 5/23 | 5/23 | 4/23 | 20.3% (14/69) |
| note devstral→devstral (same) | 5/23 | 3/23 | 5/23 | 18.8% (13/69) |
| Repo0 devstral (same) | 6/23 | 6/23 | 5/23 | 24.6% (17/69) |
| V0 devstral→glm47flash | 2/23 | 3/23 | 6/23 | 15.9% (11/69) |
| note devstral→glm47flash | 5/23 | 5/23 | 4/23 | 20.3% (14/69) |
| Repo0 glm47flash | 4/23 | 9/23 | 6/23 | 27.5% (19/69) |

| contrast (x − y) | mean per-task diff | 95% bootstrap CI | tasks x>y / x<y | sign-test p | per replicate |
|---|---|---|---|---|---|
| HRG devstral→glm47flash (V0) | -0.043 | [-0.159, +0.072] | 5 / 6 | 1 | -0.13, -0.09, +0.09 |
| HRG devstral→glm47flash (note) | +0.014 | [-0.116, +0.145] | 4 / 3 | 1 | +0.00, +0.09, -0.04 |
| FTV devstral→devstral (same) | -0.043 | [-0.188, +0.087] | 5 / 6 | 1 | -0.04, -0.04, -0.04 |
| FTV devstral→glm47flash | -0.116 | [-0.261, +0.029] | 5 / 8 | 0.581 | -0.09, -0.26, +0.00 |
| CTV devstral→devstral (same) | -0.014 | [-0.145, +0.130] | 4 / 5 | 1 | +0.00, -0.09, +0.04 |
| CTV devstral→glm47flash | +0.043 | [-0.058, +0.145] | 6 / 4 | 0.754 | +0.13, +0.09, -0.09 |
| capability glm47flash vs devstral on F_devstral | +0.029 | [-0.087, +0.145] | 6 / 4 | 0.754 | -0.09, +0.13, +0.04 |

## glm47flash failed (N = 25 tasks)

| condition | pilot_v2 | pilot_v2_r2 | pilot_v2_r3 | pooled |
|---|---|---|---|---|
| V0 glm47flash→devstral | 7/25 | 5/25 | 6/25 | 24.0% (18/75) |
| note glm47flash→devstral | 6/25 | 6/25 | 4/25 | 21.3% (16/75) |
| Repo0 devstral | 8/25 | 8/25 | 7/25 | 30.7% (23/75) |
| V0 glm47flash→glm47flash (same) | 1/25 | 8/25 | 3/25 | 16.0% (12/75) |
| note glm47flash→glm47flash (same) | 6/25 | 4/25 | 4/25 | 18.7% (14/75) |
| Repo0 glm47flash (same) | 5/25 | 9/25 | 7/25 | 28.0% (21/75) |

| contrast (x − y) | mean per-task diff | 95% bootstrap CI | tasks x>y / x<y | sign-test p | per replicate |
|---|---|---|---|---|---|
| HRG glm47flash→devstral (V0) | +0.080 | [-0.027, +0.200] | 7 / 4 | 0.549 | +0.24, -0.12, +0.12 |
| HRG glm47flash→devstral (note) | +0.027 | [-0.040, +0.093] | 5 / 3 | 0.727 | +0.00, +0.08, +0.00 |
| FTV glm47flash→glm47flash (same) | -0.120 | [-0.267, +0.027] | 6 / 9 | 0.607 | -0.16, -0.04, -0.16 |
| FTV glm47flash→devstral | -0.067 | [-0.267, +0.133] | 5 / 9 | 0.424 | -0.04, -0.12, -0.04 |
| CTV glm47flash→glm47flash (same) | +0.027 | [-0.093, +0.160] | 5 / 7 | 0.774 | +0.20, -0.16, +0.04 |
| CTV glm47flash→devstral | -0.027 | [-0.147, +0.107] | 4 / 6 | 0.754 | -0.04, +0.04, -0.08 |
| capability devstral vs glm47flash on F_glm47flash | +0.027 | [-0.067, +0.120] | 5 / 4 | 1 | +0.12, -0.04, +0.00 |

HRG = cross-model − same-model rescue on the same Repo_t^A; FTV = rescue on Repo_t^A − Repo_0 control; CTV = with handoff note − without. Exploratory; many contrasts are reported, so single p-values are not evidence.
