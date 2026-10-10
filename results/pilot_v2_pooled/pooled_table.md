# Pooled replicates — pilot_v2, pilot_v2_r2, pilot_v2_r3

3 replicate(s) per task × condition on identical failed workspaces and notes. Rates: per replicate and pooled. Contrasts: per-task mean difference, bootstrap 95% CI over tasks, exact sign test over tasks.

## devstral failed (N = 43 tasks)

| condition | pilot_v2 | pilot_v2_r2 | pilot_v2_r3 | pooled |
|---|---|---|---|---|
| V0 devstral→devstral (same) | 7/43 | 6/43 | 5/43 | 14.0% (18/129) |
| note devstral→devstral (same) | 6/43 | 5/43 | 6/43 | 13.2% (17/129) |
| Repo0 devstral (same) | 7/43 | 8/43 | 7/43 | 17.1% (22/129) |
| V0 devstral→glm47flash | 3/43 | 3/43 | 7/43 | 10.1% (13/129) |
| note devstral→glm47flash | 5/43 | 5/43 | 5/43 | 11.6% (15/129) |
| Repo0 glm47flash | 5/43 | 11/43 | 7/43 | 17.8% (23/129) |

| contrast (x − y) | mean per-task diff | 95% bootstrap CI | tasks x>y / x<y | sign-test p | per replicate |
|---|---|---|---|---|---|
| HRG devstral→glm47flash (V0) | -0.039 | [-0.109, +0.023] | 5 / 8 | 0.581 | -0.09, -0.07, +0.05 |
| HRG devstral→glm47flash (note) | -0.016 | [-0.093, +0.062] | 5 / 5 | 1 | -0.02, +0.00, -0.02 |
| FTV devstral→devstral (same) | -0.031 | [-0.109, +0.047] | 6 / 8 | 0.791 | +0.00, -0.05, -0.05 |
| FTV devstral→glm47flash | -0.078 | [-0.163, +0.008] | 5 / 9 | 0.424 | -0.05, -0.19, +0.00 |
| CTV devstral→devstral (same) | -0.008 | [-0.078, +0.070] | 5 / 6 | 1 | -0.02, -0.02, +0.02 |
| CTV devstral→glm47flash | +0.016 | [-0.039, +0.078] | 6 / 5 | 1 | +0.05, +0.05, -0.05 |
| capability glm47flash vs devstral on F_devstral | +0.008 | [-0.070, +0.085] | 7 / 6 | 1 | -0.05, +0.07, +0.00 |

## glm47flash failed (N = 44 tasks)

| condition | pilot_v2 | pilot_v2_r2 | pilot_v2_r3 | pooled |
|---|---|---|---|---|
| V0 glm47flash→devstral | 8/44 | 6/44 | 8/44 | 16.7% (22/132) |
| note glm47flash→devstral | 6/44 | 6/44 | 6/44 | 13.6% (18/132) |
| Repo0 devstral | 9/44 | 9/44 | 9/44 | 20.5% (27/132) |
| V0 glm47flash→glm47flash (same) | 1/44 | 9/44 | 3/44 | 9.8% (13/132) |
| note glm47flash→glm47flash (same) | 8/44 | 4/44 | 4/44 | 12.1% (16/132) |
| Repo0 glm47flash (same) | 6/44 | 11/44 | 8/44 | 18.9% (25/132) |

| contrast (x − y) | mean per-task diff | 95% bootstrap CI | tasks x>y / x<y | sign-test p | per replicate |
|---|---|---|---|---|---|
| HRG glm47flash→devstral (V0) | +0.068 | [+0.000, +0.144] | 9 / 4 | 0.267 | +0.16, -0.07, +0.11 |
| HRG glm47flash→devstral (note) | +0.015 | [-0.030, +0.061] | 6 / 4 | 0.754 | -0.05, +0.05, +0.05 |
| FTV glm47flash→glm47flash (same) | -0.091 | [-0.182, -0.008] | 6 / 11 | 0.332 | -0.11, -0.05, -0.11 |
| FTV glm47flash→devstral | -0.038 | [-0.167, +0.091] | 7 / 10 | 0.629 | -0.02, -0.07, -0.02 |
| CTV glm47flash→glm47flash (same) | +0.023 | [-0.045, +0.106] | 6 / 7 | 1 | +0.16, -0.11, +0.02 |
| CTV glm47flash→devstral | -0.030 | [-0.106, +0.053] | 5 / 8 | 0.581 | -0.05, +0.00, -0.05 |
| capability devstral vs glm47flash on F_glm47flash | +0.015 | [-0.053, +0.083] | 6 / 5 | 1 | +0.07, -0.05, +0.02 |

HRG = cross-model − same-model rescue on the same Repo_t^A; FTV = rescue on Repo_t^A − Repo_0 control; CTV = with handoff note − without. Exploratory; many contrasts are reported, so single p-values are not evidence.
