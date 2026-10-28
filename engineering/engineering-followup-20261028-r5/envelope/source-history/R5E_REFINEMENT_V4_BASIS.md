# R5E V4: refine real V3 retained cells at exact original boundary endpoints

## Actual prerequisite and reason for this change

The V3 pipeline was actually executed by GitHub Actions run `40641230212` at
commit `41333a369cbc44aab6fb5a723b75833a693ac16c`. Its full original16 worker
completed in 3.442656056 seconds with 133,005,312 B peak RSS and 1,124,952
boundary-box predicates. The pipeline and independent checker completed. Four
of sixteen original raw clearance gates passed. These actual records stay
unchanged.

V3 reduced panel/KEY bounds from about 18.648 to about 0.96 mm^3; each panel
frame retains only two of its original candidate cells. Other remaining
KEY/STOP bounds are approximately 1.4131346791, 0.1392068116/0.1964668737,
1.2973450117, and 0.0224/0.0796600621 mm^3. These are upper bounds, not
penetration witnesses.

The first selected real remainder is `case-001`, frame 1, original raw cell
index 202. R4's exact union merging retained all fine cut planes but made large
boxes spanning some of those planes. V3 required one exterior channel for each
entire open box. A thin expanded boundary layer at an edge can therefore block
a channel for the whole large box. V4 reuses exact endpoints of the actual
blocking boundary boxes to split that box, retaining every resulting thin
layer. It does not rebuild a full three-dimensional Cartesian arrangement.

The additional already-published non-axis support directions were inspected.
They are near axis directions for these cases, so they are not an adequate
basis for promising closure of the large spatial remainders. V4 first addresses
the directly observed whole-cell blocking with exact local subdivision.

## Mathematical invariant

Each root is one original positive R4 raw cell. Every split chooses one of the
original complete boundary-box endpoints strictly inside its parent interval.
The two closed children have the parent's exact union, overlap only in the
closed cut plane, have strictly positive diagonal maps from the unit cube,
and satisfy `V_left + V_right = V_parent` by exact rational arithmetic.
Every cut plane and every original cell face is retained as a closed
zero-volume carrier. There is no rounded-away displacement, minimum width,
sampling, discarded thin layer, or removal of an unproved material region.

An open leaf is excluded only by the V3 complete-boundary exterior-channel
lemma. Any leaf not proved exterior is retained at its full exact directed
volume. Retention needs no material-intersection assertion. The sum of all
retained leaves, intersected with the original independently established whole
support upper bound, is a valid upper bound under the unchanged R4 complete
boundary-semantics premise. The original float64 `1e-7 mm^3` gate is unchanged.

## Finite algorithm and stopping rules

For each unexcluded leaf, collect endpoints from the actual first blocking
piece in each of the 12 registered channels. Only strictly interior endpoints
are eligible. Select the endpoint with the smallest exact fractional distance
to a parent boundary, breaking ties by coordinate and exact value. This peels
off thin boundary layers; the larger child is processed first. No midpoint or
new geometric sample is introduced.

Registered absolute limits for one worker:

- At most 4,096 splits across the complete phase, including all frames.
- At most 24 splits on one root-to-leaf path.
- At most 12,000,000 complete-boundary box predicates; a mid-search budget stop
  returns an unresolved retained leaf and does not fabricate a blocked-channel
  certificate.
- A leaf of exact volume at most `original_TOL / 100000` may be retained
  without further refinement. Its entire nonzero volume is still summed.
- If the split budget/depth is exhausted, no eligible original endpoint
  exists, or a predicate budget is exhausted, the whole remaining leaf is
  retained. All unvisited pending leaves are also retained. Thus a completed
  but capacity-limited phase can still truthfully fail its clearance gate.

With 1,474 original roots and 4,096 splits, a full run has at most 5,570 leaves
and 9,666 total tree nodes. Nodes store split coordinates and leaf certificates;
child boxes are reconstructed, not duplicated in every record. Old records,
the source bridge and source locks remain separate and unchanged.

## Capacity basis and actual preflight requirement

The new predicate budget is about 10.667 times V3's actual predicate count.
Applying the measured whole V3 worker time to that factor gives a deliberately
rough 36.73-second cost estimate before additional tree/serialization work;
this is a planning estimate, not a time proof. The original 600-second,
768-MiB, shared-memory, disk, output-byte, and owned-process gates remain in
force. The larger child-first traversal and node limit bound retained memory.

The portable sequence is: one actual retained cell -> separate verifier ->
actual all16 input/capacity preflight -> all16 refined run -> separate verifier.
The first selected cell must actually reach the unchanged clearance threshold
before the all16 phase is launched. The preflight must re-read all original
identities and record actual piece/root counts, coordinate-size bounds,
static node/predicate limits, runtime and RSS. Every later contract binds these
actual prerequisite reports and owned supervisor receipts. A capacity or
resource failure remains an actual failure; it is not converted to a pass.

## Qualification scope

The complete original displacement intervals, all curved/support pieces, all
original positive cells, the original threshold, and all prior failures remain
represented. This method does not prove native BREP material semantics,
compiled curve/transform errors, the separate L2 tolerance diagnostic,
current complete-factory G2, FE qualification, or physical G3--G5.
