#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification
# Different baselines imported unchanged; a failure halts with a nonzero exit.
(cd baseline_R23/baseline_R22/baselines/R21 && python -m unittest -q test_r21.py) >verification/R24_R21_baseline.log 2>&1
(cd baseline_R23/baseline_R22 && python -m unittest -q test_r22.py) >verification/R24_R22_baseline.log 2>&1
(cd baseline_R23/baseline_R22 && python -m unittest -q test_r22_adversarial.py) >verification/R24_R22_adversarial.log 2>&1
(cd baseline_R23 && python -m unittest -q test_r23.py) >verification/R24_R23_baseline.log 2>&1
python -u r24_mechanics.py >verification/R24_mechanics.log 2>&1
python -u r24_integration.py >verification/R24_integration.log 2>&1
python -u r24_dynamic.py >verification/R24_dynamic.log 2>&1
python -u r24_faults.py >verification/R24_faults.log 2>&1
python -u r24_longlap.py >verification/R24_longlap.log 2>&1
python -u r24_rail_web.py >verification/R24_rail_web.log 2>&1
python -u r24_export.py >verification/R24_export.log 2>&1
python -m unittest -q test_r24.py >verification/R24_new_25.log 2>&1
python - <<'PY'
import json,pathlib
for p in pathlib.Path('verification').glob('R24_*.json'):
 o=json.loads(p.read_text())
 if 'manufacturing_go' in o:assert o['manufacturing_go'] is False,p
r=json.loads(pathlib.Path('verification/R24_fault_matrix.json').read_text())
assert r['current_R24_nominal_cam_fails_strict_seat_interlock']
print('R24 SOFTWARE/CAD REPRO PASSED; MANUFACTURING GO: FALSE')
PY
