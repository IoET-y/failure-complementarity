#!/bin/bash
# One H100 node: Qwen on GPUs 0,1 and Devstral on GPUs 2,3 (TP=2 each, decision D-013), runner on the same node.
# After both endpoints are healthy, the plan file given as $1 is executed with bash (read at run time).
#   sbatch scripts/slurm/gpu_job.sbatch scripts/slurm/plans/<plan>.sh
#SBATCH -A YOUR_ACCOUNT
#SBATCH -p ai
#SBATCH -N 1
#SBATCH --gpus-per-node=4
#SBATCH -c 64
#SBATCH --mem=600G
#SBATCH -t 20:00:00
#SBATCH -J fc_gpu
#SBATCH -o /path/to/scratch/failure-complementarity/runs/_slurm/%x_%j.out
set -euo pipefail
PLAN=${1:?usage: sbatch gpu_job.sbatch <plan.sh>}
export FC_PROJECT=/path/to/scratch/failure-complementarity
export FC_ENV=/path/to/scratch/conda_envs/fc FC_VLLM_ENV=/path/to/scratch/conda_envs/fc-vllm
export PY=$FC_ENV/bin/python
export HF_HOME=/path/to/scratch/fc_cache/hf HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export APPTAINER_CACHEDIR=/path/to/scratch/fc_cache/apptainer
export FC_WORK_ROOT=${TMPDIR:-/tmp}/fc_work_${SLURM_JOB_ID}
export JOBLOG=$FC_PROJECT/runs/_slurm/$SLURM_JOB_ID
mkdir -p "$JOBLOG" "$FC_WORK_ROOT"
cd "$FC_PROJECT"
echo "[job] $(date -Is) host=$(hostname) plan=$PLAN git=$(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)"
cp "$PLAN" "$JOBLOG/plan.sh"
nvidia-smi | tee "$JOBLOG/nvidia-smi.txt"
df -h "$FC_WORK_ROOT" /dev/shm | tee "$JOBLOG/df.txt"
avail_gb=$(df -BG --output=avail "$FC_WORK_ROOT" | tail -1 | tr -dc 0-9)
if [ "$avail_gb" -lt 150 ]; then echo "[job] node-local disk too small (${avail_gb}G)"; exit 1; fi

cleanup() {
  echo "[job] $(date -Is) cleanup"
  kill $(jobs -p) 2>/dev/null || true
  apptainer instance stop -a >/dev/null 2>&1 || true
  unshare -r rm -rf --one-file-system "$FC_WORK_ROOT" 2>/dev/null || true
}
trap cleanup EXIT

CUDA_VISIBLE_DEVICES=0,1 scripts/serve_model.sh qwen > "$JOBLOG/vllm_qwen.log" 2>&1 &
CUDA_VISIBLE_DEVICES=2,3 scripts/serve_model.sh devstral > "$JOBLOG/vllm_devstral.log" 2>&1 &

# resource monitor (spec §21): GPU, vLLM KV cache / throughput, CPU, RAM, disk — every 60 s
(
  while true; do
    ts=$(date -Is)
    nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader | sed "s/^/$ts gpu /"
    for port in 8001 8002; do
      curl -s --max-time 5 "http://127.0.0.1:$port/metrics" | grep -E '^vllm:(kv_cache_usage_perc|gpu_cache_usage_perc|num_requests_running|num_requests_waiting|generation_tokens_total|prompt_tokens_total)' | sed "s/^/$ts vllm$port /"
    done
    echo "$ts load $(cut -d' ' -f1-3 /proc/loadavg) mem_used_gb $(free -g | awk '/Mem/{print $3}') work_gb $(du -s -BG "$FC_WORK_ROOT" 2>/dev/null | cut -f1)"
    sleep 60
  done
) > "$JOBLOG/resources.log" 2>&1 &

for port in 8001 8002; do
  for i in $(seq 1 180); do
    if curl -s --max-time 5 "http://127.0.0.1:$port/v1/models" >/dev/null; then echo "[job] $(date -Is) port $port up"; break; fi
    sleep 10
    if [ "$i" = 180 ]; then echo "[job] server on $port did not come up"; tail -50 "$JOBLOG"/vllm_*.log; exit 1; fi
  done
done

echo "[job] $(date -Is) running plan"
bash -euo pipefail "$PLAN"
echo "[job] $(date -Is) plan finished"
