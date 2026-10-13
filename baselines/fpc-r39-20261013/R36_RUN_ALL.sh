#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Exact R35 ZIP provenance is externally verified only when the original archive exists.
if [ -r /mnt/data/files/RAZR_SLIDE_R35_verified_engineering_package_20261011.zip ]; then
  OPENBLAS_NUM_THREADS=1 python r36_freeze.py
else
  OPENBLAS_NUM_THREADS=1 python r36_verify_ancestors_offline.py
fi
for task in r36_integration r36_catalogue_fit r36_dynamic r36_tolerance r36_faults r36_export; do
  echo "RECALCULATE $task"
  OPENBLAS_NUM_THREADS=1 python "${task}.py" >"verification/R36_${task}_full_recalc.log" 2>&1
done
bash r36_inherited.sh
OPENBLAS_NUM_THREADS=1 python -m unittest -q test_r36.py > verification/R36_new_54.log 2>&1
printf '0\n' > verification/R36_new_exit.code
OPENBLAS_NUM_THREADS=1 python r36_attest.py
