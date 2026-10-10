# Context-transfer pilot — `pilot_v2_r2` (source `pilot_v2`)

Generated 2026-10-10T06:20:05.270+00:00. Same Repo_t^A for every condition; comparisons paired by task. Small pilot: counts and intervals, not claims.

## devstral failed (N = 23)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral (same model) | 5/23 (22%, CI 10–42%) | 3/23 (13%, CI 5–32%) | 6/23 (26%, CI 13–46%) |
| glm47flash | 3/23 (13%, CI 5–32%) | 5/23 (22%, CI 10–42%) | 9/23 (39%, CI 22–59%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_devstral→devstral | -0.09 [-0.25, +0.08] (n=23; x✓y✗=1, x✗y✓=3; McNemar p=0.625) |
| FTV_devstral→devstral | -0.04 [-0.27, +0.18] (n=23; x✓y✗=3, x✗y✓=4; McNemar p=1) |
| FTV_note_devstral→devstral | -0.13 [-0.35, +0.09] (n=23; x✓y✗=2, x✗y✓=5; McNemar p=0.453) |
| CTV_devstral→glm47flash | +0.09 [-0.08, +0.25] (n=23; x✓y✗=3, x✗y✓=1; McNemar p=0.625) |
| FTV_devstral→glm47flash | -0.26 [-0.51, -0.01] (n=23; x✓y✗=2, x✗y✓=8; McNemar p=0.109) |
| FTV_note_devstral→glm47flash | -0.17 [-0.40, +0.06] (n=23; x✓y✗=2, x✗y✓=6; McNemar p=0.289) |
| HRG_devstral→glm47flash (V0) = capability/complementarity + state | -0.09 = +0.13 + -0.22 (n=23) |
| HRG_devstral→glm47flash (note) = capability/complementarity + state | +0.09 = +0.13 + -0.04 (n=23) |

## glm47flash failed (N = 25)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral | 5/25 (20%, CI 9–39%) | 6/25 (24%, CI 11–43%) | 8/25 (32%, CI 17–52%) |
| glm47flash (same model) | 8/25 (32%, CI 17–52%) | 4/25 (16%, CI 6–35%) | 9/25 (36%, CI 20–55%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_glm47flash→devstral | +0.04 [-0.13, +0.21] (n=25; x✓y✗=3, x✗y✓=2; McNemar p=1) |
| FTV_glm47flash→devstral | -0.12 [-0.35, +0.11] (n=25; x✓y✗=3, x✗y✓=6; McNemar p=0.508) |
| FTV_note_glm47flash→devstral | -0.08 [-0.35, +0.19] (n=25; x✓y✗=5, x✗y✓=7; McNemar p=0.774) |
| CTV_glm47flash→glm47flash | -0.16 [-0.40, +0.08] (n=25; x✓y✗=3, x✗y✓=7; McNemar p=0.344) |
| FTV_glm47flash→glm47flash | -0.04 [-0.32, +0.24] (n=25; x✓y✗=6, x✗y✓=7; McNemar p=1) |
| FTV_note_glm47flash→glm47flash | -0.20 [-0.42, +0.02] (n=25; x✓y✗=2, x✗y✓=7; McNemar p=0.18) |
| HRG_glm47flash→devstral (V0) = capability/complementarity + state | -0.12 = -0.04 + -0.08 (n=25) |
| HRG_glm47flash→devstral (note) = capability/complementarity + state | +0.08 = -0.04 + +0.12 (n=25) |

## Handoff notes

48 notes; median length 1984 chars; truncated conversations: 1; empty notes: 1.

CTV = note rescue − V0 rescue (value of the note); FTV = V0 rescue − Repo_0 control; FTV_note = note rescue − Repo_0 control. Wald CIs are rough at this n.
