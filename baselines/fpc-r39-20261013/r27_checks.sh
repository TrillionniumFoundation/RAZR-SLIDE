#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p cad verification
if [[ "${R27_SKIP_INHERITED:-0}" != '1' ]]; then
 ./r27_inherited_unit_tests.sh
fi
python -u r27_integration.py > verification/R27_integration_run.log 2>&1
python -u r27_faults.py > verification/R27_faults_run.log 2>&1
python -u r27_tolerance.py > verification/R27_tolerance_run.log 2>&1
python -u r27_dynamic.py > verification/R27_dynamic_run.log 2>&1
python -u r27_power_faults.py > verification/R27_power_faults_run.log 2>&1
python -u r27_export.py > verification/R27_export_run.log 2>&1
python -m unittest -q test_r27.py > verification/R27_new_35.log 2>&1
python r27_attest.py > verification/R27_attestation_run.log 2>&1
