#!/bin/bash
# Outcome-blind task selection + runtime gate on a compute node (CPU work; the partition requires 1 GPU).
#SBATCH -A YOUR_ACCOUNT
#SBATCH -p ai
#SBATCH -N 1
#SBATCH --gpus-per-node=1
#SBATCH -c 32
#SBATCH --mem=200G
#SBATCH -t 02:00:00
#SBATCH -J fc_select
#SBATCH -o /path/to/scratch/failure-complementarity/runs/_slurm/%x_%j.out
set -euo pipefail
cd /path/to/scratch/failure-complementarity
export APPTAINER_CACHEDIR=/path/to/scratch/fc_cache/apptainer FC_WORK_ROOT=${TMPDIR:-/tmp}/fc_work_${SLURM_JOB_ID}
mkdir -p "$FC_WORK_ROOT"
trap 'unshare -r rm -rf --one-file-system "$FC_WORK_ROOT" 2>/dev/null || true' EXIT
echo "[select] $(date -Is) host=$(hostname) git=$(git rev-parse HEAD)"
/path/to/scratch/conda_envs/fc/bin/python scripts/select_tasks.py --config configs/pilot.yaml \
  --out configs/tasks/calibration_v0.json --parallel 8
echo "[select] $(date -Is) done"
