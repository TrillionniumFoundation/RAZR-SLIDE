#!/bin/sh
set -eu
test "$1" = "-B"
shift
task_script=$1
shift
task_output=
task_previous=
for task_argument in "$@"; do
    if test "$task_previous" = "--output"; then
        task_output=$task_argument
    fi
    task_previous=$task_argument
done
test -n "$task_output"
exec python3 -I -S -B r4-runtime/run_qualified_script_r4.py \
    --runtime-contract r4-runtime/R4_PROJECTION_CONTRACT_V3.json \
    --qualification r4-runtime/validation-worker-attempt3/R3_PROJECTION_VALIDATION_EXECUTED.json \
    --runtime-receipt "${task_output}.runtime-observation.json" \
    --script "$task_script" -- "$@"
