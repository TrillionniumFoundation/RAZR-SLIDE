#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification cad
: >verification/R30_geometry_progress.log
run() {
 local task="$1"
 echo "START $task $(date -u +%FT%TZ)" >>verification/R30_geometry_progress.log
 OPENBLAS_NUM_THREADS=1 python -u "$task.py" >"verification/${task}_final.log" 2>&1
 echo "PASS $task $(date -u +%FT%TZ)" >>verification/R30_geometry_progress.log
}
run r30_integration
run r30_dynamic
run r30_tolerance
run r30_retention
run r30_faults
run r30_section
run r30_export
