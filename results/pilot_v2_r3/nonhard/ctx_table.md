# Context-transfer pilot — `pilot_v2_r3` (source `pilot_v2`)

Generated 2026-10-10T06:20:56.490+00:00. Same Repo_t^A for every condition; comparisons paired by task. Small pilot: counts and intervals, not claims.

## devstral failed (N = 23)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral (same model) | 4/23 (17%, CI 7–37%) | 5/23 (22%, CI 10–42%) | 5/23 (22%, CI 10–42%) |
| glm47flash | 6/23 (26%, CI 13–46%) | 4/23 (17%, CI 7–37%) | 6/23 (26%, CI 13–46%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_devstral→devstral | +0.04 [-0.18, +0.27] (n=23; x✓y✗=4, x✗y✓=3; McNemar p=1) |
| FTV_devstral→devstral | -0.04 [-0.23, +0.15] (n=23; x✓y✗=2, x✗y✓=3; McNemar p=1) |
| FTV_note_devstral→devstral | +0.00 [-0.21, +0.21] (n=23; x✓y✗=3, x✗y✓=3; McNemar p=1) |
| CTV_devstral→glm47flash | -0.09 [-0.35, +0.18] (n=23; x✓y✗=4, x✗y✓=6; McNemar p=0.754) |
| FTV_devstral→glm47flash | +0.00 [-0.24, +0.24] (n=23; x✓y✗=4, x✗y✓=4; McNemar p=1) |
| FTV_note_devstral→glm47flash | -0.09 [-0.35, +0.18] (n=23; x✓y✗=4, x✗y✓=6; McNemar p=0.754) |
| HRG_devstral→glm47flash (V0) = capability/complementarity + state | +0.09 = +0.04 + +0.04 (n=23) |
| HRG_devstral→glm47flash (note) = capability/complementarity + state | -0.04 = +0.04 + -0.09 (n=23) |

## glm47flash failed (N = 25)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral | 6/25 (24%, CI 11–43%) | 4/25 (16%, CI 6–35%) | 7/25 (28%, CI 14–48%) |
| glm47flash (same model) | 3/25 (12%, CI 4–30%) | 4/25 (16%, CI 6–35%) | 7/25 (28%, CI 14–48%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_glm47flash→devstral | -0.08 [-0.23, +0.07] (n=25; x✓y✗=1, x✗y✓=3; McNemar p=0.625) |
| FTV_glm47flash→devstral | -0.04 [-0.27, +0.19] (n=25; x✓y✗=4, x✗y✓=5; McNemar p=1) |
| FTV_note_glm47flash→devstral | -0.12 [-0.32, +0.08] (n=25; x✓y✗=2, x✗y✓=5; McNemar p=0.453) |
| CTV_glm47flash→glm47flash | +0.04 [-0.13, +0.21] (n=25; x✓y✗=3, x✗y✓=2; McNemar p=1) |
| FTV_glm47flash→glm47flash | -0.16 [-0.34, +0.02] (n=25; x✓y✗=1, x✗y✓=5; McNemar p=0.219) |
| FTV_note_glm47flash→glm47flash | -0.12 [-0.32, +0.08] (n=25; x✓y✗=2, x✗y✓=5; McNemar p=0.453) |
| HRG_glm47flash→devstral (V0) = capability/complementarity + state | +0.12 = +0.00 + +0.12 (n=25) |
| HRG_glm47flash→devstral (note) = capability/complementarity + state | +0.00 = +0.00 + +0.00 (n=25) |

## Handoff notes

48 notes; median length 1984 chars; truncated conversations: 1; empty notes: 1.

CTV = note rescue − V0 rescue (value of the note); FTV = V0 rescue − Repo_0 control; FTV_note = note rescue − Repo_0 control. Wald CIs are rough at this n.
