# SEATING r3: owned-process monitoring successor

This is an independently prepared scratch successor for repository HEAD
`042b768903cccbd7a0995317c8598401e0318e2a`. It has **not executed native CAD** and
does not close the continuous SEATING domain or the full G2 gate.

## What changed

The previous controller sampled `/proc/<Popen.pid>/status`. In this environment
the process namespace PID and procfs-visible PID differ. The old fallback could
therefore return an empty memory observation. The r3 controller instead uses the
same `owned_process.py` bytes as SLIDE r3. Its worker reports its own identities
through a dedicated nonce-bound pipe and waits for a second pipe's release.
Before release, the parent verifies source identity, its Popen handle, parent
identity, namespace PID chain, procfs PID, start time, and both namespace links.
Every later RSS/HWM sample is bracketed by the same identity checks. An unreadable
or changed identity while the child is alive stops and reaps that owned child;
it cannot become a zero-RSS observation.
Keep the old r2 entry point as historical evidence; use the independently
prepared r3 entry point for any future attempt that relies on monitored worker
RSS.

The controller checks its original disk, shared-memory, wall-time, and worker-RSS
limits before releasing native work. Startup, handshake, first-receipt, runtime
telemetry, and interrupt failures keep the result incomplete and close the owned
pipe descriptors. Signals continue to use the original Popen process-group PID;
the procfs-visible PID is used only for the verified reads.

The original `run_native`, `Budget`, geometry, material enclosures, and raw-result
qualification functions are unchanged. Seven source files, including the finite
material cages, shared-descent domain, complete inventory, checkpoint reader,
journal, and original regressions, are byte-identical to r2. The original r2 ten
sources and their frozen execution copies were rechecked before and after the
new preparation and remain unchanged. The original r2 refusals remain historical
receipts; they are not r3 executions.

## Actual preparation evidence

- **50/50 pure tests passed:** the original 25 arithmetic/checkpoint tests, the
  shared helper's 17 identity/transport negatives, and 8 SEATING lifecycle tests.
- Elapsed time: **6.093588929 seconds**; peak RSS: **48,812 KiB**.
- All 13 executed sources, repository arithmetic identity, and all 43 locked
  packages matched before and after. No CAD was imported or executed.
- The 7,364 finite-cell and 48 taper checks are regressions. They are not a
  substitute for continuous native qualification.
- The shared helper is
  `db92c8ceb3c39cd5843d96d042f0202915937abdc2a919d5854e71de4a4c0b25`.
  A separate, genuinely executed stdlib-only child smoke for these exact helper
  bytes passed; its result SHA is
  `a5b492e2e19149da985218294bee8b04082ebde41ac3ac0f91c2808269e3f577`.
  That smoke did not import CAD, execute FE, or prove resource availability for
  the native model.

The source manifest is `prepared-v3/executed-source-manifest.json`, SHA-256
`1c0c613e8f44b7488c5f7a02fa6cb4d570d5ae3721bfd24e5568b0d1a17a5d44`.
The pure test report is `prepared-v3/arithmetic-tests-report.json`, SHA-256
`8046f55160fb87af78d838737caa5890ad2f6246909554397bc344810a393f1b`.
The independent source/integration review passed for this preparation scope;
its SHA-256 is
`cc9fc8f698292fc6d0f00500e2f48d4fa6734daea2f27674401d0d573d282847`.

## Preserved native bounds and scope

| Control | Value |
| --- | ---: |
| Complete native inventory | 154 materials / 11,781 unordered pairs |
| Shared SEATING descent | `d ∈ [0, 8.2] mm`, `s = 79.75 mm` |
| Released tabs | 3 mm on each side |
| Independent slot flanks | `[-1, 1]` on each side |
| Telescope constraints | Every `ji ∈ [0.1, 2.9] mm`; each side sums to `8.5 − d` |
| KEY / crosshead offsets | Both fixed to zero |
| Ordinary startup disk reserve | 400 MiB |
| Ordinary runtime disk reserve | 300 MiB |
| Startup incremental memory reserve | 1,536 MiB |
| Worker RSS/HWM limit | 1,536 MiB |
| Shared estimated unreclaimable memory limit | 6.8 GiB |
| Worker between-operator time budget | 1,740 s |
| Outer process-group time budget | 1,800 s |
| Maximum pair calls | 20,000 |
| Maximum subdivision depth | 3 by default, original controller choices 0–3 |

The complete original OLED and EP5 FPC finite material cages remain part of the
contract. A conservative overlap remains unresolved. Prefix journals are useful
partial evidence only; neither a prefix nor this monitoring repair is a resume
certificate or a qualification result. Complete native evidence, the final
checkpoint publication, the independent raw reader, and unchanged source and
locked environment are still required. Flexible-family self-validity and
physical/manufacturing qualifications are not inferred from pair checks.

## Reproduce and continue

The execution identities intentionally bind the absolute scratch source layout.
Restore the sources under
`/workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v3`, with the repository
at `/workspace/scratch/95cd2986fdf2/RAZR-SLIDE`. Keep the original `g2_seating` and
`g2_seating_v2` source/manifests beside this directory for preservation checks.
This archived code is not intended to silently execute from a different path.

The following source-bound preparation command is the one actually executed;
its output directory already exists and must be retained. A new preparation
attempt needs a different, fresh output directory.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -B \
/workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v3/run_seating_preparation.py \
--output-directory /workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v3/prepared-v3 \
--expected-head 042b768903cccbd7a0995317c8598401e0318e2a
```

The next read-only capacity decision can use this exact command. **It has not
been executed for r3.** `--preflight-only` never starts the worker.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -B \
/workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v3/supervise_seating_native.py \
--output-directory /tmp/razr-seating-r3-042b7689-preflight-1 \
--expected-head 042b768903cccbd7a0995317c8598401e0318e2a \
--prepared-manifest /workspace/scratch/95cd2986fdf2/input_recovery/g2_seating_v3/prepared-v3/executed-source-manifest.json \
--prepared-sha256 1c0c613e8f44b7488c5f7a02fa6cb4d570d5ae3721bfd24e5568b0d1a17a5d44 \
--preflight-only
```

A later explicitly scheduled native attempt uses the same controller and
manifest, a fresh `/tmp/razr-seating-r3-042b7689-native-1` output directory, and
omits `--preflight-only`. It must satisfy the unchanged startup/runtime guards;
there is no automatic retry or budget relaxation. Invoke native work through the
controller, since a direct native worker now requires its dedicated parent
identity handshake and release.
