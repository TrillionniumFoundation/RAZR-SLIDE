# Independent cross-review: numerical evidence and envelope proof scope

## Numerical work completed

The numerical agent recovered the exact original N13/N14/N15 materials and
executed the new readbacks bound in `../numerics/R9_NUMERICAL_SCOPE.json`.
Original panel and frame five-probe residuals, panel correction history, four
external load scalar/block residuals, complete saved H and five-action original
cache restore passed at unchanged criteria. The original dependency versions
were not reproduced. The additional complete linear-seed bitwise replay retains
a measured 9-entry `loadG` discrepancy of at most `2.220446049250313e-16`; the
exact rational diagnostic is preserved, with no threshold or original data edit.

## Envelope source review

The reviewer read the R9 balanced and gradient producers, parsing cache,
gradient axis selector and independent reader, together with the original R8
primitive correlations and independently written source/channel checker.

The rank-two quadratic extremum argument is sound for the serialized model.
The maximum of the convex quadratic occurs at a box vertex. Any stationary
interior minimum has a null direction that reaches a proper face without
changing its value; singular face minima can be reduced again to a proper
face. Thus the producer's vertices/edges/faces enumeration and the reader's
independent rational 27-face enumeration cover the extrema, including
zero-width boxes. Stored basis duals are used without a normalization change.

R9 correctly distinguishes a conservative unresolved enclosure from an
exclusion. `verify_observation` requires `below_radius` or `above_radius`, and
the independent checker verifies both conservative bounds and strict radius
separation. The retained mutation that changes a valid enclosure into an
unresolved one exercises the actual old reader gap and must be rejected by
the R9 wrapper.

The independent reconstruction checks original root count/order/boxes, the
complete original displacement box, every reachable node, exact midpoint
partitions, inherited depth, complete successful boundary-piece coverage and
the exact retained/excluded volume sums. Tiny positive boxes remain retained
and counted. The global split, depth and piece-test checks use the unchanged
4096, 24 and 12000000 limits. The axis heuristic affects refinement efficiency;
it does not supply an exclusion proof.

These observations support the conditional serialized-source-model scope.
They do not establish native bounded-face filling, BREP error bounds, native
envelope topology, current-geometry FE or continuous G2.

## Concrete recorded-budget audit

`R9_BALANCED_RECORDED_BUDGET_AUDIT.json` independently reads the completed
balanced run, checks its source/report identities and exact declared limits,
and records 1537 roots, 4096 global splits, 3859611 piece tests,
517.482501109 seconds and 445419520-byte reported peak RSS. It confirms eight
conditional passes and eight non-passes. The elapsed measurement is taken
after proof-tree serialization and before the final report write. This audit
does not claim an independent external wall-clock measurement or confuse RSS
with the producer's 805306368-byte address-space limit.

The budget audit does not rerun the complete mathematical certificate reader.
The independently executed complete reader remains the authority for every
individual exclusion and partition.

The balanced complete reader subsequently finished successfully in
293.958234314 seconds, independently retaining the same eight conditional
passes and eight non-passes. All eight mutation controls and seven analytic
controls passed, including the conservative-but-unresolved quadric rejection.

The separate gradient producer also completed. Its independently checked
recorded budget is `R9_GRADIENT_RECORDED_BUDGET_AUDIT.json`: 1537 roots, 4096
splits, 3853102 piece tests, 348.126441491 seconds and 462438400-byte peak RSS.
It still reports eight passes and eight non-passes; its worst retained bound
is `3.0052596034059657e-7`, above the unchanged `1e-7` threshold. Its complete
independent certificate readback then completed with the budget-aware v2
reader in 365.277779757 seconds and a reported peak RSS of 313384960 bytes.
All 16 forests, 4096 splits, eight actual mutation controls and seven analytic
controls passed readback, while the original gate still has only eight passes
and eight nonpasses. A completed verification of a nonpass does not change
that nonpass into a qualified frame.

## Correlated cylinder and slab review

The cylinder/slab argument is conservative under the retained conditional
boundary-source and exterior-channel assumptions. Fix any one displacement
in the complete original D. All coordinates of that displacement remain in
the radial derivative query, axial parameter interval and support projection.
If the radial quadratic is nondecreasing toward the known exterior and every
remaining channel boundary piece belongs to the same original cylinder, a
point strictly outside that cylinder cannot be an interior material point.
The second material's channel decreases a nonzero projection. The minimum
projection of all remaining boundary pieces then bounds that material from
below. The resulting slab contains the intersection, up to the retained
zero-volume boundary carriers. It is an intersection-volume upper bound,
not an exact clipped-solid volume or a native topology certificate.

The checker verifies the ordered complete twelve-channel census for a
cylinder/slab bound, including every original piece and every unresolved
piece projection. Early termination is allowed only for an entirely proven
exterior channel. No complete-family claim follows from a failed prefix.
All source shifts are independently derived from material side and the
original D. The exact dual axial coordinate uses the signed determinant;
the support square root is nonnegative and is squared to verify outward
rounding. The slab integral is in the original Cartesian coordinates. Its
Jacobian is `1 / abs(n_j)`, so no additional cylinder-basis determinant is
needed. A zero projection component is not an admissible slicing axis.

`R9_CYLINDER_SLAB_INDEPENDENT_PILOT_REVIEW.json` records a third-party process
that did not import the producer. It independently rebound both original
native inventories, the original frame/D and saved proof, reconstructed the
complete containing root partition, and checked the actual retained cell
at root 60/node 671. All 12 channels and 4212 original piece tests agreed.
The independently checked cell upper bound is `8.973910713019907e-20` mm3,
versus the original box volume `3.2314619085709764e-9` mm3. Three additional
real-certificate mutations and ten literal analytic controls passed. These
include negative normal, negative basis determinant, full nonzero D,
closed tangency, unsupported square root, zero slicing denominator,
singular basis and inverted directed box. The process took 5.563152513
seconds and reported a peak RSS of 238460928 bytes.

The first cylinder checker did not explicitly require the selected cylinders'
local and native-global surface records to agree. The reviewer reproduced
that narrow subroutine gap by changing only the native-global source in a
copy. Every actual required original record was independently checked and
does agree, so the gap does not invalidate this saved leaf. The owner added
the checks for both the seed and every other unresolved cylinder in the new
`check_cylinder_slab_r9_v2.py`, preserving the executed first version. The
owner's separately executed strengthened pilot reader rejects the changed
global source. Its source diff was independently reviewed.

This local result justifies trying the new whole-root algorithm. It supplies
no whole-frame, whole-domain, native-envelope or full G2 pass. The prior
balanced and gradient nonpasses remain separate actual results with their
complete costs.

## Issues sent to the envelope owner

1. The initial independent reader did not enforce the report's complete limits
   object or recorded final elapsed time at most 600 seconds. The separate
   budget audit supplies that check for the completed balanced execution.
   The new `read_balanced_all16_r9_v2.py` now enforces these checks directly,
   without changing the identity of the already executed version.
2. The producers disable the alarm before final serialization. A timeout or
   piece-limit exception inside one of the two child appends can occur after
   subtracting the parent volume and setting its kind to split. The finally
   conservation assertion can then raise again, hiding the original failure
   and preventing the partial report from being written. This did not occur
   in the completed balanced run. The new `atomic_refinement_r9.py` prepares
   both children before a single root-reference assignment, leaving the old
   committed root intact when child construction fails. Its four small
   interruption/success controls and driver source were reviewed.

The first new cylinder/slab driver's serialization exception path still
needed two corrections when reviewed: a timeout during proof writing could
leave later committed roots and pending-child diagnostics unsaved; and a
failure after the root-reference assignment but before clearing the pending
attempt could label already committed children as uncommitted. Both were
reported directly, with a separate disqualified recovery serialization and
an explicit actual commit-state marker requested. A successful full reader
must also check final elapsed time and `recorded_budget_passed`, since the
final time sample is later than the preliminary execution flag calculation.

The separately named `cylinder_slab_all16_r9_v2.py` now preserves those
conditions through `recovery_serialization_r9.py`. The v1 source was not
overwritten. After a qualified serialization failure, v2 records the original
exception, cancels qualification and the deadline, writes the committed
payloads to a separate recovery directory, and records recovery cost. A second
recovery failure has its own field and cannot hide the original failure.
The pending-attempt label is derived from the actual live root and child
object identities, distinguishing a failure before and after commit.

The reviewer separately executed `audit_recovery_serialization.py` and
retained its evidence under `recovery-io-control-attempt1/`. It actually
interrupted the second gzip payload, preserved that original truncated JSON
and its hash, independently reopened both complete recovered payloads and
pending-child evidence, and verified that qualification remains false. The
original exception and the partial JSON parse failure are saved in its report.
This is an executed synthetic I/O control of the new helper, not an execution
of the whole driver and not a retrospective recovery or qualification of v1.

The new all16 reader source was also reviewed. It reconstructs D from the
immutable original frame, verifies original report/certificate/native
inventory identities, all root locators and boxes, every reachable node,
strictly positive directed partition volumes and conservative cell bounds.
It independently checks twelve-channel proofs, exact tiny retention, final
time and recorded budget status, original frame order and global counters.
At this review snapshot, that source review is not being represented as an
executed all16 cylinder/slab readback.

No envelope source or result was edited by this reviewer. The new whole-root
driver is a separate attempt; its eventual execution and complete independent
readback must be recorded before changing any whole-domain qualification.

## Distinct qualification states at this review snapshot

| Evidence | Mathematical/source review | Producer execution | Independent readback | Native obligations |
| --- | --- | --- | --- | --- |
| Balanced original-root forests | Reviewed | Completed; 8/16 gate passes | Completed; same 8/16 | Unqualified |
| Gradient original-root forests | Reviewed | Completed; 8/16 gate passes | Completed; same 8/16 | Unqualified |
| Actual cylinder/slab pilot leaf | Reviewed | Completed for one saved leaf | Independently completed for that leaf | Unqualified |
| Cylinder/slab all16 v1 | Core and reader sources reviewed | Separate running attempt; no final result asserted here | No execution asserted here | Unqualified |
| Cylinder/slab v2 I/O recovery | Source and small fault controls reviewed | Whole driver not executed by reviewer | Two synthetic recovery payloads independently reopened | No geometric qualification implied |
