# Environment and Version Pins

Recorded 2026-10-06. Every run additionally captures its live environment in `runs/<exp>/manifest.json`
(packages, Apptainer, Slurm job, GPUs/driver/CUDA, endpoint server versions).

## Cluster

| Item | Value |
|---|---|
| System | Purdue RCAC **Anvil** (Rocky Linux 8.10, kernel 4.18.0-553.162.1.el8_10); any Slurm cluster with Apptainer and H100-class GPUs should work |
| Allocation | a GPU allocation on partition `ai` (H100 nodes; the site enforces 240 GB RAM per GPU and a 2-day wall-time); billing 1 SU = 1 GPU-hour. Account name replaced by `YOUR_ACCOUNT` in the job scripts |
| GPU nodes | `h000–h020`: 4× H100 80 GB, 96 cores, ~1 TB RAM, local `/tmp` |
| Login node | no GPU; fine for builds/tests, **not** for model serving or agent runs |
| Containers | **Apptainer 1.5.3** (no Docker, no Modal) → decision D-002 |
| git | 2.43.7 |

### Storage — important

| Path | Use | Policy |
|---|---|---|
| `/path/to/scratch` | code, envs, caches, live runs | **purged: files not accessed for 30 days**, not backed up |
| `/path/to/projects` | durable archive of `runs/` and `results/` | 5 TB group quota (~1 TB used) |
| `$HOME` | nothing large | 25 GB quota, already ~80% full; never point caches here |

Push the git repository to a remote and copy finished experiment directories to the projects space; scratch
is not durable storage for paper results.

## Pinned components

| Component | Pin | Verified how |
|---|---|---|
| Benchmark | SWE-bench Pro V2 **v2.0.0**, `scaleapi/SWE-bench_Pro-os` @ `66f92766bba642462d4bbe5479e83f91f9211862` | `git rev-parse`, `v2/SHA256SUMS` (6436 files OK) — checked by `scripts/preflight.py` |
| Benchmark (HF mirror, reference only) | `ScaleAI/SWE-bench_Pro` rev `2d52cb3df914a3fcf80c7f66738b3a88ae37fc50` | HF API |
| Task images | `ghcr.io/scaleapi/swe-bench_pro-v2:<instance_id>` → SIF | digest recorded per task (Milestone 2) |
| Harness | **mini-swe-agent 2.4.6** (PyPI) | `pip freeze` |
| LLM client | litellm 1.104.0, openai 2.54.0 | `pip freeze` |
| Runner Python | 3.12.15 (conda env `fc`) | |
| Inference server | **vLLM 0.31.0**, torch 2.13.0, transformers 5.17.0, mistral_common 1.12.0, flashinfer 0.7.0.post1 (conda env `fc-vllm`, Python 3.12) | `pip freeze`; server `/version` recorded per run |
| Qwen | `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8` @ `dcaee4d4dfc5ee71ad501f01f530e5652438fde0` (official FP8, Apache-2.0, not gated; D-020) | HF API |
| Devstral | `mistralai/Devstral-Small-2-24B-Instruct-2512` @ `55c5b41e98c2dbd21b0c8afffc540dcfc9eb5128` (official release is FP8, Apache-2.0, not gated) | HF API |
| CUDA driver / GPU | recorded automatically on the first GPU job (`manifest.json → environment.gpu`) | `nvidia-smi` |

## Setup from scratch

```bash
export SCR=/path/to/scratch
export CONDA_PKGS_DIRS=$SCR/conda_pkgs PIP_CACHE_DIR=$SCR/pip_cache
export APPTAINER_CACHEDIR=$SCR/fc_cache/apptainer HF_HOME=$SCR/fc_cache/hf

# 1. benchmark (exact release commit)
git clone https://github.com/scaleapi/SWE-bench_Pro-os.git $SCR/fc_vendor/SWE-bench_Pro-os
git -C $SCR/fc_vendor/SWE-bench_Pro-os checkout 66f92766bba642462d4bbe5479e83f91f9211862

# 2. runner env
conda create -y -p $SCR/conda_envs/fc python=3.12
$SCR/conda_envs/fc/bin/pip install -e "$SCR/failure-complementarity[dev]"     # pins mini-swe-agent==2.4.6

# 3. serving env (kept separate: the runner only needs an OpenAI-compatible endpoint)
conda create -y -p $SCR/conda_envs/fc-vllm python=3.12
$SCR/conda_envs/fc-vllm/bin/pip install "vllm==0.31.0" "mistral_common>=1.8.6"

# 4. checks
cd $SCR/failure-complementarity
$SCR/conda_envs/fc/bin/python -m pytest
$SCR/conda_envs/fc/bin/python scripts/preflight.py --config configs/pilot.yaml
```

## Model serving

Launch commands are rendered from `configs/agents.yaml` (single source of truth) by
`scripts/serve_model.sh <agent>`. One H100 per model (D-020); in practice each model runs in its own Slurm job
(`scripts/slurm/model_job.sbatch`, D-019):

```bash
CUDA_VISIBLE_DEVICES=0 scripts/serve_model.sh qwen
# vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 --revision dcaee4d4… --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
#   --host 127.0.0.1 --port 8001 --tensor-parallel-size 1 --max-model-len 131072 --gpu-memory-utilization 0.9
#   --enable-auto-tool-choice --tool-call-parser qwen3_coder
CUDA_VISIBLE_DEVICES=0 scripts/serve_model.sh devstral
# vllm serve mistralai/Devstral-Small-2-24B-Instruct-2512 --revision 55c5b41e… --served-model-name mistralai/Devstral-Small-2-24B-Instruct-2512
#   --host 127.0.0.1 --port 8002 --tensor-parallel-size 1 --max-model-len 131072 --gpu-memory-utilization 0.9
#   --enable-auto-tool-choice --tool-call-parser mistral
```

Model-specific settings:

* **Qwen3-Coder:** tool-call parser `qwen3_coder` (built into vLLM 0.31.0; the HF repo also ships
  `qwen3coder_tool_parser.py`, not used). Chat template from the HF repo (`chat_template.jinja`).
* **Devstral Small 2:** tool-call parser `mistral`; requires `mistral_common >= 1.8.6` (installed 1.12.0). Flags
  follow the model card's vLLM command (it uses `--tensor-parallel-size 2` and `--max-model-len 262144`; we use
  131072 for both models, decision D-008).
* Both use `--enable-auto-tool-choice`, which mini-swe-agent's tool-calling mode needs.

**Still to verify on a GPU node before any experiment** (spec §16): that both checkpoints load, that the
chat templates render, that `scripts/preflight.py --endpoints` passes the bash tool-call probe for both, and one
trivial agent smoke test. Never substitute a fallback model: the preflight check fails if the served model id
differs from the configured one.

## Container runtime (decision D-002)

Per branch: `apptainer build --sandbox <node-local>/rootfs <task>.sif`, then

```bash
apptainer instance start --containall --cleanenv --no-home --no-mount tmp \
    --fakeroot --ignore-fakeroot-command --writable --net --network none <rootfs> <name>
apptainer exec --cleanenv --pwd /app instance://<name> bash -c '<agent command>'
```

Evaluation: fresh pristine sandbox, apply the diff, then run `bash /tests/test.sh` with
`-B tests:/tests:ro -B logs:/logs` and network enabled (`/tests` and `/logs` mount points pre-created).
Per-task SIF ≈ 0.7 GB (NodeBB example; 2.5 min to build on the login node); unpacked sandbox ≈ 1.9 GB.
