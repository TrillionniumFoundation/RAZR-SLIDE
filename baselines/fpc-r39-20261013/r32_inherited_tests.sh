#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification
: > verification/R32_inherited_progress.log
run() {
 local label="$1" directory="$2" script="$3"
 echo "START $label $(date -u +%FT%TZ)" >>verification/R32_inherited_progress.log
 ( cd "$directory" && OPENBLAS_NUM_THREADS=1 python -m unittest -q "$script" ) >"verification/R32_inherited_${label}.log" 2>&1
 echo "PASS $label $(date -u +%FT%TZ)" >>verification/R32_inherited_progress.log
}
run R21 baseline_R24/baseline_R23/baseline_R22/baselines/R21 test_r21.py
run R22 baseline_R24/baseline_R23/baseline_R22 test_r22.py
run R22_adversarial baseline_R24/baseline_R23/baseline_R22 test_r22_adversarial.py
run R23 baseline_R24/baseline_R23 test_r23.py
run R24 baseline_R24 test_r24.py
run R25 . test_r25.py
run R26 . test_r26.py
run R27 . test_r27.py
run R28 . test_r28.py
run R29 . test_r29.py
run R30 . test_r30.py
run R31 . test_r31.py
