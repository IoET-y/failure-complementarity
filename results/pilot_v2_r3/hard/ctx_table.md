# Context-transfer pilot — `pilot_v2_r3` (source `pilot_v2`)

Generated 2026-10-10T06:20:39.796+00:00. Same Repo_t^A for every condition; comparisons paired by task. Small pilot: counts and intervals, not claims.

## devstral failed (N = 20)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral (same model) | 1/20 (5%, CI 1–24%) | 1/20 (5%, CI 1–24%) | 2/20 (10%, CI 3–30%) |
| glm47flash | 1/20 (5%, CI 1–24%) | 1/20 (5%, CI 1–24%) | 1/20 (5%, CI 1–24%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_devstral→devstral | +0.00 [+0.00, +0.00] (n=20; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| FTV_devstral→devstral | -0.05 [-0.15, +0.05] (n=20; x✓y✗=0, x✗y✓=1; McNemar p=1) |
| FTV_note_devstral→devstral | -0.05 [-0.15, +0.05] (n=20; x✓y✗=0, x✗y✓=1; McNemar p=1) |
| CTV_devstral→glm47flash | +0.00 [+0.00, +0.00] (n=20; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| FTV_devstral→glm47flash | +0.00 [+0.00, +0.00] (n=20; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| FTV_note_devstral→glm47flash | +0.00 [+0.00, +0.00] (n=20; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| HRG_devstral→glm47flash (V0) = capability/complementarity + state | +0.00 = -0.05 + +0.05 (n=20) |
| HRG_devstral→glm47flash (note) = capability/complementarity + state | +0.00 = -0.05 + +0.05 (n=20) |

## glm47flash failed (N = 19)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| devstral | 2/19 (11%, CI 3–31%) | 2/19 (11%, CI 3–31%) | 2/19 (11%, CI 3–31%) |
| glm47flash (same model) | 0/19 (0%, CI 0–17%) | 0/19 (0%, CI 0–17%) | 1/19 (5%, CI 1–25%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_glm47flash→devstral | +0.00 [-0.15, +0.15] (n=19; x✓y✗=1, x✗y✓=1; McNemar p=1) |
| FTV_glm47flash→devstral | +0.00 [-0.15, +0.15] (n=19; x✓y✗=1, x✗y✓=1; McNemar p=1) |
| FTV_note_glm47flash→devstral | +0.00 [-0.15, +0.15] (n=19; x✓y✗=1, x✗y✓=1; McNemar p=1) |
| CTV_glm47flash→glm47flash | +0.00 [+0.00, +0.00] (n=19; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| FTV_glm47flash→glm47flash | -0.05 [-0.15, +0.05] (n=19; x✓y✗=0, x✗y✓=1; McNemar p=1) |
| FTV_note_glm47flash→glm47flash | -0.05 [-0.15, +0.05] (n=19; x✓y✗=0, x✗y✓=1; McNemar p=1) |
| HRG_glm47flash→devstral (V0) = capability/complementarity + state | +0.11 = +0.05 + +0.05 (n=19) |
| HRG_glm47flash→devstral (note) = capability/complementarity + state | +0.11 = +0.05 + +0.05 (n=19) |

## Handoff notes

39 notes; median length 1950 chars; truncated conversations: 2; empty notes: 0.

CTV = note rescue − V0 rescue (value of the note); FTV = V0 rescue − Repo_0 control; FTV_note = note rescue − Repo_0 control. Wald CIs are rough at this n.
