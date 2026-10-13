#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: > verification/R34_geometry_progress.log
run(){
 local mod="$1"
 echo "START $mod $(date -u +%FT%TZ)" >>verification/R34_geometry_progress.log
 OPENBLAS_NUM_THREADS=1 python -u "$mod.py" >"verification/R34_${mod}_recalc.log" 2>&1
 echo "PASS $mod $(date -u +%FT%TZ)" >>verification/R34_geometry_progress.log
}
run r34_freeze
run r34_integration
run r34_dynamic
run r34_tolerance
run r34_faults
run r34_export
OPENBLAS_NUM_THREADS=1 python -m unittest -q test_r34.py >verification/R34_new_36.log 2>&1
printf '0\n' >verification/R34_new_exit.code
printf '0\n' >verification/R34_geometry_exit.code
run r34_attest
