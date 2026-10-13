# RAZR SLIDE — independent safety audit, 2026-10-13

`manufacturing_go=false`. This review adds reproducible fault witnesses and a
bounded control/force study. It does not implement or qualify a mechanical latch,
power circuit, FPC assembly, or OLED.

The product constraints remain two compartments with the same external size,
one approximately 7-inch flexible OLED, B sliding upward 79.75 mm followed by
8.2 mm normal seating, and priority for a larger A battery. R79 is a separate
mathematical branch and supplies no measured FPC tension, physical actuator
profile, or force qualification to this review.

## What was independently checked

`audit_baseline.py` independently reconstructs the original expressions, then
runs the R37 geometry fault code and R38 architecture code with `write=False`.
Bytecode writing is disabled. Hashes of all 1,157 baseline files before and after
the audit match. The baseline is not rewritten.

| Evidence | Fresh result | Meaning |
|---|---:|---|
| Legacy mechanical fault table | 64 states; 36 escape states | The original escape counterexamples remain |
| Mechanical minimal cut sets | 4 pairs | Failure of both side barriers can defeat retention |
| Legacy power fault table | 512 states; 487 live-pad states | Abstract source paths remain energized in these modeled combinations |
| Power minimal cut sets | 7; 3 singletons | Three direct PCB shorts bypass the commanded isolation |
| R37 local-stop OCC fault model | 16 rows match baseline | A broken integral lip reopens the old local cap extraction path |
| R38 architecture table | 32 rows match baseline | Existing negative architecture placeholder is reproducible |
| R37/R38 unit rerun | 84 tests pass | Negative and nominal model checks; no safety closure |
| New safety study tests | 13 tests pass | Adversarial software checks for the explicitly limited study |

The initial unit invocation failed at import because `shapely` was not yet
available. `baseline-unit-tests.log` preserves that failure. The subsequent full
run is saved as `baseline-unit-tests-retry.log`; its real process exit was 0.

These exhaustive Boolean counts are neither fault probabilities nor physical
reliability percentages. The six-axis mechanical table includes two false-pawl
axes which do not affect its escape predicate. Consequently, 36/64 must not be
described as a measured escape rate. The four minimal escape cut sets are:

- L ear broken + R ear broken.
- L ear broken + R gate forced open.
- L gate forced open + R ear broken.
- L gate forced open + R gate forced open.

The three electrical single-point cuts are `A_direct_pad_short`,
`B_direct_pad_short`, and `shared_live_bus_to_pad_short`. The other four cuts each
combine a source isolator weld with that source's main or precharge switch weld.
No new circuit/layout or physical bypass test closes any of them.

## A concrete limitation in the inherited architecture model

In `r38_faults.py`, `electrical_hazard_unmitigated` depends only on
`pcb_single_point_bypass`, `electric_isolation_effective`, and
`flex_insulation_intact`. `flex_loom_continuous` and `mechanical_captured` are
enumerated but do not affect any electrical hazard result. An open FPC can remove
sensing or actuator power, and loss of capture can tension/tear a loom. Neither
consequence is modeled by that field. This is acceptable for its stated
conservative placeholder role; it cannot be used as the FMEA for a new fixed
connector and moving harness.

The new `safety_model.py` therefore records path-specific open/short/abrasion,
anchor-slip, common-cause release, and stale-zero-measurement witnesses. These
witnesses are unresolved requirements, not fixes or hardware simulations.

## Independent signal, USB, and power paths

| Path | Candidate architecture | What still prevents qualification |
|---|---|---|
| Signal | BM28 remains statically mated; its signal FPC receives local strain relief at both ends | Vendor mating geometry, exact pinout, both PCBs, clamp geometry, pull/peel load, moving strain and fatigue |
| USB | Separate controlled-impedance moving path and static terminations | Frozen USB speed/topology/pinout; stackup, shielding and return paths; TDR/S-parameters/eye/BER/ESD/EMI across worst poses |
| Power | Local protected cell/BMS in each compartment; separately protected controlled exchange path if needed | Real cells/loads, schematic/layout, reverse-current blocking, precharge, fuse/current limit, residual energy and PCB-bypass tests |

Direct parallel connection of unlike battery states is excluded from this
candidate study. BM28 mating is not repeated by the slide motion. A flex loom
cannot be a structural restraint. Separate file/net names do not establish
independence: shared ground, shielding, chassis contacts, shared actuator,
abrasion surfaces, and a shared PCB can create common-cause or backfeed paths.
The FMEA explicitly preserves power-to-signal and power-to-USB short witnesses.

The current report does not select actual USB or power connectors, allocate
pins, select cells, choose a converter, or authorize OEM protected-core cutting.
These must follow the true three-dimensional routing clearance work.

## Mechanical release and finite-force retraction

The required sequence is: stop motion while both captures remain engaged;
isolate every source and independently measure voltage and bounded residual
energy; verify retraction under a calibrated force limit; only then permit an
intentional latch release. A jam must retain the captures and leave power
isolated. No available program physically enforces this sequence yet.

`ReleaseEvidence` defaults every input to false. Its 256 Boolean combinations
allow a *model* sequencing decision in one complete-evidence state; all 256
retain `manufacturing_go=false`. Sending an isolation command cannot substitute
for voltage/energy measurements. False zero-voltage readings, coupled inhibit
paths, actuator breakage, and loss of supply require physical fault tests even
when the software guard would accept entered booleans.

For an accepted operating envelope, the force study requires:

`worst retraction resistance <= guaranteed available retraction force <= maximum limited force < minimum damage/capture threshold`.

Resistance must include contact mechanism, friction/contamination, FPC/OLED
restoring forces, springs, and inertia over the actual travel. The guarantee of
available force and the maximum applied force are separate bounds: a force cap
alone cannot guarantee retraction. Every default bound is `null`, so the present
study denies force feasibility. The few numbers in unit tests are explicitly
synthetic fixture cases and are not product limits.

| Remaining mechanical requirement | Required evidence |
|---|---|
| Positive capture at STOW and OPEN on both sides | Actual A keys and B latches, assembly/docking path, GD&T, physical force-displacement records |
| No false seating or unintended release | Absent-key, partial-seat, single and dual release, debris and side-load tests |
| Passive fail-closed behavior | Real spring/stop/load path, spring failure, pin/lip/fastener fracture, loss of supply, common-cause analysis |
| Finite-force retraction | Measured worst resistance and weakest-part threshold, calibrated force limiter, jam and low-supply tests |
| No electrical release while energized | Synchronized voltage/current/position/force waveform with PCB shorts and welded switch injection |
| Connector and harness cannot become load path | Anchor/strain-relief CAD and measured terminal/FPC force/strain in worst motion and vibration |

Missing material/force/OLED data are physical hard blockers. Geometry collisions
and Boolean safety assertions cannot supply those data.

## Reproduce without changing the baseline

From this directory, with the project's CadQuery/OCC dependencies installed:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python audit_baseline.py
PYTHONDONTWRITEBYTECODE=1 python safety_model.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_safety_model
```

The first script writes a full hash inventory and the independently enumerated
fault rows in this directory. The study output is
`architecture-and-release-study.json`. Tests do not promote a product gate.
