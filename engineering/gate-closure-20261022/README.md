# Gate closure execution — 2026-10-22

This branch continues from PR36 commit `e25cf001c1b714514d501de4c16d1592fde06b61`. It preserves the rejected EP4 candidate and the original PR35 contact experiment. No hardware or manufacturing gate is granted.

## Implemented software corrections

- `tools/verify_product_native.py` runs the seven EP4 native regression groups, all three finite scenes and a separate STEP reader. The required CI job uses the exact PR head. Execution success and geometric rejection are separate results.
- The driver compares every selected working source's Git blob identity with the real HEAD tree, disables Git replace objects, and records source SHA256 before and after execution. Both assume-unchanged and skip-worktree concealment have regression coverage.
- The physical follow-on qualification contract binds design roles, specimen, plan, acquisition, calibration and originals. Known failures survive missing observations. Finite arithmetic, uncertainty intervals, preregistration review and end-of-evaluation revalidation prevent false qualification. Manual reviewer attestations are explicitly not machine authentication of reviewer identity.

The new native driver has 15 passing targeted tests. The final qualification change has 51 new tests plus nine existing acquisition tests, all passing; a separate 23-case review checked the repaired edge cases. The integrated working source also passed all 80 targeted tests (15 native-driver, 51 qualification, 9 acquisition, 5 state), with unchanged checked source bytes; see [raw report](targeted-p0-p2/report.json). The [initial failed run](targeted-initial-enospc/report.json) is retained: its temporary directory was on the full shared disk, and the separate material-motion suite could not import Shapely. These development runs are not a complete validation of this branch.

## Actual baseline attempt

[Complete raw report](baseline-e25/report.json) and all per-suite JSON/logs preserve the actual e25 attempt: 35 suites selected, 24 passed, 11 failed, 1114 tests run, no syntax errors in 1052 Python files, and unchanged source bytes. Missing original native archive payloads blocked dependent suites. An additional frozen manifest and two BREP inputs found by that attempt have been restored afterward.

The installed runtime differed from `uv.lock`: Python 3.12.14, CadQuery 2.7.0, OCP 7.8.1.1.post1, NumPy 2.3.5 and SciPy 1.17.0; Shapely was not installed. Offline locked setup failed because a required wheel was absent. This is explicitly an unlocked diagnostic execution, not a claimed locked pass.

## Gate ledger and next work

| Gate | Current disposition | Required next evidence |
| --- | --- | --- |
| G0 — reliable research baseline | Blocked | Complete current unit and native execution on the exact branch source in the locked environment; successful required CI jobs; status and evidence reconciliation. |
| G1 — real inputs frozen | Blocked | Same-donor board/module labels and dimensions, OLED/COF limits, FPC supplier stack and dynamic rating, complete battery packs/tabs/swelling, twelve terminal bindings and actual process limits. Current donor identity XT2551-3 alone is insufficient. |
| G2 — geometry and motion | Blocked | Finish EP5 complete assemblies and independent readback, continuous forward/reverse collision checks, assembly access and measured tolerance budget. Local finite clearances do not establish these conditions. |
| G3 — unpowered assembly | Blocked | Build the identified specimen and collect complete assembly, retention, opening/closing and relock records against a preregistered plan. |
| G4 — functional prototype | Blocked | Same-specimen power, charging, USB, display, touch and function during motion with calibrated raw records. |
| G5 — manufacturing release | Blocked | Requalify the changed solids, real material/preload/contact model, durability, process capability, inspection and traceability against defined criteria. |

Work order: restore executable input/runtime access (G0); freeze the actual part and process interfaces (G1); resolve the candidate's geometry and tolerance results (G2); execute the unpowered plan (G3); execute the powered plan (G4); qualify structure, endurance and process control (G5). Software and original-input recovery can continue in parallel with physical collection. No dimensions, thresholds or supplier qualification are invented to mark a gate complete.

The available repository workflow uses `ubuntu-24.04`. The requested project-specific cloud instance was not identified by a usable current connection during this session. A single old-job rerun request did not return; a later read still showed run `39389220804`, attempt 1, completed failure, with no new attempt. The request was not repeated. Prior direct provider billing annotations are retained as historical evidence, not a claim to have read current account billing settings.

All six gates remain open. The new code closes specific validation defects; it does not supply absent real specimens or measurements.
