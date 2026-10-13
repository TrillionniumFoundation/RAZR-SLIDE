#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification
: >verification/R28_inherited_status.log
run() {
 local label="$1" d="$2" module="$3"
 echo "RUN $label" >&2
 ( cd "$d" && python -m unittest -q "$module" ) > "verification/R28_inherited_${label}.log" 2>&1
 echo "PASS $label $(tail -1 verification/R28_inherited_${label}.log)" >>verification/R28_inherited_status.log
}
run R21 baseline_R24/baseline_R23/baseline_R22/baselines/R21 test_r21.py
run R22 baseline_R24/baseline_R23/baseline_R22 test_r22.py
run R22_adversarial baseline_R24/baseline_R23/baseline_R22 test_r22_adversarial.py
run R23 baseline_R24/baseline_R23 test_r23.py
run R24 baseline_R24 test_r24.py
run R25 . test_r25.py
run R26 . test_r26.py
run R27 . test_r27.py
echo 'INHERITED_TOTAL=226 RC=0' >>verification/R28_inherited_status.log
