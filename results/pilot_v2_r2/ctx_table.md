# Context-transfer pilot — `pilot_v2_r2` (source `pilot_v2`)

Generated 2026-10-10T06:19:30.657+00:00. Same Repo_t^A for every condition; comparisons paired by task. Small pilot: counts and intervals, not claims.

## devstral failed (N = 43)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral (same model) | 6/43 (14%, CI 7–27%) | 5/43 (12%, CI 5–24%) | 8/43 (19%, CI 10–33%) |
| glm47flash | 3/43 (7%, CI 2–19%) | 5/43 (12%, CI 5–24%) | 11/43 (26%, CI 15–40%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_devstral→devstral | -0.02 [-0.12, +0.08] (n=43; x✓y✗=2, x✗y✓=3; McNemar p=1) |
| FTV_devstral→devstral | -0.05 [-0.17, +0.08] (n=43; x✓y✗=3, x✗y✓=5; McNemar p=0.727) |
| FTV_note_devstral→devstral | -0.07 [-0.20, +0.07] (n=43; x✓y✗=3, x✗y✓=6; McNemar p=0.508) |
| CTV_devstral→glm47flash | +0.05 [-0.04, +0.14] (n=43; x✓y✗=3, x✗y✓=1; McNemar p=0.625) |
| FTV_devstral→glm47flash | -0.19 [-0.33, -0.04] (n=43; x✓y✗=2, x✗y✓=10; McNemar p=0.0386) |
| FTV_note_devstral→glm47flash | -0.14 [-0.28, -0.00] (n=43; x✓y✗=2, x✗y✓=8; McNemar p=0.109) |
| HRG_devstral→glm47flash (V0) = capability/complementarity + state | -0.07 = +0.07 + -0.14 (n=43) |
| HRG_devstral→glm47flash (note) = capability/complementarity + state | +0.00 = +0.07 + -0.07 (n=43) |

## glm47flash failed (N = 44)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral | 6/44 (14%, CI 6–27%) | 6/44 (14%, CI 6–27%) | 9/44 (20%, CI 11–35%) |
| glm47flash (same model) | 9/44 (20%, CI 11–35%) | 4/44 (9%, CI 4–21%) | 11/44 (25%, CI 15–39%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_glm47flash→devstral | +0.00 [-0.11, +0.11] (n=44; x✓y✗=3, x✗y✓=3; McNemar p=1) |
| FTV_glm47flash→devstral | -0.07 [-0.21, +0.08] (n=44; x✓y✗=4, x✗y✓=7; McNemar p=0.549) |
| FTV_note_glm47flash→devstral | -0.07 [-0.23, +0.09] (n=44; x✓y✗=5, x✗y✓=8; McNemar p=0.581) |
| CTV_glm47flash→glm47flash | -0.11 [-0.26, +0.03] (n=44; x✓y✗=3, x✗y✓=8; McNemar p=0.227) |
| FTV_glm47flash→glm47flash | -0.05 [-0.21, +0.12] (n=44; x✓y✗=6, x✗y✓=8; McNemar p=0.791) |
| FTV_note_glm47flash→glm47flash | -0.16 [-0.30, -0.02] (n=44; x✓y✗=2, x✗y✓=9; McNemar p=0.0654) |
| HRG_glm47flash→devstral (V0) = capability/complementarity + state | -0.07 = -0.05 + -0.02 (n=44) |
| HRG_glm47flash→devstral (note) = capability/complementarity + state | +0.05 = -0.05 + +0.09 (n=44) |

## Handoff notes

87 notes; median length 1950 chars; truncated conversations: 3; empty notes: 1.

CTV = note rescue − V0 rescue (value of the note); FTV = V0 rescue − Repo_0 control; FTV_note = note rescue − Repo_0 control. Wald CIs are rough at this n.
