# WP7: bearing seed coverage and tensile-only spring semantics

This work provides a reproducible initial-point improvement for the existing
rigid-bearing investigation and extracts the useful slack-spring law from PR25
onto the main force-QP backend. It does not qualify a new full elastic/contact
solution, physical installation, material, load capacity, or manufacturing.

## Source and input identity

The main baseline is `a1b3cc1e0773446f2e36d0a607edf61211dd9919`.
The retained rigid-bearing investigation is PR35 head
`176df31ceb35bb3737d68030e60ba377665de210`; the old spring-law reference is
PR25 head `44a5830f49af73605d5161efff80e6744b0fb468`.
Source hashes in every new report identify what actually executed.

| Input | SHA256 |
| --- | --- |
| `engineering/consistent-load-20261017/projection-512/panel-faces.json` | `28a649178d20522b4dd418224cd6f498a8bba03cd209e1a85b86a3485985e2da` |
| `engineering/consistent-load-20261017/projection-512/frame-faces.json` | `6f1391cab252100011dc867821919dd56c78e531b6505fa3762bbf0f794c47b8` |
| Retained `rigid-install-v3/bearing-domains.json` | `9e6f489b7adc9f4ae4579f6f9e822a85fc38a2296d44fc64f0dd60401d3b0d14` |
| Retained `rigid-install-v3/bearing-gaps-016.json` | `2523fe073e84eb452756df474a181cc6c99c66b60ec75942c923220f9389fd6f` |
| PR25 `integration/spatial_contact.py` | `c1bdefebf5ab98e1c0173c050459deca4ad49d59ae90f78f5f3b41608b25e195` |

The projection files already exist in the main repository. The original probe
manifest is preserved without editing as
`original-rigid-install-v3-manifest.json`. The remote raw evidence directory is
`/home/qian-qi/.local/share/razr-slide-evidence/bearing-contact-20261018/rigid-install-v3`.
This manifest also preserves the original 3600-second timeout/exit 124; a new
point-coverage result does not replace that failed solve.

## Bearing-point improvement

[PR35's driver](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/176df31ceb35bb3737d68030e60ba377665de210/engineering/trace-enrichment-20261017/rigid_bearing_probe.py)
seeds each of the eight bearing regions from twelve support directions. These
points lie on the perimeter of the combined bearing region. The full declared
projection consists of 404 panel and 792 frame faces, 1196 in total. A sparse
perimeter set does not constrain all the interior degrees of freedom.

`integration/bearing_seed_diagnostic.py` reconstructs the ordered domains and
replays the original support-direction arithmetic. It retains every point of
that replay and adds at most 128 points, with round-robin allocation among the
eight bearings. The geometry-only candidate chooses the face centroid furthest
from that bearing's existing points. The retained-witness candidate first
chooses the most negative saved witness on each bearing and then uses the same
spatial distribution rule, with severity and face identity as tie breakers.
Candidates are not a substitute for the subsequent complete gap audit.

All accepted polygons must be convex: every vertex is checked against every
oriented edge half-plane. Optional retained witnesses require the gap and
domain files to match the same original manifest by byte size and SHA256.
Every original projection field, including vertices, triangle coordinates and
DOF indices, must match the corresponding retained domain row. Body, bearing,
patch, normal direction and origin are checked as well. Matching only 1196
array entries is insufficient. Every selected saved witness must lie inside
its bound face, and the saved negative-cell indices must agree with the frozen
`1e-7 mm` target.

### Executed diagnostic on the actual rejected witnesses

`main-witness-coverage/report.json` was executed in the original locked main
environment, Python 3.12.3 / NumPy 2.5.4, against the complete original gap and
domain files. Both file hashes matched their shared retained-run manifest and
all 1196 domain ordinals passed the complete projection-field identity check.
All 1112 saved negative witnesses were inspected. The frozen numerical gap
target remains `1e-7 mm`.

| Metric | Replayed perimeter seeds | Plus 128 distributed centroids | Plus 128 distributed negative witnesses |
| --- | ---: | ---: | ---: |
| Points | 77 | 205 | 205 |
| Faces containing a point, including boundary | 80 / 1196 | 208 / 1196 | 338 / 1196 |
| Faces containing a strictly interior point | 0 / 1196 | 128 / 1196 | 23 / 1196 |
| Saved negative face witnesses at a seed coordinate | 0 / 1112 | 0 / 1112 | 195 / 1112 |
| Maximum saved-witness distance to nearest same-bearing seed | 0.9978334911 mm | 0.4386015656 mm | 0.4105935663 mm |

Several adjacent faces can have the same negative minimum coordinate. Thus 128
new points can represent 195 indexed face witnesses; this is not 195 new
independent constraints. The centroid alternative covers more face interiors,
while the witness alternative targets the old field's actual negative points.
The coverage metrics alone cannot establish which gives the better re-solved
contact field.

These lists are initial-seed candidates. They do not replace exchange 16's
existing 1491 bearing points or 4515 body points. A true restart from that
iteration must retain all its existing constraints and form a bounded union
with additional candidates. It must not replace that larger set by 205 points.
No gap, force, displacement or material field was re-solved in this diagnostic,
and no independent recovery of the rejected FE field is claimed.

### Additional local geometry replay

`geometric-coverage-local/report.json` uses the exact projection hashes above.
It is a point-coverage calculation, with no new FE solve.

| Metric | Replayed perimeter seeds | Plus 128 distributed face centroids |
| --- | ---: | ---: |
| Points | 79 | 207 |
| Faces containing at least one point, including boundary | 83 / 1196 | 211 / 1196 |
| Faces containing a strictly interior point | 0 / 1196 | 128 / 1196 |
| Maximum face-centroid distance to the nearest same-bearing point | 0.9683737563 mm | 0.4306256987 mm |

The historical initialization recorded 77 points. The original locked runtime
also replays 77, while the local Python 3.12.14 / NumPy 2.3.5 runtime gives 79.
Extreme-vertex comparisons contain near ties and can depend on floating-point
evaluation. The archived initial point coordinates were not restored or
asserted identical; matching a point count alone would not establish that.
Both reports record their actual runtime and set
`historical_seed_positions_verified: false`. The two point counts must not be
silently interchanged. This runtime discrepancy does not alter the 1196 input
faces or the requirement to audit their whole area.

The coverage distance above is an in-plane sampling distance. It is not an
opening or penetration of the solid and must not be compared with manufacturing
clearance. PR35's saved negative gaps are displacements from its rejected
numerical field; the approximately 113.7-fold numerical gap-target exceedance
is not a physical material or hardware failure factor.

Reproduce geometry from a complete repository checkout, choosing a new output
directory:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python integration/bearing_seed_diagnostic.py \
  --panel-faces engineering/consistent-load-20261017/projection-512/panel-faces.json \
  --frame-faces engineering/consistent-load-20261017/projection-512/frame-faces.json \
  --extra-points 128 --output /tmp/razr-bearing-coverage-new
```

To use the actual rejected field, additionally supply `--gaps` and
`--bearing-domains` pointing to the two original files named above, and
`--retained-manifest engineering/product-integration-20261018/numerics/original-rigid-install-v3-manifest.json`.
The resulting report explicitly distinguishes whether the actual witness file
was available and hash verified. Geometry-only reports make no assertion that
the 1112 saved negative witnesses were replayed. The retained gap arrays are
used as input; this diagnostic does not independently recover the FE field.

## PR25 semantic extraction

`integration/slack_spring_contact.py` is a separate, optional entry point. It
uses the existing
[`contact_dual_active.solve_force_qp`](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/a1b3cc1e0773446f2e36d0a607edf61211dd9919/integration/contact_dual_active.py)
with `free_prefix=0`. There is no copied second optimizer and no replacement of
the current `spatial_contact` API.

For leading spring forces and subsequent normal contact forces, the supplied
body response is complementary compliance `H`. With spring compliance `c`,
initial constitutive force parameter `P0`, unloaded relative response `q0`,
rigid map `G` and contact gap `g`, the adapter forms:

```text
S = H + diag(c for springs, 0 for contacts)
d = q0 + [c * P0, -g]
minimize 0.5 * force.T * S * force - d.T * force
subject to G.T * force = load and every force >= 0
q = q0 - H * force + G * rigid_coordinates
```

Spring slack is `c * (force - P0) - q`; contact slack is `g - q`.
Both must be nonnegative and complementary to their force. The adapter checks
that the original body compliance itself is reciprocal and nonnegative in
energy before adding the springs, so a negative body energy mode cannot be
hidden by positive spring compliance. All original equilibrium rows and full
KKT checks remain the backend's responsibility, and their failure is retained.

The simple counterexample `H=2`, `c=3`, `P0=0.4`, `q0=-2` produces force `0`
and spring slack `0.8`. Treating that spring as an unrestricted force instead
would yield `-0.16`; callers of that unrestricted formulation previously had
to reject it as outside their positive-force branch. For `q0=0.5`, both models
give the expected positive force `0.34`. These are dimensionally consistent
algebraic fixtures, not measured installation values.

`adapter-reference-comparison.json` records eight small examples against the
SHA-pinned PR25 source, including three coupled spring/contact equilibria.
All eight share admissible discrete solutions. Duplicate contact rows can
have nonunique individual multipliers, so that example compares their total
reaction. One deliberate scope difference is recorded: PR25 can solve a
perfectly rigid zero-response contact row, whereas the main backend requires
a positive response diagonal and the thin adapter rejects it. No artificial
stiffness, discarded reaction column or added support is used to hide that
restriction. Zero body response for a *spring* is supported when its own
positive compliance supplies the diagonal.

Reproduce the reference comparison by supplying the unmodified PR25 file from
the fixed commit above:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python \
  engineering/product-integration-20261018/numerics/run_adapter_comparison.py \
  --pr25-source /tmp/pr25-spatial-contact.py \
  --output /tmp/razr-adapter-comparison-new.json
```

This is an extraction of one useful law. PR25's old full-body driver, old
failure results, old test-count manifest and conflicting `spatial_contact.py`
are not adopted. The draft may be resolved administratively with links to this
semantic extraction and the preserved old evidence; it should not be labelled
as fully merged or fully capability-equivalent.

## Validation and controlled continuation

`targeted-unit-report.json` contains the executed ten tests in the two new WP7
test files, their source hashes, environment and complete output. The tests
cover a genuine released spring, an independent exhaustive three-variable
KKT oracle, infeasible or unsupported equilibrium, negative energy hidden by
springs, the explicit zero-response limitation, convexity, face/DOF order,
in-face negative witnesses, frozen target and changed manifest bytes. This
report is a narrow new-feature run and is not a re-run of either the previous
1187 main tests or the 1216 PR35 tests.

The additional KEY section budget below has two separate formula/scaling tests;
it does not change the scope or historical count in the ten-test report.

### Executed restart preflight and stopping condition

`restart-cache-preflight.json` and `restart-cache-execution.json` record the
completed read-only inspection on main at 2026-10-18 14:24:32 UTC. The process
took 3.472 seconds. It scanned 3292 files within its declared roots, completed
without errors and inspected seven response/cache candidates. Three response
arrays lacked matching manifest/point metadata. Four historical contact,
preload or L1/L2 states had matching hashes but zero bearing-point entries.
No current rigid-bearing restart candidate was identified.

The saved `rigid-install-v3/bearing-field-016.npz` contains `u`, `applied`,
`forces`, `rigid`, `planes` and `actuator`. It contains no response `H`, force
operator `C` or ordered point descriptors. This matches the PR35 source:
the bearing driver saves fields each iteration but does not persist its
in-memory force-response cache. The base `--state/response.npz` restored by
`solve_trace_probe.py` is the old case6 L2 response; the trace update still
requires rebuilding the elastic factorization and Schur response. It cannot
be silently treated as the current bearing model's cache.

The preflight therefore returned `stop_no_identified_bearing_response_restart`.
The proposed 900-second re-solve was **not launched**. A concrete next solver
step is to persist the exact bearing response, ordered force-point descriptors
and model/input/selection identity together, then verify a restore using the
existing response probes. The full original force-point set must be retained.
This missing restart checkpoint is separate from the unresolved contact gaps.

The read-only inspection can be repeated with an explicit root:

```bash
python engineering/product-integration-20261018/numerics/inspect_restart_cache.py \
  --root /home/qian-qi/.local/share/razr-slide-evidence --seconds 30
```

Its scope is response/cache-named NPZ files plus selected field/block headers.
A discovered candidate still requires exact trace identity checks and response
restore probes; file existence or a matching array shape alone never passes it.

The point-coverage calculation needs at most 30 seconds and starts no FE job.
A later solver pilot should restore a hash-matched existing exact elastic
response cache, add at most 128 bearing columns, perform at most two QP solves
with full gap audits, and stop at 900 seconds total wall time. Use one compute
thread and a peak memory budget no larger than the lesser of 24 GiB or 40% of
the measured available memory. If the cache or resources are unavailable, stop
before rebuilding the entire FE model. These are proposed limits, not a claim
that this pilot has executed.

Stop the pilot on a cache identity mismatch, KKT failure, unsupported physical
resultant, invalid or unresolved domain audit, or resource cap. Retain the
field, points, gap witnesses, iteration log and process exit. A reduction in
negative-cell count or sampling distance is a diagnostic result only. Advancing
the contact gate requires all body and bearing regions to satisfy their
original `1e-7 mm` bound, every force and moment equation to remain satisfied,
and independent field recovery/audit. Material, physical supports, actual
preload and fabrication decisions remain separate required inputs.

## KEY narrow-tab section sensitivity

`integration/key_section_budget.py` and `key-section-budget.json` address the
new web added by the current `L_KEY_YOKE` construction. The script pins
[`integration/cam_coupling.py`](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/a1b3cc1e0773446f2e36d0a607edf61211dd9919/integration/cam_coupling.py)
by SHA256. Its box endpoints `(13.2, 15.8, 4.05)` and
`(13.45, 39.6, 4.35)` define a nominal 23.8 mm extent along Y and a
0.25 mm by 0.30 mm X/Z section. This script does not remeasure the STEP file.
The current `L_KEY_YOKE.step` reference hash is
`a819b786a0d7f2a406194b60908233b106af6ed11988b4216c5e4e4d101aab94`;
the `native-v5-geometry.tar.gz` reference hash is
`249f50dae36b591df189e17ed8f46b1d1e793d481b1d0fb57f0ff1a553dfbd07`.
The original `L_ORIGINAL_KEY` does not represent this newly added web.

The actual material, unsupported span, guides, joint stiffness, force path and
load history are unknown. In particular, 23.8 mm is a CAD extent, not a measured
cantilever boundary condition. The calculations below are ideal uniform-beam
parameter studies, not strength acceptance or a prediction of real failure.

For the nominal section, area is `0.075 mm²`. The second moments are
`Ix = 0.0005625 mm⁴` and `Iz = 0.000390625 mm⁴`. With beam axis Y, X deflection
uses the weaker `Iz`. The report evaluates assumed elastic moduli of 2, 70 and
200 GPa, assumed unsupported spans of 23.8, 12, 8 and 4 mm, and Euler effective
length factors `K = 0.5, 1, 2` for ideal fixed/fixed, pinned/pinned and
fixed/free axial-buckling scenarios respectively. The moduli are sensitivity
values and do not identify the actual material.

For a *separate hypothetical cantilever with a transverse force at its free
end*, lateral stiffness is `3 E I / L³`. Euler's ideal centered axial load is
`π² E I / (K L)²`. Here E in GPa is multiplied by 1000 to obtain N/mm².
Changing the Euler K factor does not automatically change the cantilever's
transverse boundary condition.

| Assumed E | Assumed span | Weak-direction cantilever stiffness | Deflection under hypothetical 10 µN end force | Ideal weak-axis Euler load, K=1 |
| --- | ---: | ---: | ---: | ---: |
| 2 GPa | 23.8 mm | 0.00017385 N/mm | 0.057520 mm | 0.013612 N |
| 70 GPa | 23.8 mm | 0.00608483 N/mm | 0.00164343 mm | 0.476435 N |
| 200 GPa | 23.8 mm | 0.01738523 N/mm | 0.00057520 mm | 1.361244 N |
| 70 GPa | 12 mm | 0.04747179 N/mm | 0.00021065 mm | 1.874111 N |
| 70 GPa | 8 mm | 0.16021729 N/mm | 0.00006242 mm | 4.216750 N |
| 70 GPa | 4 mm | 1.28173828 N/mm | 0.00000780 mm | 16.867000 N |

The JSON includes both bending directions and hypothetical transverse forces
of 1, 10 and 100 µN. Linear deflection must remain small relative to span for
the beam approximation to apply. Euler values also require elastic buckling
and ideal end conditions; yield, imperfections, local notches, torsion and
guide clearance can govern first. No yield/fatigue data or actual force margin
has been established here. The larger short-span Euler numbers are therefore
not allowable forces.

The geometry ratios identify useful experiments without assigning a real load.
For unchanged section, material and support type, reducing assumed span from
23.8 mm to 8 mm multiplies lateral stiffness by 26.33 and ideal Euler load by
8.85. A change to a 0.30 by 0.30 mm section multiplies weak-axis I by 1.728;
0.35 by 0.40 mm gives 3.659, and scaling both nominal dimensions by two gives
16. No fit, admission, stroke, interference or fabrication clearance has been
validated for those larger hypothetical sections. An intermediate guide is
therefore a useful design branch to examine, together with measuring real
axial/lateral loads and checking that the guide actually constrains the weak
direction while preserving the required motion.

The dimension-loss example is also explicitly hypothetical. Reducing each
*total section dimension* by 0.02 mm produces 0.23 by 0.28 mm: area decreases
14.13%, Ix 25.20% and Iz 27.32%. If instead each of the two opposed outer faces
moves inward 0.02 mm, the total dimensions decrease 0.04 mm to 0.21 by 0.26 mm:
area decreases 27.20%, Ix 45.32% and Iz 48.63%. These are distinct geometry
scenarios, not manufacturing tolerances or a whole-assembly clearance stack.
The `output_origin` value 0.020 in `endpoint_joint_pawl` is not used as a gap.

```bash
python integration/key_section_budget.py --output /tmp/razr-key-section-budget-new.json
python -m unittest discover -s integration/product-study-tests -p 'test_key_section_budget.py' -v
```

The two tests check section axes and formulas, I scaling with the fourth power
of a uniform section scale, distinct `L⁻³` lateral-stiffness and `L⁻²` Euler
scaling, and the unchanged lack of any physical qualification flag.
