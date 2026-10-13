#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification cad
: > verification/R29_geometry_progress.log
run() {
  local task="$1"
  echo "START $task $(date -u +%FT%TZ)" >>verification/R29_geometry_progress.log
  OPENBLAS_NUM_THREADS=1 python -u "$task.py" >"verification/${task}_run.log" 2>&1
  echo "PASS $task $(date -u +%FT%TZ)" >>verification/R29_geometry_progress.log
}
run r29_integration
run r29_dynamic
run r29_faults
run r29_clearance
run r29_presence_study
run r29_ear_section
run r29_export
