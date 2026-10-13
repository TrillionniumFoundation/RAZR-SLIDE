#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-quick}"
if [[ "$MODE" != "quick" && "$MODE" != "--full" ]]; then
 echo "usage: $0 [quick|--full]" >&2; exit 2
fi
mkdir -p verification cad viewer
(
 cd baselines/R21
 python -m unittest -q test_r21.py
)
if [[ "$MODE" == "--full" ]]; then
  echo 'R22 FULL: expensive fresh OCC B shell and 5 poses (may take multiple minutes).'
  python -u r22_verify.py > verification/R22_full_verify.log
  python -u r22_export.py > verification/R22_export.log
else
  echo 'R22 QUICK: using previously completed OCC whole-body results; not re-running heavy CAD.'
  python - <<'PY'
from pathlib import Path
for f in ('verification/R22_mechanical_results.json','verification/R22_STEP_manifest.json'):
 assert Path(f).exists(),f
PY
  python - <<'PY'
from r22_verify import fault_report
from r22_electrical import report as electrical
from r22_oled import report as oled
fault_report();electrical();oled()
print('fresh local fault, power Boolean and OLED sensitivity models recomputed')
PY
fi
if [[ "$MODE" == "--full" ]]; then python r22_viewer.py >/dev/null; fi
python -m unittest -q test_r22.py > verification/R22_unittest.log 2>&1
tail -4 verification/R22_unittest.log
python - <<'PY'
import json,pathlib
p=pathlib.Path('verification')
for n in ('mechanical','fault','electrical','oled'):
 d=json.loads((p/f'R22_{n}_results.json').read_text())
 assert not d.get('manufacturing_go',d.get('manufacture_go',False)),n
m=json.loads((p/'R22_mechanical_results.json').read_text())
assert m['B_one_solid'] and not m['extra_safety_moving_parts_vs_OLED_FPC_A_and_B_collision_count']
f=json.loads((p/'R22_fault_results.json').read_text())
assert f['ideal_fault_scan']['scenarios']==320 and f['ideal_fault_scan']['false_unlock_blocking_failures']==0
assert f['explicit_negative_cases']['all_three_stops_false_open_unmitigated']
e=json.loads((p/'R22_electrical_results.json').read_text())
assert e['logic']['logic_states_checked']==8192 and e['logic']['logic_false_energization_failures']==0
assert e['logic']['mutation_bad_controller_rejected']
print('R22 CAD recorded evidence, reference logic + test gates PASS; manufacturer NO-GO')
PY
python r22_attest.py
