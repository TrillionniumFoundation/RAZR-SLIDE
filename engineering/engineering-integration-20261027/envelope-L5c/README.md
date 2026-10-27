# L5c: diagnose the preserved EXTRUSION and STEP failures

This separately named diagnostic reads only the original scientific operands retained by L5b run 40465353232, artifact 12715683051. The source ZIP is 143,535 bytes with SHA-256 39bd7f2f28bb81cf8e8a80357ce4c74e0ceb0d7433190e30c67515558a0310aa. Its flat MANIFEST has 68 members; all 69 regular files, including the manifest, were independently verified before this request. L5b's failure remains unchanged.

## Actual reason for this diagnostic

L5b passed the unchanged seven L2 controls and the four new ordinary/reversed/zero/tiny capsule controls. It exactly reproduced the original unsupported advancing surface EXTRUSION rejection. Its new V2 route produced twelve positive, valid regions, but the finite containment loop recorded only t=0 with outside volume zero. A ValueError arose before the t=0.25 record could be appended. The original exception text was not retained.

The separate reader verified 26 geometry hashes and successfully read 25 BREP files, then failed before the first STEP count increased. The 26th item was the original-shape STEP. No physical pair was completed; the current-K1 job was skipped by the original dependency.

## New bounded native observations

The driver imports the actual original whole BREP, original EXTRUSION face BREP, twelve saved V2 region BREPs, and the original whole/face STEP files. It does not reconstruct a substitute specimen or regenerate the V2 regions. A failure to validate a retained region remains a failure.

STEP importStep, vals, exact one-root checks, and the original p.single or face-valid check have separate checkpoints. STEP work is independent of the later BREP subtraction investigation, so one failed STEP does not prevent the other retained input from being examined.

The unchanged translation_regions.regions call is replayed once to record the expected original EXTRUSION rejection. The unchanged subtract_regions and p.volume are then called at t=0 and t=0.25. Each actual translate and returned remainder is retained. A separate t=0.25 diagnostic replay splits the exact original loop into whole_material(empty=True), cut, clean, and final whole_material gates. It retains cut and clean shapes separately. This traced replay is explicitly distinct from both the original L5b operation and the new direct unchanged-function calls.

Raw shape type, validity, null state, solid count and signed mass accessors are observations. They do not substitute for the original signed whole-material predicate. The original validator alone defines an allowed empty result. No absolute value, negative clamping, repair, tolerance change or dropped tiny material is introduced.

Failures record the controlled operation name, exception class, message SHA/byte count and source-relative traceback file/function/line with source SHA. Raw exception text, machine paths, environments, process inventories and native logs are excluded from scientific export.

## Completion and scope

diagnostic_observations_completed records whether the bounded diagnostic reached its end. all_selected_original_operation_guards_passed is a different field: any failed selected original gate keeps it false and makes the worker return 2. The supervisor uses that scoped field and the worker exit code. It does not use, assert or replace the original L5 all-pairs qualification flag.

The driver always reports zero original-seven/current-seven pair calls and false full-domain, K3 and physical qualification flags. The original L5b producer, method, readers, tests, source binding and nineteen source files are unchanged. L5c is not an attempted seven-pair pass with the EXTRUSION control bypassed.

## Resource and publication contract

The capacity preregistration cites the actual L5b producer's 5.608743999 seconds and 521,879,552-byte peak RSS, and the actual reader's 3.461119890 seconds and 503,541,760-byte peak RSS. These observations are not bounds on unseen operations.

The unchanged resource contract remains 1800 seconds per worker, 1536 MiB peak RSS, 6.8 GiB shared unreclaimable memory, 200 MiB startup and 100 MiB runtime ordinary disk reserves, 1536 MiB startup memory allowance, 2220-second host deadline, and a 40-minute job. Ownership handshake, process-group termination and source/environment closure checks remain intact. The new diagnostic additionally bounds saved shapes to 96 files and 64 MiB, JSON to 4 MiB, and retained roots to eight per STEP input. The original one-root predicate is checked separately before that retention cap.

The new workflow is below 500,000 bytes and triggers only diagnostic/s4-l5c-extrusion-20261027, plus explicit workflow_dispatch. It is an independent workflow under .github/workflows/s4-l5c-extrusion.yml. Its parent is actual L5b commit 690b1ed0df100fe175f5d6752b716105c0521a25, base tree 40ed335630e030487d213104fb49a2c3af3b575b. Functional checkout remains immutable S4.

The old L5b source/host setup is retained verbatim. Five new diagnostic files are embedded with exact SHA/size gates and written exclusively to the two external source directories. The input action expands the fixed L5b artifact; every one of its 68 member hashes plus the exact manifest and member set is verified. The hosted input check does not falsely claim it hashed the compressed ZIP itself.

Actual local validation executed only the new inline source installer, exact input-member gate and failure-safe exporter controls. Ten source copies matched; a one-byte changed original BREP was rejected; negative signed failure data survived export; an unknown filename kept the export red while preserving accepted science; a private locator was rejected. Seven shell blocks and seven inline Python blocks parsed. No network or native CAD executed in these checks.
