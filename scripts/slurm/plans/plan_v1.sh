# Plan v1 (executed by gpu_job.sbatch after both endpoints are up). Every step must succeed (set -e).
# 1. spec §16: endpoint + tool-call probe, manifests
$PY scripts/preflight.py --config configs/validation_v0.yaml --endpoints --write-manifest
$PY scripts/preflight.py --config configs/pilot.yaml --endpoints --write-manifest
# 2. spec §16.5: trivial real-model agent smoke tests
for a in qwen devstral; do
  $PY scripts/dev/agent_smoke.py --config configs/pilot.yaml --agent $a --sif /path/to/scratch/fc_cache/deb.sif --out "$JOBLOG/agent_smoke"
done
# 3. Milestones 2 + 4 on held-out validation tasks (D-017); stop on any violated invariant
V="--config configs/validation_v0.yaml --tasks configs/tasks/validation_v0.json"
$PY scripts/run_stage.py $V --stage primary
$PY scripts/run_stage.py $V --stage recovery
$PY scripts/summarize_results.py $V
$PY scripts/check_validation.py $V | tee "$JOBLOG/validation_check.txt"
# 4. Milestone 5: Phase-0 calibration (= the primary runs of pilot_v0)
# D-011: the frozen task list must exist AND be committed before calibration starts (wait up to 4 h)
for i in $(seq 1 240); do
  if git ls-files --error-unmatch configs/tasks/calibration_v0.json >/dev/null 2>&1 && \
     [ -z "$(git status --porcelain configs/tasks/calibration_v0.json)" ]; then break; fi
  [ "$i" = 240 ] && { echo "[plan] calibration task list not committed; stopping"; exit 1; }
  sleep 60
done
C="--config configs/pilot.yaml --tasks configs/tasks/calibration_v0.json"
$PY scripts/run_stage.py $C --stage primary
$PY scripts/summarize_results.py $C
# 5. pre-registered rule D-016; recovery only if it passes
if $PY scripts/check_calibration_gate.py $C; then
  $PY scripts/run_stage.py $C --stage recovery
  $PY scripts/summarize_results.py $C
else
  echo "[plan] D-016 rule not met: stopping before recovery for task-mix review"
fi
