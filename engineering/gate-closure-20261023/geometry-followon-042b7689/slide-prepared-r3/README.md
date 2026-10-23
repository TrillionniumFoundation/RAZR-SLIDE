# SLIDE r3: prepared diagnostic, no r3 native execution

This successor preserves the original SLIDE mathematics, full 154-material /
11,781-pair scope, native numerical tolerances and resource limits. It adds
durable pair evidence and a verified owned-child memory sampler. The final
65 small contracts passed in the exact frozen source/runtime identity. Their
geometry rows are synthetic. They do not establish native clearance or G2.

The 65 tests consist of the original 27 arithmetic/raw contracts, 11 journal
contracts, 17 shared process controls and 10 SLIDE supervisor lifecycle controls.
The shared 17 also appear in the separate SEATING r3 preparation; do not add
them as different tests. None changes the repository's existing 1,558-test result.
The first combined preparation's actual MemoryError and all preliminary
receipts remain under `historical/`. Only the external preparation harness's
math-thread environment was corrected; its 512 MiB address-space cap stayed.

`prepared-r3-final/executed-source-manifest.json` binds the 17 execution sources
and the additional preparation harness. `SOURCE_LAYOUT.json` maps their copied
bytes to the original workspace layout. Four original math/reader/test files
are byte-identical. The copied native-contract test changes only its explicit
source-count assertion from 11 to 17. The original geometry/budget helper
definitions retain their ASTs; worker changes bind sources, persist evidence
and perform the early ready/release handshake. Original v2 sources and their
prepared copies have not changed.

The parent verifies a fresh nonce, worker source hash, original Popen PID,
procfs-visible PID, parent PID, NSpid chain, starttime and namespaces before
releasing the worker. Each later positive RSS/HWM observation is bracketed by
identity checks. Missing live-child memory is an error. Signals still target
the original Popen process group. Initial writes, pipe failures and monitor
exceptions all stop/reap that child and close owned descriptors. The separately
archived real stdlib smoke exercised this exact helper once; it was not CAD.

`pairs.jsonl` durably records pair selection before evaluation and completed
raw evidence after return. A start does not prove entry into a kernel call.
An intact prefix reports persisted progress only and never qualifies resume
or completion. Final qualification additionally needs the full report, final
commit, atomic index, stable byte hashes and the unchanged independent raw
geometry/source/runtime reader. Positive conservative enclosures remain
unresolved; a persisted record is not automatically a clear pair.

## Reproduction

Use a clean checkout of functional commit
`042b768903cccbd7a0995317c8598401e0318e2a` as `RAZR-SLIDE` beneath a workspace
containing the source layout. Restore every mapped source from the copied bytes
and verify its SHA-256 before use. The original source/runtime checks still
require the exact locked 43-package environment. Keep outputs outside the repo.

To run only the small preparation contracts in a fresh output directory:

```bash
RAZR-SLIDE/.venv/bin/python -B ci_audit/run_slide_r3_preparation.py --output /tmp/razr-slide-r3-new-preparation
```

When resources permit a separately recorded native attempt, the reviewed entry
point is the supervisor. The worker's native mode requires its private handshake:

```bash
RAZR-SLIDE/.venv/bin/python -B g2_slide_r3/supervise_slide_native.py --output /tmp/razr-slide-r3-new-native --expected-head 042b768903cccbd7a0995317c8598401e0318e2a --maximum-subdivision-depth 2
```

The original 1,800-second wall, 1,536 MiB worker RSS, 6.8 GiB shared memory,
200 MiB startup disk and 100 MiB runtime disk limits remain. Do not infer a
completed native run from this preparation bundle or from a startup refusal.
After interruption, use `check_slide_checkpoint.py --prefix ... --expected-head
... --output ...`; after normal publication use its `--report` mode. Both require
the same source layout and exact functional checkout. Never edit old receipts.

`REFERENCES.json` binds the separately preserved v2 preparation/start refusal,
the actual v2 attempt2 resource stop, both original procfs probes, and the real
final-helper smoke. The v2 native attempt completed five construction probes
but retained zero completed pair records before its shared-memory stop. That
actual result remains v2; r3 has not undergone preflight or native execution.
All canonical/full-G2/physical and fabrication/go flags remain false.
