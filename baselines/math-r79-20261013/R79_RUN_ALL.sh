#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/results"
R78="${R78_PARENT_ZIP:-/mnt/data/files/RAZR_SLIDE_R78_verified_incremental_hardgate_20261013.zip}"
R77="${R77_PARENT_ZIP:-/mnt/data/files/RAZR_SLIDE_R77_verified_incremental_hardgate_20261013.zip}"
R76="${R76_PARENT_ZIP:-/mnt/data/files/RAZR_SLIDE_R76_verified_incremental_hardgate_20261013.zip}"
OPENBLAS_NUM_THREADS=1 python "$ROOT/src/r79_accel_robust.py" --out "$OUT" --r78 "$R78" --r77 "$R77" --r76 "$R76"
OPENBLAS_NUM_THREADS=1 python "$ROOT/src/r79_independent_90digit.py" --csv "$OUT/R79_C1_piecewise_quadratic_witness.csv" --out "$OUT/R79_independent_90digit.json"
OPENBLAS_NUM_THREADS=1 python -m unittest discover -s "$ROOT/tests" -p 'test_r79.py' -v
