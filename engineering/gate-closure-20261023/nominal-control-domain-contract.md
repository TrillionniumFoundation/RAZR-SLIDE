# Nominal EP5 control-domain evidence contract

## Scope and acceptance

`integration/product_nominal_motion.py` checks the complete current EP5 finite-material inventory over a declared continuous manual-control domain. It includes the actual split mechanical assembly, EP5 shell and KEY relief, all 41 finite routing participants, four component allocations, and the geometric OLED trial. No mechanical body or cable endpoint is removed to obtain a clear result.

| Fixed product pose | Continuous parameter domain | Complete bodies | Unordered material pairs |
|---|---|---:|---:|
| STOW: slide 0, descent 0 mm | independent left/right tabs in [0,3] mm; independent slot flanks in [-1,1]; every independent left/right telescope allocation with each joint in [0.1,2.9] mm and each side summing to 8.5 mm | 154 | 11,781 |
| PREDOCK: slide 79.75, descent 0 mm | both tabs fixed at released 3 mm; independent slot flanks in [-1,1]; the same complete independent telescope allocation domain as STOW | 154 | 11,781 |
| OPEN: slide 79.75, descent 8.2 mm | both tabs fixed at released 3 mm; independent slot flanks in [-1,1]; each telescope joint fixed at the unique feasible 0.1 mm allocation; all seven OPEN accessories installed | 161 | 12,880 |

PREDOCK and OPEN do not authorize moving the tabs through their full stroke. The existing `product_motion.transition` contract permits tab operation at STOW only. These studies keep KEY and crosshead offsets at zero. They do not establish complete product motion, physical qualification, or any fabrication/manufacturing release.

## Continuous enclosure construction

For each side, TAB, THUMB_PAD and PAD_SCREW_M06_NOMINAL translate along Y by the tab coordinate. PAWL and SHOULDER_PIN_NOMINAL translate along Z by `native_slot.slope * tab + native_slot.halfwidth * flank`. The complete factory supplies all ten control-dependent material bodies.

The split TELESCOPE_1 and its removable BOTTOM_CAP translate along Z by the first joint deviation `delta_j1`. TELESCOPE_2 and its BOTTOM_CAP translate by `delta_j1 + delta_j2`. TELESCOPE_3 and its three removable pieces remain fixed because the sum of all three joints is fixed at each product pose. All eight moving telescope bodies and caps are required by name. Every other current participant is fixed in this declared domain.

For each side, feasible joints form the convex polytope `0.1 <= ji <= 2.9` and `j1 + j2 + j3 = 8.5 - descent`. Its vertices are obtained by putting two joints on bounds and solving for the third; exact rational arithmetic on the declared decimal dimensions constructs the full vertex inventory. STOW/PREDOCK have the three permutations of `(2.7,2.9,2.9)`; OPEN has the single point `(0.1,0.1,0.1)`. This arithmetic does not turn later floating-point native geometry into a formally rounded certificate.

All telescope motion is along the same Z axis. For each material pair, the code evaluates its linear relative-Z law at every vertex on each side, takes the minimum and maximum, and adds the two independent intervals. A linear projection of a connected convex polytope is the entire interval between these extrema. The resulting one-dimensional telescope interval is independent of the four control parameters, so it preserves the complete relative-motion image. It does not impose an equal-allocation assumption or loosen the joint-sum constraint into a larger independent joint box.

For bodies A and B with affine displacements a(u) and b(u), the intersection at any admissible control vector is translation-equivalent to `(A + a(u) - b(u)) ∩ B`. The code forms this relative displacement directly. A positive lower bound on an axis gap excludes intersection. Otherwise it builds a conservative enclosure of the complete relative translation using the existing native `translation_regions.regions` construction. Successive segment enclosures contain the Minkowski sum of all parameter segments; they cover the continuous parameter box rather than a finite collection of poses.

For an unresolved first enclosure, the code may independently enclose the equivalent motion of B by `b(u)-a(u)` against fixed A. A clear result from either complete enclosure is sufficient. Positive enclosure overlap alone remains unresolved. Control corner/midpoint and feasible telescope-vertex probes can establish a collision only after reproducing the same positive native Common in a freshly constructed complete actual scene. An inadmissible joint combination is never relabelled as an actual collision witness. Clear probes cannot close an unresolved domain.

The code also rebuilds the complete actual factory at independent controls and unequal left/right telescope allocations, then compares every participant with the stated affine translation by bidirectional material differences. This check detects omitted moving material, including removable caps; the continuous law comes from the explicit construction and polytope projection, not interpolation through that probe. A focused native regression additionally checks every one of the 108 mechanical split participants at a 4.1 mm seating depth with widely unequal feasible joints.

The numerical tolerance remains `1e-7 mm³`. This is an OCCT-based numerical continuous-enclosure study. It is not a certificate with formally directed numerical rounding, an independent CAD-kernel result, or an independent STEP material-equivalence proof.

## Multi-region tolerance correction

The intersection of a union of enclosure regions with an obstacle has volume at most the sum of the nonnegative individual region Common volumes. Comparing only the largest individual Common to the tolerance can incorrectly clear a larger accumulated overlap.

A retained native counterexample uses a unit cube translated continuously by `(2,2,0)` and an obstacle spanning `[1.495,1.505]` in X and Y and `[0.4,0.4018]` in Z. Two advancing face regions each intersect the obstacle by approximately `9e-8 mm³`, below the original tolerance, while the actual middle pose intersects it by approximately `1.8e-7 mm³`, above that same tolerance. The former maximum/per-region rule falsely cleared this case.

`translation_regions.sum_common_upper_bound` now computes the conservative sum, rejecting empty, negative or nonfinite inputs. The new control-domain verifier and the existing `translation_regions.checks`, `verify_serviceable_pawl.motion`, product allocation sweep, mounted back-panel insertion, and cover-capture path acceptance use that sum with the unchanged tolerance. Complete roof material partitions also retain the summed bound when recombining their component checks. The thin-mechanism STOP contact gate combines the full pin and all remainder cages for the same STOP/KEY pair. The box-guide gate combines all covering material pieces separately for each side and fixed target, with a closed piece inventory. Different fixed targets and separate sequential route stages are not indiscriminately added together.

The exact material-partition regression divides the same unit cube into a diagonal center strip and two remaining positive solids. The complete swept material still reaches the `1.8e-7 mm³` actual overlap while each retained raw region intersection remains below `1e-7 mm³`. The combined parent gate must retain the rejection even if its children expose individually sub-threshold raw rows. Maximum region Common remains a diagnostic where useful. A positive conservative sum is not relabelled as a demonstrated actual collision. Historical evidence bytes and their original execution signatures are retained unchanged.

The enclosure cache also binds the actual native source object and its topology/location identity; a repeated caller label cannot reuse a different material body's enclosure. A native ring-then-solid counterexample is retained as a regression.

## Explicit mechanism inputs

`product_assembly.native_scene` and `product_scene` now accept independent continuous slot flanks, independent left/right telescope allocations, and explicit left/right KEY and crosshead clearance offsets. The split scene and full EP5 scene preserve these inputs in the actual material geometry and metadata.

Each telescope joint remains in `[0.1,2.9] mm`, and each side independently sums to `8.5 - descent_mm`. KEY and crosshead offsets must satisfy both existing cam and yoke groove constraints. The native contact profile is defined only on its declared finite KEY travel; an offset beyond that travel is rejected, including the unresolved negative KEY branch at STOW and positive branch at full slide. The implementation does not clamp those branches or invent an end-stop constraint.

These interfaces and focused native tests permit further legitimate domain work. The fixed-pose continuous-domain calculation includes every feasible independent telescope allocation while keeping KEY/crosshead offsets at zero. It does not establish every combined KEY-clearance and telescope-allocation domain.

## Execution identity and failure handling

Canonical execution requires the actual Git HEAD blob identities, the existing complete EP5 native input closure, every executed repository source, and all locked runtime package versions. The CLI reuses `tools/verify_product_ep5_native.py` and `tools/check_environment.py`; it checks source bytes and HEAD again after execution. It derives pair completeness from actual names and unordered pairs, not a reported count alone. `--expected-head` can bind the requested full 40-character commit explicitly.

Scratch source overlays require `--diagnostic-overlay`. Their raw bounded geometric conclusions may be recorded, but their `execution_checks_passed` is always false. `diagnostic_execution_checks_passed` distinguishes a completed diagnostic from canonical committed-source evidence.

Both reference-frame diagnostics are retained. A first-frame kernel exception is not erased when the reverse frame proves geometric clearance. All evaluation errors are counted from the raw nested records and prevent execution success. Ordinary conservative enclosure overlap is recorded separately from evaluation failure. The modified standalone motion readers also bind their own executed source and the actual `translation_regions` helper before computation and recheck both after all report geometry has been evaluated.

Example canonical invocation, after committing the reviewed sources:

```sh
.venv/bin/python -B integration/product_nominal_motion.py --pose STOW --expected-head FULL_40_CHARACTER_COMMIT --output /outside-repository/stow-controls.json
```

Repeat for PREDOCK and OPEN with new output paths. The CLI rejects an existing output or one inside the repository.

## Remaining G2 work

These fixed-pose control and telescope domains leave the continuous slide/seating action, nonzero independent KEY/crosshead clearance, accessory installation/removal, and their coupled full-material domains unresolved. In particular, telescope variation during the continuous slide/seating action is not covered by checking the three fixed product poses. OLED and routing geometry change shape during those actions, so this fixed-pose affine construction cannot be applied unchanged. End-of-travel KEY backlash branches also need an explicit modeled geometric constraint or a broader valid profile before their domain can be assessed. Material, strength, friction, retention, operating force, selected component identity, and measured hardware remain separate requirements.

## Retained earlier diagnostic scope

The v3 scratch diagnostics evaluated STOW, PREDOCK and OPEN over their continuous independent control ranges using only the nominal equal telescope allocation: 36,442 complete unordered pairs, no unresolved pairs and no evaluation failures. They are source-bound scratch diagnostics, not committed-source canonical evidence, and do not certify the expanded telescope domain above.

A separate six-scene diagnostic exercised actual nonzero independent KEY/crosshead offsets and unequal telescope allocations at two slide midpoints, two seating midpoints, STOW and OPEN. Its 71,785 complete unordered pairs included 4,594 native Common evaluations, with no positive overlap or evaluation error. These are six finite configurations only; their clear results do not close the continuous KEY/telescope/action domain. The reports retain exact input/source identities, raw pairs, and explicit false full-motion and physical-go fields.
