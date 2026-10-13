#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification
: > verification/R32_geometry_progress.log
run() {
 local script="$1"
 echo "START $script $(date -u +%FT%TZ)" >>verification/R32_geometry_progress.log
 OPENBLAS_NUM_THREADS=1 python -u "$script.py" >"verification/R32_${script}_final.log" 2>&1
 echo "PASS $script $(date -u +%FT%TZ)" >>verification/R32_geometry_progress.log
}
run r32_freeze
run r32_integration
run r32_envelope
run r32_dynamic
run r32_tolerance
run r32_faults
run r32_vendor_fit
run r32_export
OPENBLAS_NUM_THREADS=1 python -m unittest -q test_r32.py >verification/R32_new_40.log 2>&1
printf '0\n' >verification/R32_new_40_exit.code
echo "PASS test_r32 $(date -u +%FT%TZ)" >>verification/R32_geometry_progress.log
