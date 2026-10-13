#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
python3 r44_prepare.py | tee evidence/R44_parent_prepare.log
python3 r44_rear_bypass.py > evidence/R44_OCC_run.log 2>&1
python3 -u r44_dense_121.py > evidence/R44_dense_run.log 2>&1
python3 r44_feedthrough_probe.py > evidence/R44_feedthrough_run.log 2>&1
python3 r44_clearance_stow.py > evidence/R44_stow_clearance_run.log
python3 r44_budget.py > evidence/R44_budget_run.log
(cd base_R43 && PYTHONPATH="$PWD/parent_R42:$PWD${PYTHONPATH:+:$PYTHONPATH}" python3 -m unittest -v test_r43.py) > evidence/R44_fresh_R43_21_tests.log 2>&1
python3 -m unittest -v test_r44.py > evidence/R44_new_tests.log 2>&1
python3 r44_attest.py | tee evidence/R44_attest_stdout.log
printf 'R44 independent research replay complete. All candidates remain NO-GO.\n'
