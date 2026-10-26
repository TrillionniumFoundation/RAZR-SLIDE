# Reproducible SEATING preparation and checkpoint delivery

The active entry point is the **v2-r2** supervisor. This archive contains code
and small evidence only. It does not contain a native SEATING result, a solved
FE payload, or a completed G2 qualification. The embedded member manifest
records the actual sole v2 resource-preflight disposition; the external
archive index records a full member-by-member SHA256 readback.

## Source layout

These scratch adapters intentionally bind their actual execution paths and
the clean repository commit. Restore each archive subtree to the indicated
layout to reproduce the same source identity:

| Archive subtree | Original execution location |
|---|---|
| `v1/` | `/workspace/scratch/95cd2986fdf2/input_recovery/g2_seating/` |
| `v2/` | `/workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v2/` |
| `independent-reviews/` | Independent review evidence; original paths are in the member manifest |
| `preflight/controller.json` | Original non-starting preflight receipt; path and SHA are in the member manifest |

The repository must separately be materialized at
`/workspace/scratch/95cd2986fdf2/RAZR-SLIDE` with clean HEAD
`042b768903cccbd7a0995317c8598401e0318e2a`, its exact native inputs and the
existing 43-package locked environment. This small archive does not duplicate
that Git repository or its geometry inputs. Reproduction at another path or
with altered source must use a new explicit source identity; recorded hashes
must not be relabeled.

`v1/prepared-v1/` retains the original six execution sources and 15-test
preparation. `v2/prepared-v2/` retains the first ten-source 22-test preparation
and its later-discovered metadata-reader limitation. The current
`v2/prepared-v2-r2/` retains all ten current execution sources and the 25-test
preparation that closes that specific reader limitation. All historical
manifests and raw test results are preserved. The source layout for actually
running r2 is `v2/`, not the preserved source-copy directories.

## Exact bounded continuation command

After allocation of the shared heavy-computation slot, the original gates
must all pass again at the time of the attempt. The concrete native command
below has **not** been executed by this delivery and uses a new output path:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -B \
/workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v2/supervise_seating_native.py \
--expected-head 042b768903cccbd7a0995317c8598401e0318e2a \
--prepared-manifest /workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v2/prepared-v2-r2/executed-source-manifest.json \
--prepared-sha256 1024dc5aa4e8cc2011b4201ea73f84abe78f6695ed27e5b70e517d6e56af867c \
--output-directory /tmp/razr-seating-v2-042b7689-native-1
```

The unchanged limits are 400 MiB ordinary available disk before starting,
300 MiB during execution, 1,536 MiB startup incremental memory and worker RSS,
6.8 GiB shared unreclaimable memory, a 1,740-second worker budget inside the
independent 1,800-second process-group deadline, 20,000 pair calls and depth
three. `--preflight-only` checks these gates without starting the worker; each
invocation requires a fresh output directory. A previous successful check
does not waive any later gate.

The current worker appends each completed raw pair to a source/domain/run-
bound JSONL journal. An interrupted prefix remains incomplete. Final external
pair qualification additionally requires the complete raw report, its final
journal commit, the atomic index and independent source/input/lock/geometric
postguard. This is a fresh bounded native attempt, not an unimplemented
partial-geometry resume. The preserved v1 command is historical and is not
the active checkpoint-capable entry point.
