# Geometry execution, 2026-10-25

This folder makes the prepared SLIDE and SEATING r3 sources executable from the
current repository, and adds a complete finite KEY diagnostic. It does not
declare continuous motion, structural qualification or fabrication release.

## Current execution and candidate boundary

The current verified functional candidate is S4,
`dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`. Its new
[D6 run](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40210734348)
completed all 36 suites and 1,654 actual tests, plus three new complete finite
geometry runs and independent native STEP/material readers. C2's original
36-suite/1,641-test result remains bound to C2. S3's D5 geometry succeeded, while
its full software verification failed because generated documents still stated
1,641 instead of 1,654. S4 synchronized those documents through the original
generator and performed a new same-source validation; no earlier receipt was
relabeled. These software and finite-pair results do not grant hardware release.
[Execution report](../EXECUTION_REPORT.md), [evidence index](../COMPLETED_EVIDENCE_INDEX.json)
and [work plan](../WORK_PLAN.md) are the current result entrypoints.

* Canonical STOW and OPEN completed with 11,781 and 12,880 clear pairs.
* Original v4 completed all six actual native labels in
  [D4](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40204613951).
  STOW HALF_BAND and FULL_BAND each retain four positive actual Common records;
  the other four labels are finite-clear. Across six labels, 20,880 pairs were
  fresh and 53,103 fixed pairs were reused from the matching canonical controls.
  The original strict resume then validated all six saved bundles with zero
  native trial recomputations. All original profile-domain rejections remain.
* D4 separately evaluated the original `candidate=none` STOW orthogonal slot
  vertex: all 11,781 pairs were fresh, with zero positive Common or evaluation
  errors, and its independent native reader passed. This is one finite vertex.
* SLIDE r3 recorded all 11,781 pairs: 11,762 clear, ten enclosure-unresolved
  and nine top-level evaluation failures. These original classifications remain.
  L1 completed all 89 targeted calls and retained their exact original returns;
  a separate source-derived analysis identifies four finite whole-body
  A_BACK_PANEL/KEY intersection states in the nominal rigid pair domain. The
  original C2 standalone-reader import defect and supervisor-order readback
  exit 2 are retained. S3 adds minimal import-order repairs and fresh-process
  regressions; it does not change the original negative native evidence.
* SEATING r3 cleared all 11,781 declared external pairs and its fresh original
  reader passed. KEY/crosshead remained zero; left/right telescoping allocations
  were independent. Continuous flexible-material self-validity is not proved.
* The original C2 single-layer FULL_BAND face-relief candidate still has two actual KEY/ROOT_INNER
  intersections, each about 0.00649356 mm3. Material accounting and same-kernel,
  independent-process STEP readback passed; geometric clearance did not.
* S3's explicit two-layer relief completed FULL_BAND and ORTHOGONAL in
  [D5](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40208304041):
  each retained all 154 bodies and evaluated all 11,781 pairs fresh, with zero
  Common volumes and evaluation errors. Both independent native readers passed.
  A third fresh `candidate=none` FULL_BAND regression reproduced the original
  four positive pairs and their exact D4 volume values. D5 as a whole failed
  the separate software/document-consistency gate; these are S3 results only.
* S4/D6 newly executed all three cases: both v2 points were finite-clear and
  the default `none` FULL_BAND control retained the four true positive Common
  objects. All 35,343 pairs were fresh, all 70,686 journal events matched, and
  all three independent readers passed. D5 results were not reused as S4 data.

The finite worker's original `exact_commit_execution_claimed=false` is retained;
each run's actual complete source/input set is separately bound to its C2, S3 or S4
Git blobs. Earlier incomplete local and hosted attempts remain separate records.
No nominal material property, tolerance, physical stop or production-default
change is inferred from these results.

The [D5 aggregate](evidence/source-20dfddfe/D5-finite/SUMMARY.md),
[D6 aggregate](evidence/source-dd7def6e/D6-finite/SUMMARY.md), and
[L1 aggregate](evidence/candidate-bec1c8d7/slide-L1/SUMMARY.md) are new derived
public engineering documents containing results, public source identities and
original archive hashes. Complete original ZIPs, materials, API/log records and
runtime process/environment provenance are retained privately, without changing
their bytes or publishing those payloads in the aggregate documents.

## Source and scope

`PORTING.json` binds 33 historical files to their original archived SHA256 and
the current ported bytes. Path declarations and source-identity path checks
were relocated; native computation, the original `Budget` definitions, complete
material domains and Common tolerance were preserved. The port has a new source
identity. Historical `results.tar.gz` inputs are read without extraction by
`prepare_portable.py`; their byte identities and all top-level definition
differences are verified again before the pure regression suites run.

The old `seating/run_seating_preparation.py` and `key/run_key_endpoint_trials.py`
are preserved reference sources. They depend on former scratch layouts and are
not the current preparation or complete KEY entry points. Use the commands below.

## Complete finite KEY diagnostic (B)

The current worker builds the actual complete 154-part STOW or 161-part OPEN
scene, crosschecks every body against an accepted in-domain factory placement,
and evaluates every unordered pair: 11,781 or 12,880 pairs. It reuses no earlier
fixed-pair result. Original out-of-range contact-profile rejection remains
explicit, and the trial only translates existing finite material according to
the original v4 helper. The STOW finite floor is inspected by that same helper.

Nominal and trial inventories record each body's complete positive solid count,
signed volume, exact geometric bounds, source functions, actual partition and
relief metadata. Material grades, constitutive properties, friction and joint
properties remain unassigned. Bounding dimensions are not wall-thickness
measurements. A new EP5 structural model cannot inherit a PR34 FE pass.

Run one explicitly selected trial while holding the shared CAD resource window:

```sh
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/key/supervise_key.py --mode trial --trial STOW_OUTSIDE_HALF_BAND --output /tmp/razr-key-half-band
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/key/supervise_key.py --mode readback --report /tmp/razr-key-half-band/trial/report.json --output /tmp/razr-key-half-band-readback
```

Each output directory must be new. The supervisor verifies the 43 locked package
versions, binds the child through the nonce/procfs identity handshake and checks
the actual owned worker's RSS. Trial limits are 1,200 seconds, 1,536 MiB worker
RSS, 6.8 GiB shared unreclaimable memory and 100 MiB runtime ordinary-user disk
reserve. Startup requires 256 MiB disk and 2 GiB additional memory reserve.
The separate STEP reader uses 90 seconds and 768 MiB worker RSS.

Every selected and completed pair is journaled. All positive numeric Common
records survive an export failure; such a failure prevents a completion claim.
The independent reader checks the full pair inventory and journal, reimports
all roots and solids of each positive STEP and compares the complete signed
volume without importing geometry generators. It uses the same CAD kernel.

This execution is explicitly **not the original v4 contract run**. Its source
identity binds every imported project module and every native input before and
after execution while allowing unrelated concurrent work in the checkout.
Canonical validation and original v4 contract execution (A) have their own
source identities, controls, receipts and status in the execution report.
They remain separate from this finite diagnostic (B).

### Original single-layer relief: retained negative evidence

The complete baseline identified four real penetrating pairs: each KEY against
its CAP_0 and ROOT_INNER. `key/stow_face_relief.py` defines finite local cuts from
the actual intersection coordinates. It moves the four relevant fixed faces
back by the original full coupled-groove KEY band, preserving the original
0.02 mm nominal face gap at the negative full-band endpoint. X/Z padding is an
explicit 0.001 mm geometric research choice, not a manufacturing tolerance.

The candidate retains every participant, requires each modified body to remain
one valid positive solid, and records complete removed/added material and signed
volume balance. Each body exports before, after and actual finite cut-envelope
STEP files. The independent native reader reconstructs the cut and checks
bidirectional material differences using all imported roots and solids.

It does not change production defaults, the contact law or the allowed control
domain. Its original FULL_BAND result remains a failed geometry trial, with two
secondary ROOT_INNER intersections. It can be reproduced from C2:

```sh
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/key/supervise_key.py --mode trial --candidate stow_face_relief --trial STOW_OUTSIDE_FULL_BAND --output /tmp/razr-key-relief-full-band
```

The run recomputes all 11,781 pairs. There is no inherited fixed-pair result.
Use the independent reader command for the resulting report.

### Two-layer relief: S3 and new same-source S4 finite executions

`key/stow_two_layer_face_relief.py` adds the second measured Y-face layer while
retaining the original six primary cut boxes: four complete fixed bodies and
14 boxes in total. In both S3/D5 and newly executed S4/D6 trials, every modified before/after body remains
one valid positive solid. The independent reader rebuilt every frozen cut tool;
both directed tool-definition differences and both directed material
reconstruction differences were zero. Added volume was zero, and the largest
absolute material-balance residual was `3.325340003357269e-12 mm3`.

Reproduce the current D6 runs only in the S4 source checkout, with fresh output
directories. Historical D5 reproduction uses its separate S3 checkout:

```sh
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/key/supervise_key.py --mode trial --candidate stow_two_layer_face_relief --trial STOW_OUTSIDE_FULL_BAND --output /tmp/razr-key-v2-full-band
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/key/supervise_key.py --mode trial --candidate stow_two_layer_face_relief --trial STOW_OUTSIDE_ORTHOGONAL --output /tmp/razr-key-v2-orthogonal
```

Run the independent native reader for each report. FULL_BAND uses
`dx=-0.0252814320072192, dq=-0.06063677106654654 mm`; ORTHOGONAL uses
`dx=+0.0252814320072192, dq=-0.010073907052108134 mm`. KEY has no X translation
in this declared rigid endpoint model. Two clear negative-dq points do not
prove every control combination or a continuous domain. Positive-dq real
factory motion changes STOP positions and spring-envelope lengths; it requires
its own source-derived model and cannot inherit a 24-body rigid-study claim.
The `0.02 mm` gap and `0.001 mm` padding remain geometric research values, not
manufacturing tolerances. Strength, retention force, installation force,
fatigue, service locking and all physical release flags remain unqualified.

## L1 targeted observations: completed diagnostics and limited finite witnesses

[L1 run 40210275856](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40210275856)
used functional C2 and a distinct frozen external observer. E17 completed the 17
original rejected evaluation calls; O72 completed the 72 terminal overlap calls.
All 89 actual raw return values equal their frozen r3 originals. Together they
preserve all 19 pair identities, exact rational intervals and all 59 recursive
error rows. The original functions, `1e-7 mm3`
predicate, domain and resource guards are unchanged. The observer retains actual
Common/failed-prism references and exception traces; STEP/BREP export occurs
only after the original function has returned and tracing is detached.

The actual observations retained 505 per-case material records, not 505 globally
unique bodies, and 1,010 successful STEP/BREP exports. Twenty-five distinct
ValueError objects comprise 16 tiny-displacement failures, five nonpositive
temporary prism solids, three impossible Common-volume failures and one
unsupported EXTRUSION surface. The 272 GeneratorExit events come from the
original generator expression closing normally; they are separately retained.
Export byte/hash and original in-memory signatures were independently checked;
independent native STEP reimport was not executed by L1.

Eight A_BACK_PANEL/KEY overlap nodes contain sixteen actual positive Common
observations at `whole_start` or `whole_end`. These regions are complete rigid
bodies, and these two pair laws contain only one shared q, with no independent
height, joint, flank or maximum-spring enlargement. The frozen factory sources
use a fixed complete panel and a closed complete KEY template translated in Y.

| Pair states | Exact q (mm) | Approximate slide (mm) | Observed Common (mm3) |
|---|---|---:|---:|
| A_BACK_PANEL with L_KEY and R_KEY | `1392875388202497/400000000000000` | 23.142044210239405 | about 0.245587849382247 |
| A_BACK_PANEL with L_KEY and R_KEY | `3664291796067499/400000000000000` | 60.880681403413135 | about 0.230137383539251 |

These four side-by-coordinate states are finite whole-body intersection
witnesses within the declared nominal rigid pair model. This is a new derived
interpretation; the original `unresolved_enclosure_overlap` and
`collision_proved=false` fields remain unchanged. Exact rational endpoints,
binary64 translation recipes and factory floating-point conversion are recorded
separately. A newly reconstructed, bit-identical full factory scene at those
coordinates and an independent STEP reimport were not performed. The other 64
KEY/STOP and SPRING/STOP overlap calls retain their enlarged height/spring
correlation limits and are not promoted to physical collision witnesses.

L1 is not another complete 11,781-pair execution and does not clear SLIDE.
Both shards retained the original 1,800-second native limit,
1,536 MiB worker limit, 6.8 GiB shared-memory guard and original disk reserves.
The new hosted 40-minute job/2,220-second external cap only surrounds those
unchanged native limits. A method failure, conservative overlap, export failure
or interrupted prefix remains visible in its own category. All material,
force, tolerance, service-locking and physical release qualifications remain open.

## SLIDE and SEATING r3

Prepare the portable sources without importing CAD:

```sh
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/prepare_portable.py --output /tmp/razr-portable-geometry-prepared
```

The preparation emits pure regression logs and a new SEATING source manifest.
The preserved r3 supervisors require a clean frozen repository and an explicit
full expected HEAD. They retain their original native domains and resource
guards, and never retry automatically. Obtain the final source SHA from the
frozen repository; do not use a historical example SHA.

```sh
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/slide/supervise_slide_native.py --expected-head FULL_FROZEN_SHA --output /tmp/razr-slide-r3
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/seating/supervise_seating_native.py --expected-head FULL_FROZEN_SHA --prepared-manifest /tmp/razr-portable-geometry-prepared/seating-prepared-source-manifest.json --prepared-sha256 PREPARED_MANIFEST_SHA256 --output-directory /tmp/razr-seating-r3
```

SLIDE/SEATING native execution must also hold the shared resource window. A
resource refusal, incomplete journal or unresolved conservative enclosure does
not constitute a clear continuous domain. Read the emitted controller, raw
checkpoint and independent reader together before making a completion claim.
