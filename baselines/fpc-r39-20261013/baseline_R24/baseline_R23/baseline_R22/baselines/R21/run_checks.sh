#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python r21_verify.py
python r21_export.py
python -m unittest -q test_r21 2>&1 | tee verification/R21_new_tests.txt
PYTHONPATH="$PWD/baselines/R20" python -m unittest -q test_r20 2>&1 | tee verification/R20_regression.txt
PYTHONPATH="$PWD/baselines/R20/legacy_R19/sources:$PWD/baselines/R20/legacy_R19" python -m unittest -q r19_verify.TestR19 2>&1 | tee verification/R19_regression.txt
PYTHONPATH="$PWD/baselines/R20/legacy_R17/legacy_R16:$PWD/baselines/R20/legacy_R17" python -m unittest -q test_r17 2>&1 | tee verification/R17_regression.txt
python r21_report.py
python - <<'PY'
from pathlib import Path
import json,hashlib
p=Path('.');fs=[]
for f in sorted(p.rglob('*')):
 if not f.is_file() or any(x in f.parts for x in ('__pycache__','pdf_render','preview')):continue
 if f.name in ('R21_SHA256_MANIFEST.json','R21_SHA256_CHECK.txt','pdf_contact.png'):continue
 fs.append(dict(path=f.as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size))
(p/'verification'/'R21_SHA256_MANIFEST.json').write_text(json.dumps({'revision':'R21','count':len(fs),'files':fs,'manufacturing_release':False},ensure_ascii=False,indent=2))
print('MANIFEST',len(fs))
PY
