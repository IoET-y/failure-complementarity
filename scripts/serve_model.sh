#!/bin/bash
# Launch one model server from configs/agents.yaml (the YAML is the single source of truth).
#   scripts/serve_model.sh <agent_name> [config=configs/pilot.yaml]
# Must run on a GPU node. Uses the vLLM env (FC_VLLM_ENV) for the server and the project env (FC_ENV)
# only to render the command. See docs/environment.md.
set -euo pipefail
AGENT=${1:?usage: serve_model.sh <agent_name> [config]}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CONFIG=${2:-$ROOT/configs/pilot.yaml}
FC_ENV=${FC_ENV:-/path/to/scratch/conda_envs/fc}
FC_VLLM_ENV=${FC_VLLM_ENV:-/path/to/scratch/conda_envs/fc-vllm}
export HF_HOME=${HF_HOME:-/path/to/scratch/fc_cache/hf}
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
# FlashInfer JIT-compiles its sampling kernel on first use (needs ninja/nvcc on compute nodes); vLLM's PyTorch
# top-k/top-p sampler draws from the same distribution without compilation. Same setting for every model.
export VLLM_USE_FLASHINFER_SAMPLER=0
export PATH="$FC_VLLM_ENV/bin:$PATH"
export FC_VLLM_BIN="$FC_VLLM_ENV/bin/vllm"
echo "[serve_model] host=$(hostname) agent=$AGENT CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
"$FC_VLLM_ENV/bin/python" -c 'import vllm, sys; print("[serve_model] vllm", vllm.__version__, "python", sys.version.split()[0])'
exec "$FC_ENV/bin/python" -m failure_complementarity.agents.serve --config "$CONFIG" --agent "$AGENT" --exec
