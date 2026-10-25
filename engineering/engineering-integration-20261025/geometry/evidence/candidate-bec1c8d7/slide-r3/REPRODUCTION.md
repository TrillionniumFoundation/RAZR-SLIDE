# C2 SLIDE r3 execution and independent readback

Frozen repository HEAD: `bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb`.
Repository path used for this execution: `/workspace/scratch/fea78049c104/RAZR-SLIDE`.
The original 43-package lock check passed before and after execution. All repository source bytes, the original source-path checks, the original full material/pair domain, and all original resource/geometry criteria remained unchanged.

## Original native invocation

The recorded command was:

```sh
/workspace/scratch/fea78049c104/RAZR-SLIDE/.venv/bin/python -B  /workspace/scratch/fea78049c104/RAZR-SLIDE/engineering/engineering-integration-20261025/geometry/slide/supervise_slide_native.py  --expected-head bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb  --output /tmp/razr-slide-r3-bec1c8d7-20261025
```

The separate outer environment receipt records `TMPDIR=/tmp`, one BLAS/OMP thread, and the authorized parallel verification window. The supervisor retains its 1,800-second wall guard, 1,536 MiB worker RSS guard, 6.8 GiB shared unreclaimable-memory guard, 100 MiB runtime ordinary-disk reserve, and unchanged default maximum subdivision depth 2.

The native worker completed all 11,781 pairs in 1,236.487 seconds. Its exit code 2 is the preserved negative diagnostic outcome: 11,762 clear, 10 conservative enclosure overlap, and 9 top-level evaluation-failure pairs. There are 59 recursive error records, not 59 distinct failed pairs. No capacity or wall guard stopped the run. Complete diagnostic and domain-clear flags remain false.

## Known standalone reader entrypoint defect

Direct execution of frozen `slide/check_slide_checkpoint.py --report ...` failed its own source identity check before reading the geometry evidence. The reader imports `slide_evidence` first; the latter prepends the SEATING helper directory. The later `verify_slide_native` import therefore resolves `owned_process` from the SEATING directory. This is a real C2 entrypoint defect. The archive retains the original CLI traceback, execution receipt, and actual-versus-expected module paths. It has not been fixed in C2.

The native supervisor has a valid import order: it imports `verify_slide_native` first, then imports `check_slide_checkpoint` in its final readback block. A fresh, independent process used that exact order to call the unchanged reader. No module was monkeypatched; no path/source/environment/HEAD check was disabled; no physical criterion changed.

The actually executed launcher is retained in the archive under `sidecars/razr-slide-r3-bec1c8d7-20261025-supervisor-order-full-reader-v2.py`:

```python
"""Readback using the frozen supervisor module's import order, in a new process.
The original standalone reader CLI failure remains separately recorded.
No repository source, identity check, or physical criterion is modified.
"""
import sys
from pathlib import Path
here = Path("/workspace/scratch/fea78049c104/RAZR-SLIDE/engineering/engineering-integration-20261025/geometry/slide")
sys.path.insert(0, str(here))
import supervise_slide_native
import check_slide_checkpoint as checkpoint_reader
raise SystemExit(checkpoint_reader.main(sys.argv[1:]))
```

Launcher SHA-256: `c4cc0b68202653755e77c96d80ab3b8cb40e03481abe4c4b90cef465c41ce36c`.

The actual independent command was:

```sh
/workspace/scratch/fea78049c104/RAZR-SLIDE/.venv/bin/python -B  /tmp/razr-slide-r3-bec1c8d7-20261025-supervisor-order-full-reader-v2.py  --report /tmp/razr-slide-r3-bec1c8d7-20261025/report.json  --expected-head bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb  --output /tmp/razr-slide-r3-bec1c8d7-20261025-supervisor-order-full-reader-v2.json
```

It wrote the complete independent receipt and returned exit 2, correctly preserving the incomplete-diagnostic result. It verified the full publication hash chain, all 11,781 unique raw pairs, zero pending pairs, the original geometric arithmetic/postguard, exact source identities, and the 43-package environment. It did not import CAD or recompute native geometry. A prior launcher attempt mistakenly referenced the reader as a supervisor module attribute; its pre-readback `AttributeError` and source bytes are also retained. That failed attempt is not counted as an independent readback.

These are historical execution commands. Repeating them requires an unused output path because the original programs reject overwrites. Source-path identity is deliberately bound to the recorded root and helper files; relocating the checkout is not silently accepted as equivalent evidence.

## Raw evidence and precise limits

`run/report.json` SHA-256: `597c7897f0f3151783042bb752397eeee34f3cd7861b3f26405205d113b36527`.

`run/pairs.jsonl` SHA-256: `6b084a595021c1ccc2662f9eceefc08b98718b8adf03fffaa7e6f3a6664e6362`.

The producer's `completed_pair_count=11776` is a stale 128-pair heartbeat. The unchanged report pair array and independently checked journal both contain all 11,781 pairs. The archive does not edit that raw scalar.

The `method-observations` sidecar preserves the tiny exact interval, its parent interval, corresponding native binary-float displacement, source identities, and the complete affected raw pair tree. The original native catch block retained exception type/message but did not record a runtime traceback. The sidecar explicitly distinguishes its static call chain from a runtime traceback.

Conservative enclosure overlap and method failure do not prove physical penetration. This result does not qualify continuous flexible self-validity, contact loads, strength, tolerances, physical fabrication, or manufacturing release. The separately archived finite KEY half-band baseline contains a different, actual positive-volume collision result; the two evidence types must not be conflated.

`execution.tar.gz` is immutable and includes 37 content members plus its per-member SHA-256 manifest. This reproduction note accompanies it without changing the original archive bytes.
