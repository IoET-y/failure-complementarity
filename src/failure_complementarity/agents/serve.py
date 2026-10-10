"""Render the documented vLLM launch command from agents.yaml (single source of truth).

    python -m failure_complementarity.agents.serve --config configs/pilot.yaml --agent qwen [--exec]
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil

from failure_complementarity.config import AgentSpec, load_experiment


def vllm_command(spec: AgentSpec, *, host: str = "127.0.0.1", vllm_bin: str = "vllm", port: int | None = None) -> list[str]:
    if spec.serve is None or spec.serve.engine != "vllm":
        raise ValueError(f"agent {spec.name!r} has no vllm serve block")
    if not spec.hf_repo or not spec.hf_revision:
        raise ValueError(f"agent {spec.name!r} must pin hf_repo and hf_revision before serving")
    s = spec.serve
    return [
        vllm_bin, "serve", spec.hf_repo,
        "--revision", spec.hf_revision,
        "--served-model-name", spec.model,
        "--host", host,
        "--port", str(port or s.port),
        "--tensor-parallel-size", str(s.tensor_parallel_size),
        "--max-model-len", str(s.max_model_len),
        "--gpu-memory-utilization", str(s.gpu_memory_utilization),
        *s.extra_args,
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--vllm-bin", default=os.environ.get("FC_VLLM_BIN", "vllm"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("FC_SERVE_PORT", "0")) or None)
    ap.add_argument("--exec", action="store_true", help="replace this process with the vLLM server")
    args = ap.parse_args()
    cfg = load_experiment(args.config)
    cmd = vllm_command(cfg.agent(args.agent), host=args.host, vllm_bin=args.vllm_bin, port=args.port)
    print(shlex.join(cmd), flush=True)
    if args.exec:
        os.environ.setdefault("HF_HOME", str(cfg.paths.hf_home))
        exe = shutil.which(cmd[0]) or cmd[0]
        os.execv(exe, cmd)


if __name__ == "__main__":
    main()
