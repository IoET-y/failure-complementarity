# Context-transfer pilot — `ctx_v1` (source `pilot_v1`)

Generated 2026-10-08T13:39:11.881+00:00. Same Repo_t^A for every condition; comparisons paired by task. Small pilot: counts and intervals, not claims.

## qwen failed (N = 31)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| qwen (same model) | 3/31 (10%, CI 3–25%) | 1/31 (3%, CI 1–16%) | 2/31 (6%, CI 2–21%) |
| devstral | 11/31 (35%, CI 21–53%) | 7/31 (23%, CI 11–40%) | 12/31 (39%, CI 24–56%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_qwen→qwen | -0.06 [-0.15, +0.02] (n=31; x✓y✗=0, x✗y✓=2; McNemar p=0.5) |
| FTV_qwen→qwen | +0.03 [-0.08, +0.14] (n=31; x✓y✗=2, x✗y✓=1; McNemar p=1) |
| FTV_note_qwen→qwen | -0.03 [-0.14, +0.08] (n=31; x✓y✗=1, x✗y✓=2; McNemar p=1) |
| CTV_qwen→devstral | -0.13 [-0.30, +0.04] (n=31; x✓y✗=2, x✗y✓=6; McNemar p=0.289) |
| FTV_qwen→devstral | -0.03 [-0.22, +0.16] (n=31; x✓y✗=4, x✗y✓=5; McNemar p=1) |
| FTV_note_qwen→devstral | -0.16 [-0.34, +0.02] (n=31; x✓y✗=2, x✗y✓=7; McNemar p=0.18) |
| HRG_qwen→devstral (V0) = capability/complementarity + state | +0.26 = +0.32 + -0.06 (n=31) |
| HRG_qwen→devstral (note) = capability/complementarity + state | +0.19 = +0.32 + -0.13 (n=31) |

## devstral failed (N = 16)

| rescuer | V0 rescue (Repo_t) | note rescue (Repo_t + note) | Repo_0 control |
|---|---|---|---|
| qwen | 0/16 (0%, CI 0–19%) | 0/16 (0%, CI 0–19%) | 0/16 (0%, CI 0–19%) |
| devstral (same model) | 1/16 (6%, CI 1–28%) | 0/16 (0%, CI 0–19%) | 2/16 (12%, CI 3–36%) |

| quantity | paired difference [95% Wald CI] |
|---|---|
| CTV_devstral→qwen | +0.00 [+0.00, +0.00] (n=16; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| FTV_devstral→qwen | +0.00 [+0.00, +0.00] (n=16; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| FTV_note_devstral→qwen | +0.00 [+0.00, +0.00] (n=16; x✓y✗=0, x✗y✓=0; McNemar p=1) |
| CTV_devstral→devstral | -0.06 [-0.18, +0.06] (n=16; x✓y✗=0, x✗y✓=1; McNemar p=1) |
| FTV_devstral→devstral | -0.06 [-0.27, +0.15] (n=16; x✓y✗=1, x✗y✓=2; McNemar p=1) |
| FTV_note_devstral→devstral | -0.12 [-0.29, +0.04] (n=16; x✓y✗=0, x✗y✓=2; McNemar p=0.5) |
| HRG_devstral→qwen (V0) = capability/complementarity + state | -0.06 = -0.12 + +0.06 (n=16) |
| HRG_devstral→qwen (note) = capability/complementarity + state | +0.00 = -0.12 + +0.12 (n=16) |

## Handoff notes

47 notes; median length 1773 chars; truncated conversations: 0; empty notes: 0.

CTV = note rescue − V0 rescue (value of the note); FTV = V0 rescue − Repo_0 control; FTV_note = note rescue − Repo_0 control. Wald CIs are rough at this n.
