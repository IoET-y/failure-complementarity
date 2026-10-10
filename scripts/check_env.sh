#!/bin/bash
# Refuse to run if either Python environment differs from its committed lock file (env drift, decision D-033).
ROOT=$(cd "$(dirname "$0")/.." && pwd)
FC_ENV=${FC_ENV:-/path/to/scratch/conda_envs/fc}
FC_VLLM_ENV=${FC_VLLM_ENV:-/path/to/scratch/conda_envs/fc-vllm}
ok=0
for pair in "$FC_ENV:fc" "$FC_VLLM_ENV:fc-vllm"; do
  env=${pair%%:*}; name=${pair##*:}
  extra=""; [ "$name" = fc ] && extra="--exclude-editable"
  if ! diff <("$env/bin/pip" freeze $extra 2>/dev/null) "$ROOT/env/$name.lock.txt" > /tmp/envdiff_$$_$name; then
    echo "[check_env] $name environment differs from env/$name.lock.txt:"; head -20 /tmp/envdiff_$$_$name; ok=1
  fi
  rm -f /tmp/envdiff_$$_$name
done
[ $ok = 0 ] && echo "[check_env] both environments match their lock files"
exit $ok
