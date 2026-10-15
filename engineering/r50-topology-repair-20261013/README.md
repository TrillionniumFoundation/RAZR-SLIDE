# R50 pure-solid topology compatibility repair

This is an isolated continuation of `engineering/r50-repair-20261013`, triggered
by the actual strict-motion counterexample. No prior source, receipt, archive,
or protected research core is edited. `manufacturing_go=false`.

The former `validated_solid_volume` checked validity, one deduplicated Solid,
and positive finite volume. OCC can report exactly those properties for a
Compound containing a Solid and an extra Wire. Repeating an existing Solid
Wire can even leave **all** deduplicated vertex/edge/wire/face/shell/solid counts
and signed volume unchanged. The actual R50 AABB shortcut then accepted a far
mixed Compound as an already checked zero intersection.

`REJECTED_pre_topology_guard_tests.log` and its exit-code file preserve four
actual failures against the copied former implementation. These are actual
`solid_intersection` calls with far body/cell loose Wire or repeated existing
Wire, not a fabricated scalar or mock predicate. The valid pure nested wrapper
case passed before the fix and continues to pass after it.

The only geometry helper change walks the original participant at every
Compound layer. Every Compound must have exactly one direct child; the terminal
shape must be a Solid. Existing validity/one-Solid/finite-positive signed volume
checks remain. It does not take `Solids()[0]`, rebuild the object, discard a Wire,
or change the solid-intersection builder. The copied
`src/r50_full_span_finite_ribbon.py` is byte-identical to the existing repaired
builder (SHA-256 `fc258ddd7c9016aaa47a20ff789e55859f277a30f1a5d27a7c01b6a8d9bb7576`).

Before execution, `source_provenance.json` binds all 102 existing isolated-cache
files, inherited sources/tests, strict-motion trigger sources, and new source
hashes. The runner verifies these identities before loading geometry and verifies
the source-cache hashes again afterward. Python bytecode writes are disabled.

The execution runs the original **23** receipt tests, **10** signed-volume guard
tests, the existing **4** AABB participant tests, and **5** new real topology
tests. It then actually rebuilds **108 finite loft cells for each of two poses**:
`INBOARD_R15_ALPHA25_MID_SLACK / STOW` and `DOCK_4p013`. Both full and trimmed
A/B checks still go through the unchanged R50 builder and new participant
guard. Native process exit and complete per-cell signed common records are
saved separately in this directory. Original historic 63-pose receipts are not
represented as newly recomputed geometry.

The retained B-collision comparison is in `preserved_witness_comparison.json`.
The native runner exits 0; all 42 tests pass. Both actual 108-cell calculations
retain the existing collision tallies exactly:

| Actual pose | Old / new free-span B cell tally, mm3 |
| --- | ---: |
| STOW | 19.95814036 / 19.95814036 |
| DOCK q = 4.013 mm | 21.02772977 / 21.02772977 |

These are checked per-cell sums, not union volumes or authorized cut volumes.
This repair changes accepted participant topology; it does not provide a viable
FPC route, OEM channel, physical material/lifetime, mechanical protection,
electrical qualification or OLED qualification. No new STEP is necessary for
this topology counterexample. `manufacturing_go=false`.

Reproduce against the preserved verified source cache:

```sh
python3 -B run_repair.py --source-root /workspace/scratch/522038b915ed/work-cad/r50-checked-replay
```
