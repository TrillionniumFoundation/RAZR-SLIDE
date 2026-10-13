#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p verification
: >verification/R27_inherited_unit_tests_exit.log
(
 cd baseline_R24/baseline_R23/baseline_R22/baselines/R21
 python -m unittest -q test_r21.py
) >verification/R27_inherited_R21.log 2>&1
(
 cd baseline_R24/baseline_R23/baseline_R22
 python -m unittest -q test_r22.py
) >verification/R27_inherited_R22.log 2>&1
(
 cd baseline_R24/baseline_R23/baseline_R22
 python -m unittest -q test_r22_adversarial.py
) >verification/R27_inherited_R22_adversarial.log 2>&1
(
 cd baseline_R24/baseline_R23
 python -m unittest -q test_r23.py
) >verification/R27_inherited_R23.log 2>&1
(
 cd baseline_R24
 python -m unittest -q test_r24.py
) >verification/R27_inherited_R24.log 2>&1
python -m unittest -q test_r25.py >verification/R27_inherited_R25.log 2>&1
python -m unittest -q test_r26.py >verification/R27_inherited_R26.log 2>&1
echo R27_INHERITED_UNIT_TESTS_FINISHED >>verification/R27_inherited_unit_tests_exit.log
echo RC=0 >>verification/R27_inherited_unit_tests_exit.log
