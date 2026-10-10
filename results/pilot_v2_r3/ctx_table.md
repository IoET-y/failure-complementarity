# Context-transfer pilot — `pilot_v2_r3` (source `pilot_v2`)

Generated 2026-10-10T06:20:22.524+00:00. Same Repo_t^A for every condition; comparisons paired by task. Small pilot: counts and intervals, not claims.

## devstral failed (N = 43)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral (same model) | 5/43 (12%, CI 5–24%) | 6/43 (14%, CI 7–27%) | 7/43 (16%, CI 8–30%) |
| glm47flash | 7/43 (16%, CI 8–30%) | 5/43 (12%, CI 5–24%) | 7/43 (16%, CI 8–30%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_devstral→devstral | +0.02 [-0.10, +0.14] (n=43; x✓y✗=4, x✗y✓=3; McNemar p=1) |
| FTV_devstral→devstral | -0.05 [-0.16, +0.06] (n=43; x✓y✗=2, x✗y✓=4; McNemar p=0.688) |
| FTV_note_devstral→devstral | -0.02 [-0.14, +0.10] (n=43; x✓y✗=3, x✗y✓=4; McNemar p=1) |
| CTV_devstral→glm47flash | -0.05 [-0.19, +0.10] (n=43; x✓y✗=4, x✗y✓=6; McNemar p=0.754) |
| FTV_devstral→glm47flash | +0.00 [-0.13, +0.13] (n=43; x✓y✗=4, x✗y✓=4; McNemar p=1) |
| FTV_note_devstral→glm47flash | -0.05 [-0.19, +0.10] (n=43; x✓y✗=4, x✗y✓=6; McNemar p=0.754) |
| HRG_devstral→glm47flash (V0) = capability/complementarity + state | +0.05 = +0.00 + +0.05 (n=43) |
| HRG_devstral→glm47flash (note) = capability/complementarity + state | -0.02 = +0.00 + -0.02 (n=43) |

## glm47flash failed (N = 44)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral | 8/44 (18%, CI 10–32%) | 6/44 (14%, CI 6–27%) | 9/44 (20%, CI 11–35%) |
| glm47flash (same model) | 3/44 (7%, CI 2–18%) | 4/44 (9%, CI 4–21%) | 8/44 (18%, CI 10–32%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_glm47flash→devstral | -0.05 [-0.15, +0.06] (n=44; x✓y✗=2, x✗y✓=4; McNemar p=0.688) |
| FTV_glm47flash→devstral | -0.02 [-0.17, +0.12] (n=44; x✓y✗=5, x✗y✓=6; McNemar p=1) |
| FTV_note_glm47flash→devstral | -0.07 [-0.20, +0.06] (n=44; x✓y✗=3, x✗y✓=6; McNemar p=0.508) |
| CTV_glm47flash→glm47flash | +0.02 [-0.08, +0.12] (n=44; x✓y✗=3, x✗y✓=2; McNemar p=1) |
| FTV_glm47flash→glm47flash | -0.11 [-0.23, -0.00] (n=44; x✓y✗=1, x✗y✓=6; McNemar p=0.125) |
| FTV_note_glm47flash→glm47flash | -0.09 [-0.21, +0.03] (n=44; x✓y✗=2, x✗y✓=6; McNemar p=0.289) |
| HRG_glm47flash→devstral (V0) = capability/complementarity + state | +0.11 = +0.02 + +0.09 (n=44) |
| HRG_glm47flash→devstral (note) = capability/complementarity + state | +0.05 = +0.02 + +0.02 (n=44) |

## Handoff notes

87 notes; median length 1950 chars; truncated conversations: 3; empty notes: 1.

CTV = note rescue − V0 rescue (value of the note); FTV = V0 rescue − Repo_0 control; FTV_note = note rescue − Repo_0 control. Wald CIs are rough at this n.
