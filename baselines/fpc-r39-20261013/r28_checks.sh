#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p cad verification
# This complete workflow is slow because OCP performs many exact full-solid
# booleans. All actions are serialized so no competing OCC builds hide errors.
./r28_inherited_tests.sh
python -u r28_integration.py  >verification/R28_integration_run.log 2>&1
python -u r28_dynamic.py      >verification/R28_dynamic_run.log 2>&1
python -u r28_faults.py       >verification/R28_faults_run.log 2>&1
python -u r28_tolerance.py    >verification/R28_tolerance_run.log 2>&1
python -u r28_presence.py     >verification/R28_presence_run.log 2>&1
python -u r28_clearance.py    >verification/R28_clearance_run.log 2>&1
python -u r28_export.py       >verification/R28_export_run.log 2>&1
python -m unittest -q test_r28.py >verification/R28_new_42.log 2>&1
python r28_attest.py          >verification/R28_attestation_run.log 2>&1
