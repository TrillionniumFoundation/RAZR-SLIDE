#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
python r38_verify_offline.py
python r38_integration.py
python r38_faults.py
python r38_export.py
python -m unittest -q test_r38.py
# Fresh inherited tests take substantially longer:
if [[ ${1:-} == --all ]]; then python r38_inherited.py; fi
printf 'R38 geometric research repeated; connector/FPC still not electrically connected. NO-GO.\n'
