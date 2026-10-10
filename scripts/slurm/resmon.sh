#!/bin/bash
# Resource monitor (spec §21) — deliberately no `set -e`: a failed probe must never stop the loop.
port=$1; work=$2
while true; do
  ts=$(date -Is)
  nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader | sed "s/^/$ts gpu /"
  curl -s --max-time 5 "http://127.0.0.1:$port/metrics" | grep -E '^vllm:(kv_cache_usage_perc|num_requests_running|num_requests_waiting|generation_tokens_total|prompt_tokens_total|num_preemptions_total)' | sed "s/^/$ts vllm /"
  echo "$ts load $(cut -d' ' -f1-3 /proc/loadavg) mem_used_gb $(free -g | awk '/Mem/{print $3}') work_gb $(du -s -BG "$work" 2>/dev/null | cut -f1)"
  sleep 60
done
