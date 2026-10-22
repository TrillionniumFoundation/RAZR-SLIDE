# PR35 rigid-bearing continuation checkpoint

This change prevents a future rigid-bearing run from losing its complete response cache at a process timeout. It does not establish a converged original bearing solution, change the contact model, or qualify hardware. The original retained `bearing-field-016.npz` is explicitly rejected as a restart checkpoint.

## Source and numerical scope

`source-lock.json` binds the three byte-identical reference files to PR35 head `176df31ceb35bb3737d68030e60ba377665de210`: the outer FE/trace driver, the rigid-bearing driver, and the eight-bearing equilibrium maps. `ADAPTER_DIFF.patch` exposes the complete change to the rigid driver. The wrapper dispatches the unchanged outer driver's existing rigid-bearing hook to the new adapter.

The eight free head/nut normal/tilt planes, axial-only bolts, original fixed frame, zero external load, simultaneous force installation, gap target, QP tolerance, rank fallback, contact selection, full residual/energy/force/moment/complementarity checks and final release flags retain their original formulas. No FE/QP optimization or load-case widening is included. Runtime dependency files and Python/NumPy/SciPy/scikit-fem versions are recorded and must agree on restoration. A runtime dependency hash is a current-run binding; it does not claim that every file in a later repository is historically identical to PR35.

## Atomic complete state

Each `ready_for_qp` generation includes sparse `C.npz`, dense `H.npz`, ordered `points.json`, `state.json` (next iteration, previous exchange history, warm force vector), `identity.json`, and a manifest binding every member's size/SHA256, sources, parameters, and dimensions. Files are written exclusively into a private temporary directory, flushed, then the generation is renamed and the `LATEST.json` pointer atomically replaced. Previously published generations are never overwritten. An interrupted publication leaves the old pointer valid; an unpublished orphan generation may be retained after an I/O failure.

The adapter publishes before each QP, after the previous exchange has appended its new columns. A timeout during QP can replay that exchange from a complete boundary. A timeout during a new column append can replay from the previous published boundary. The current QP's internal factorization/active-set steps are not serialized. A completed generation is recoverable state, not a whole-contact PASS.

Restoration requires the manifest SHA256 held independently by the caller, such as the emitted `BEARING_CHECKPOINT` receipt retained outside the bundle. The operator must retain that receipt in a trusted job log; reading a digest from an untrusted bundle and treating it as independently trusted provides no provenance. No signing service or new authentication infrastructure is required.

The loader rejects missing or altered members, symlinked members, duplicate JSON/NPZ keys, object/pickle arrays, non-finite values, inconsistent CSC arrays, dimensions, changed source/parameter/operator identity, incomplete or impossible iteration state, and a field-only NPZ. The adapter regenerates every C column from the current frozen descriptors, checks their order and requires every appended point to lie in its frozen bearing face polygon or body-contact cell polygon, then runs the original five complete-operator probes with the original tolerance. The planar membership check uses the original quadratic audit feasibility tolerance, `cross >= -1e-12 * max(edge_scale^2, 1e-300)`, including boundary points; the basis triangle does not replace a clipped domain. Non-finite coordinates or polygon arithmetic are rejected. Undefined arithmetic in a probe is rejected. The probe check supplements provenance; it does not independently prove every H entry. Restart identity conservatively retains original absolute input/source paths as well as content hashes; relocation and runtime changes are rejected rather than automatically re-bound.

The reader hashes the exact byte buffers it subsequently decodes. Native cache artifacts must still be kept immutable while a job is running. Checkpoints can be large, so allocate storage for successive generations; this package does not silently delete old evidence. The original late exchange had 6,010 columns, which alone implies 288,960,800 bytes for one float64 H before compression; this is not a measured runtime-memory forecast.

## Commands

Source-only preflight is safe without native caches or scikit-fem. It does not validate FE inputs or execute a QP:

```sh
python engineering/bearing-continuation-20261022/run_continuation.py --source-preflight
```

For an actual run, provide the same controlled original inputs and arguments through `run_continuation.py`: `--volume`, `--state`, `--surface-loads`, `--installation-control`, `--frozen-selection`, `--case`, `--gap-tolerance`, `--faces-per-patch`, `--load-face-cap`, `--rank-fallback`, `--max-points`, `--max-exchanges`, plus explicit `--surface-load-mode consistent --external-load-scale 0`, a new `--output` directory and `--checkpoint-root`. Original CLI defaults are retained, but no undocumented historical exchange/point limit should be inferred from those defaults. Retain the frozen invocation alongside its receipt.

To resume, repeat the exact controlled input/parameter set and add `--resume-checkpoint /path/to/checkpoint-generation --checkpoint-sha256 <trusted-64-hex-digest>` with a new output directory. The wrapper still prepares the original full FE/trace/load context and verifies its legacy response seed; it then restores the bearing C/H cache instead of recomputing all prior bearing columns. Restoring the bearing cache does not eliminate that original preparation cost. There is no automatic conversion from historical fields or gap logs.

`REBUILD_INPUTS.json` lists precise repository and owner-retained inputs, known hashes, large-file transport limitations, and the distinction between an original-body response seed and a bearing restart. The original 86-file retained manifest contains no complete bearing C/H checkpoint. The historical PR36 read-only inventory found zero bearing restart candidates; that historical inventory was inspected, not re-executed on the owner's host in this session. Missing volume/legacy-response input artifacts must be recovered or faithfully rebuilt before a genuine PR35 run is possible.

## Bounded validation

Run the small tests from a checkout containing this package:

```sh
PYTHONPATH=integration:engineering/bearing-continuation-20261022 python -m unittest -v continuation_test_cases
```

`integration/manufacturing-tests/test_bearing_continuation.py` imports the same cases into the existing manufacturing suite. These 31 tests include a small actual QP continued uninterrupted versus stopped and restored with exactly equal forces/fields/H/points/history; an end-to-end eight-bearing zero-load synthetic adapter run and restart; failed atomic pointer publication; missing/truncated/symlinked/tampered artifacts; changed controls/identity; sparse corruption; descriptor/order mismatch; impossible exchange state; and finite input whose verification arithmetic overflows. Ten domain regression cases additionally exercise the actual original bearing and body-contact map functions: matching C from an extrapolated point is rejected; points inside a basis triangle but outside its clipped domain are rejected; vertices, edges, original roundoff allowance, and both polygon orientations are accepted; non-finite coordinates and overflowing polygon arithmetic are rejected. All fixtures are explicitly synthetic and temporary.

`verification.json` records the local result and source preflight. No original full FE or large QP, original bearing cache restoration, actual hardware measurement, independent whole-surface certification, or release approval was performed by these tests. The original driver keeps `candidate_go`, `fixture_fabrication_go`, `manufacturing_go`, and `hardware_or_actual_preload_qualified` false even if its numerical solve later converges. Independent review of this package is recorded separately by the reviewer and must not be inferred from author tests.
