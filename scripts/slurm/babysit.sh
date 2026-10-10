#!/bin/bash
# Resubmit a model's job if it left the queue before the experiment finished (stages are resumable).
# Usage: [PREFIX=fc_v2] babysit.sh <experiment_id> <cal-config> <cal-tasks> <val-config> <agent>...   (max 3 resubmissions per agent)
EXP=$1; CAL=$2; TASKS=$3; VAL=$4; shift 4
PREFIX=${PREFIX:-fc_v2}
ROOT=$(cd "$(dirname "$0")/../.." && pwd); cd "$ROOT"
declare -A n
done_flag() { grep -l "all stages done" runs/_slurm/worker_${1}_*.log 2>/dev/null | xargs -r grep -l "\[$EXP\]" 2>/dev/null | head -1; }
while true; do
  all=1
  for a in "$@"; do
    if [ -n "$(done_flag $a)" ]; then continue; fi
    all=0
    if ! squeue -u "$USER" -h -o %j | grep -qx "${PREFIX}_$a"; then
      n[$a]=$(( ${n[$a]:-0} + 1 ))
      if [ "${n[$a]}" -gt 3 ]; then echo "$(date -Is) $a: resubmission limit reached"; continue; fi
      jid=$(sbatch --parsable -J ${PREFIX}_$a -t 08:00:00 --export=ALL,FC_AGENT=$a,"FC_WORKER_ARGS=--skip-validation --val-config $VAL --cal-config $CAL --cal-tasks $TASKS" scripts/slurm/model_job.sbatch)
      echo "$(date -Is) resubmitted $a as $jid (#${n[$a]})"
    fi
  done
  [ $all = 1 ] && { echo "$(date -Is) all agents done"; exit 0; }
  sleep 300
done
