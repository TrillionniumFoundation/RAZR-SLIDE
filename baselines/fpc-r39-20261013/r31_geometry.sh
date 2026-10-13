#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: > verification/R31_geometry_progress.log
run() {
 local task="$1"
 echo "START $task $(date -u +%FT%TZ)" >> verification/R31_geometry_progress.log
 OPENBLAS_NUM_THREADS=1 python -u "${task}.py" >"verification/${task}_final.log" 2>&1
 echo "PASS $task $(date -u +%FT%TZ)" >> verification/R31_geometry_progress.log
}
run r31_integration
run r31_dynamic
run r31_tolerance
run r31_faults
run r31_section
run r31_export
