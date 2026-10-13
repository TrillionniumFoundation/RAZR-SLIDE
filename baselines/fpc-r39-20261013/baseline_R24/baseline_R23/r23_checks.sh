#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification
printf '%s\n' 'R23: independently replay baseline R22 and negative 56-case proof'
(cd baseline_R22/baselines/R21 && python -m unittest -q test_r21.py) > verification/R23_R21_28.log 2>&1
(cd baseline_R22 && python -m unittest -q test_r22.py) > verification/R23_R22_37.log 2>&1
(cd baseline_R22 && python -m unittest -q test_r22_adversarial.py) > verification/R23_R22_adversarial_11.log 2>&1
python -u r23_gate.py > verification/R23_gate_run.log
python -u r23_power.py > verification/R23_power_run.log
python -u r23_oled.py > verification/R23_oled_run.log
if [[ "${1:-quick}" == "--full" ]]; then
   python -u r23_integration.py > verification/R23_integration_run.log
   python -u r23_export.py > verification/R23_export_run.log 2>&1
fi
python -m unittest -q test_r23.py > verification/R23_unittest.log 2>&1
python - <<'PY'
import json,pathlib
v=pathlib.Path('verification')
for name in ['R23_lock_fault_results','R23_B_integration','R23_power_faulttree','R23_OLED_tolerance_gate']:
 d=json.loads((v/(name+'.json')).read_text())
 assert d['manufacturing_go'] is False,name
s=json.loads((v/'R23_lock_fault_results.json').read_text())['independent_fault_enumeration']
assert s['all_R22_open_both_new_open_unseated_escape']==56
print('R23 engineering regression passed. MANUFACTURING RELEASE = NO-GO')
PY
