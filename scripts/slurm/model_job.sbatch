#!/bin/bash
# One model on TP x H100 (TP from agents.yaml; submit with --gpus-per-node=TP) + its worker (D-019, D-020).
#   sbatch --export=ALL,FC_AGENT=qwen     scripts/slurm/model_job.sbatch
#   sbatch --export=ALL,FC_AGENT=devstral scripts/slurm/model_job.sbatch
#SBATCH -A YOUR_ACCOUNT
#SBATCH -p ai
#SBATCH -N 1
#SBATCH --gpus-per-node=1
#SBATCH -c 8
#SBATCH --mem=240G   # ai partition enforces 240 GB per GPU anyway (JobDefaults DefMemPerGPU=240000)
#SBATCH -t 08:00:00   # short for backfill; stages are resumable, resubmit to continue
#SBATCH -J fc_model
#SBATCH -o /path/to/scratch/failure-complementarity/runs/_slurm/%x_%j.out
set -euo pipefail
AGENT=${FC_AGENT:?set FC_AGENT}
export FC_PROJECT=/path/to/scratch/failure-complementarity
export FC_ENV=/path/to/scratch/conda_envs/fc FC_VLLM_ENV=/path/to/scratch/conda_envs/fc-vllm
export PY=$FC_ENV/bin/python
export HF_HOME=/path/to/scratch/fc_cache/hf HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export APPTAINER_CACHEDIR=/path/to/scratch/fc_cache/apptainer
export FC_WORK_ROOT=${TMPDIR:-/tmp}/fc_work_${SLURM_JOB_ID}
export JOBLOG=$FC_PROJECT/runs/_slurm/${SLURM_JOB_ID}_${AGENT}
mkdir -p "$JOBLOG" "$FC_WORK_ROOT"
cd "$FC_PROJECT"
echo "[job] $(date -Is) host=$(hostname) agent=$AGENT git=$(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)"
bash scripts/check_env.sh || { echo "[job] environment drift: refusing to run (D-033)"; exit 1; }
nvidia-smi | tee "$JOBLOG/nvidia-smi.txt"
# D-019: every run of the experiment on the same GPU type
if nvidia-smi --query-gpu=name --format=csv,noheader | grep -qv "H100"; then echo "[job] non-H100 GPU; refusing"; exit 1; fi
df -h "$FC_WORK_ROOT" | tee "$JOBLOG/df.txt"
avail_gb=$(df -BG --output=avail "$FC_WORK_ROOT" | tail -1 | tr -dc 0-9)
[ "$avail_gb" -ge 100 ] || { echo "[job] node-local disk too small (${avail_gb}G)"; exit 1; }
# D-030: shared nodes -> pick a free port per job and point every process of this job at it
PORT=$($PY -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])")
export FC_SERVE_PORT=$PORT
export "FC_ENDPOINT_${AGENT^^}=http://127.0.0.1:$PORT/v1"
echo "[job] endpoint for $AGENT: http://127.0.0.1:$PORT/v1"
TP=$($PY -c "from failure_complementarity.config import load_experiment as l; print(l('configs/pilot.yaml').agent('$AGENT').serve.tensor_parallel_size)")
GPUS=$(seq -s, 0 $((TP-1)))
NGPU=$(nvidia-smi -L | wc -l)
[ "$NGPU" -ge "$TP" ] || { echo "[job] $AGENT needs $TP GPUs, job has $NGPU (submit with --gpus-per-node=$TP)"; exit 1; }

cleanup() {
  echo "[job] $(date -Is) cleanup"
  kill $(jobs -p) 2>/dev/null || true
  apptainer instance stop -a >/dev/null 2>&1 || true
  unshare -r rm -rf --one-file-system "$FC_WORK_ROOT" 2>/dev/null || true
}
trap cleanup EXIT

CUDA_VISIBLE_DEVICES=$GPUS scripts/serve_model.sh "$AGENT" > "$JOBLOG/vllm_${AGENT}.log" 2>&1 &
bash scripts/slurm/resmon.sh "$PORT" "$FC_WORK_ROOT" > "$JOBLOG/resources.log" 2>&1 &  # no set -e inside

for i in $(seq 1 180); do
  curl -s --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null && { echo "[job] $(date -Is) server up"; break; }
  [ "$i" = 180 ] && { echo "[job] server did not come up"; tail -80 "$JOBLOG/vllm_${AGENT}.log"; exit 1; }
  sleep 10
done
grep -E "version|Loading|weights|KV cache|maximum concurrency|tool" "$JOBLOG/vllm_${AGENT}.log" | head -40 || true

$PY scripts/preflight.py --config configs/validation_v1.yaml --endpoints --agents "$AGENT"
$PY scripts/dev/agent_smoke.py --config configs/pilot.yaml --agent "$AGENT" --sif /path/to/scratch/fc_cache/deb.sif --out "$JOBLOG/agent_smoke"
$PY ${FC_WORKER:-scripts/worker.py} --agent "$AGENT" ${FC_WORKER_ARGS:-}
echo "[job] $(date -Is) worker finished"
