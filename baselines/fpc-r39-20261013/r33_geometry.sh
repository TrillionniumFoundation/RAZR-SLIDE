#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: >verification/R33_geometry_progress.log
run() {
 local mod="$1"
 echo "START $mod $(date -u +%FT%TZ)" >>verification/R33_geometry_progress.log
 OPENBLAS_NUM_THREADS=1 python -u "$mod.py" >"verification/R33_${mod}_recalc.log" 2>&1
 echo "PASS $mod $(date -u +%FT%TZ)" >>verification/R33_geometry_progress.log
}
run r33_freeze
run r33_integration
run r33_retention
run r33_dynamic
run r33_catalogue
run r33_expansion
run r33_export
OPENBLAS_NUM_THREADS=1 python -m unittest -q test_r33.py >verification/R33_new_40.log 2>&1
printf '0\n' >verification/R33_new_40_exit.code
printf '0\n' >verification/R33_geometry_exit.code
echo "PASS test_r33 $(date -u +%FT%TZ)" >>verification/R33_geometry_progress.log
