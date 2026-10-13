#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification cad
if [[ "${R25_SKIP_INHERITED:-0}" != "1" ]]; then
  (cd baseline_R24 && ./r24_checks.sh) >verification/R25_R24_FULL_REGR_RUN.log 2>&1
fi
# Always recompute evidence; no stale baked JSON can quietly turn to PASS.
python -u r25_capture.py >verification/R25_capture_run.log 2>&1
python -u r25_gate.py >verification/R25_gate_run.log 2>&1
python -u r25_faults.py >verification/R25_faults_run.log 2>&1
python -u r25_tolerance.py >verification/R25_tolerance_run.log 2>&1
python -u r25_integration.py >verification/R25_integration_run.log 2>&1
python -u r25_dynamic.py >verification/R25_dynamic_run.log 2>&1
python -u r25_export.py >verification/R25_export_run.log 2>&1
python -m unittest -q test_r25.py >verification/R25_new_30.log 2>&1
python - <<'PY'
import json,pathlib
v=pathlib.Path('verification')
for p in v.glob('R25_*.json'):
 data=json.loads(p.read_text())
 if 'manufacturing_go' in data: assert data['manufacturing_go'] is False,p
assert json.loads((v/'R25_faults.json').read_text())['OPEN_old_early_fault_remains_unsafe']
assert json.loads((v/'R25_tolerance.json').read_text())['groups'][1]['clashes_at_seat']>0
print('R25 OFFLINE REPRO SUCCESS; MECHANICAL/ELECTRICAL/OLED MANUFACTURING: NO-GO')
PY
