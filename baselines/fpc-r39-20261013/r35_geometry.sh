#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
: > verification/R35_geometry_progress.log
run(){
 local mod="$1"
 echo "START $mod $(date -u +%FT%TZ)" >>verification/R35_geometry_progress.log
 OPENBLAS_NUM_THREADS=1 python3 -u "$mod.py" >"verification/R35_${mod}_recalc.log" 2>&1
 echo "PASS $mod $(date -u +%FT%TZ)" >>verification/R35_geometry_progress.log
}
run r35_freeze
run r35_integration
run r35_dynamic
run r35_tolerance
run r35_faults
printf '0\n' >verification/R35_faults_exit.code
run r35_export
printf '0\n' >verification/R35_export_exit.code
OPENBLAS_NUM_THREADS=1 python3 -m unittest -q test_r35.py >verification/R35_new_50.log 2>&1
printf '0\n' >verification/R35_new_exit.code
run r35_attest
printf '0\n' >verification/R35_geometry_exit.code
