# Geometry execution, 2026-10-25

This folder makes the prepared SLIDE and SEATING r3 sources executable from the
current repository, and adds a complete finite KEY diagnostic. It does not
declare continuous motion, structural qualification or fabrication release.

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
Exact-commit canonical validation, a new fixed-control run and original v4
contract execution (A) remain separate gates after the source is frozen.

### Local face-relief research candidate

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
domain. Run the full-band endpoint and the opposite cam-flank vertex separately:

```sh
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/key/supervise_key.py --mode trial --candidate stow_face_relief --trial STOW_OUTSIDE_FULL_BAND --output /tmp/razr-key-relief-full-band
.venv/bin/python -B engineering/engineering-integration-20261025/geometry/key/supervise_key.py --mode trial --candidate stow_face_relief --trial STOW_OUTSIDE_ORTHOGONAL --output /tmp/razr-key-relief-orthogonal
```

Both runs recompute all 11,781 pairs. There is no inherited fixed-pair result.
Use the independent reader command for each resulting report. These finite
points do not prove the continuous backlash domain, local strength or tolerance
robustness, even when every native pair is clear.

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
