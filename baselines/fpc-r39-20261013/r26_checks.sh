#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification cad
if [[ "${R26_SKIP_INHERITED:-0}" != "1" ]]; then
  ./r25_checks.sh > verification/R26_inherited_153_run.log 2>&1
fi
python -u r26_faults.py >verification/R26_faults_run.log 2>&1
python -u r26_tolerance.py >verification/R26_tolerance_run.log 2>&1
python -u r26_integration.py >verification/R26_integration_run.log 2>&1
python -u r26_dynamic.py >verification/R26_dynamic_run.log 2>&1
python -u r26_export.py >verification/R26_export_run.log 2>&1
python -m unittest -q test_r26.py >verification/R26_new_38.log 2>&1
python - <<'PY'
import pathlib,json,hashlib
v=pathlib.Path('verification')
for name in ('R26_integration','R26_dynamic','R26_tolerance','R26_faults','R26_STEP_manifest'):
 d=json.loads((v/f'{name}.json').read_text())
 assert d['manufacturing_go'] is False,name
assert json.loads((v/'R26_dynamic.json').read_text())['unexpected_count']==0
f=json.loads((v/'R26_faults.json').read_text());assert f['undocked_R26_second_gate_absent_or_broken_escape_rows']>0
r=json.loads((v/'R26_STEP_manifest.json').read_text())
assert r['exported_scenes']==10
for item in r['scenes']:
 p=pathlib.Path('cad')/item['STEP'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
print('R26 OFFLINE GEOMETRY/FAULTS VERIFIED: RESEARCH ONLY, MANUFACTURING NO-GO')
PY
