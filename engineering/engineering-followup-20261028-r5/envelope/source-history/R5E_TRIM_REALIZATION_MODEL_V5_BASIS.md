# V5: a separate trim-realization-conditioned enclosure experiment

## Actual V3 and V4 remain unchanged

V3's original complete-boundary-box method has four raw clearance passes out of
the original sixteen frames. V4 was actually run at commit
`06e4f37690e2d5b9dc2abaf69cab9ba16957f1e2` in Actions run `40643098035`.
Its selected real remainder produced 6 exact splits, 13 tree nodes and 7 leaves
in about 0.296 seconds. No leaf was excluded, and the retained bound stayed
about 0.48 mm^3, above the original threshold. The independent V4 process
checked the partition and executed twelve applicable negative controls, then
failed its own requirement for case-derived channel controls because no
excluded leaf existed. It was not a resource failure. Later phases did not run.

V5 does not reclassify any of these original results. Its new bounds are
**conditioned on an explicitly defined trim realization class**. Membership of
the actual native face in that class remains unverified. Neither native trim
semantics nor complete-factory G2 is claimed.

## Source and the missing spatial information

The existing panel face 95 and its matching sleeve faces have an inner wire of
four line pcurves. R4 enclosed each whole face by its UV bounding rectangle;
that rectangle fills the inner hole, creating a closed artificial barrier to
V3/V4's exterior channels. Original source `cam_coupling.py` also constructs
the sleeve from four fused boxes around the same nominal hole. That source is
corroborating design evidence, not proof of native Boolean set identity.

A lossless source projection selects complete relevant planar face records
from the original 65,374,048-byte native inventory, whose original registered
SHA is checked. It preserves every original pcurve parameter, endpoint source,
orientation, tolerance, location, outer wire and other inner wire. Thirty-two
whole-material records map the original sixteen moving/fixed pairs and full D.
The projection contains 40 complete candidate faces and 80 candidate four-line
inner wires, all in the four panel records. The current KEY/STOP inputs have
no candidate inner wire of this narrow class; their old boundaries are retained.
Source projection and independent source readback are not mathematical passes.

## Exact auxiliary hole construction; no original endpoint is changed

Admit only an inner wire with exactly four actual Line pcurves whose UV
directions are exactly one of (+/-1,0) or (0,+/-1). Compute their true trimmed
endpoints using the original rational representations of first/last parameters.
Apply the recorded occurrence orientation. Require two distinct constant-U
sides and two distinct constant-V sides. Their intersections define an
auxiliary rectangle, not replacement source endpoints.

Assign each true directed endpoint to the uniquely nearest auxiliary corner on
its constant-coordinate side. The four oriented ideal sides must make one
four-corner directed cycle, with each corner having one predecessor and one
successor. Let delta be the exact maximum L-infinity distance of the eight true
endpoints from their assigned corners. Require four times delta smaller than
both rectangle widths. Preserve every signed endpoint offset and every actual
segment. Around each auxiliary corner retain the closed square of radius
delta. The hole core is the open rectangle obtained by moving all four ideal
sides inward by delta. It is nonempty; its boundary is never removed.

The declared realization class allows the original oriented line segments to
be joined only by paths inside their corresponding corner squares, and
interprets the recorded inner wire as a removed hole of this face. Such paths
cannot cross the core. Deforming only within these squares preserves the
ideal cycle's winding number about any core point. Therefore every realization
in this class excludes the core. If delta is zero, the endpoints already meet
exactly in this auxiliary model. If it is nonzero, its numerical value is only
an observed endpoint-to-corner bound; it is **not** a proven native closure or
compiled-error bound.

The two unproved membership conditions remain explicit:

1. Native trimming uses the intended inner-wire-as-hole semantics.
2. Native treatment of the actual pcurve endpoint gaps stays within the
   registered corner-square closure class.

No native `isClosed`, `isValid`, tolerance field, source CSG operation, or
`Common = 0` substitutes for proving these conditions. New model passes must
not be placed in the original strict native qualification column.

## Conservative boundary boxes for that model

For a selected planar face, use its complete stored local affine surface
`x = origin + u X + v Y`. Require exact identity placement, as in the original
R4 source class. Choose the first lexicographic pair of coordinates with a
nonzero 2-by-2 tangent determinant. Its exact inverse maps that pair of world
coordinates to UV. Project the complete old stationary face box through this
inverse to obtain a conservative outer UV rectangle. Require every admitted
hole core strictly inside this rectangle.

Subtract each **open** core from the current UV rectangles using four closed
strips. Every original rectangle boundary and every cut rectangle boundary is
retained. Explicitly append the four zero-width closed edges of each whole core;
later subtractions retain these carriers even when cores overlap. The strips
and carriers are a conservative cover, and may retain additional zero-measure
boundaries. Zero-width patches are retained. Map each resulting UV patch through
the exact affine plane, intersect its axis box with the original stationary
face box, and add the entire original D for a moving material. A genuinely
empty intersection may be omitted only with its original UV index recorded;
a zero-width intersection remains. Any unsupported or rejected face retains
its entire original box, and the reason remains recorded.

Every old boundary piece has an explicit mapping to either its unchanged box
or all of its replacement patches. All old 3D edges and vertices remain
unchanged, including every actual endpoint and terminal extension. The old
stationary boxes are recovered by exact subtraction of D's lower/upper bounds;
the original nonzero D is added back exactly after refinement. V5 then applies
the already retained exact endpoint-splitting/exterior-channel method to these
model-conditioned complete boundary covers. Its tree, positive directed
volumes, zero-measure carriers, pending leaves and all resource gates remain.

## Registered capacity and sequence

This initial class has only 80 four-line candidate loops in 40 faces. Every
face admits at most 1,024 UV patches; every material at most 4,096 complete
boundary pieces. Exceeding either bound causes an explicit retained original
face or an explicit worker failure, never material deletion. The exact tree
limits stay at 4,096 total splits, depth 24 and 12,000,000 boundary predicates.
Tiny leaves at or below original_TOL/100000 retain their entire nonzero volume.

The source census is not uniform: each of the four panel records has ten
candidate faces with respectively 2, 10, 1, 1, 1, 1, 1, 1, 1 and 1 candidate
inner wires. Before the hard patch cap, a face with n holes has at most
4^n strip-derived patches (including zero-width ones), plus 4n explicit
zero-width carriers. Thus the hard-capped
replacement bound for one panel is 1,438 - 10 + 24 + 1,024 + 8*8 = 2,540 pieces,
below the 4,096-piece material cap. Unchanged nonpanel materials remain unchanged.
The independent checker uses at most (4n+3)^2 exact UV strata per face, including
closed edges and points; for the largest ten-hole face this is 1,849 strata.
Its search is bounded by the actual patch count and the 1,024-patch cap.

Actual prior V3 full16 work used about 3.443 seconds, 133,005,312 bytes peak RSS,
and 1,124,952 boundary predicates on these same complete R4 proofs. A linear
predicate-count projection to the unchanged 12,000,000 cap is about 37 seconds;
this is a capacity estimate, not a timing guarantee for the new model, parser,
or independent UV checks. The new source projection is 35,630 compressed bytes
and 714,083 decoded JSON bytes, compared with 21,025,630 bytes of unchanged
public R4 inputs. The owned 600-second/768-MiB and output gates remain decisive.

First execute the original real retained cell 202 of case-001/frame-1 under
this new explicitly conditional model, then independently reconstruct its
hole, patches and tree. Only an actual conditional model pass permits the
all16 model input/capacity preflight and the full original16 model experiment.
The actual preflight records the admitted/rejected holes, patch counts, exact
coordinate sizes, source identities, time and RSS before the full phase.
The original 600-second, 768-MiB, shared-memory, disk and output limits apply.
There is no claim that these planned runs have already occurred.

The next checker must handle a real case with no excluded or no split leaves
honestly. Mandatory analytically complete box/channel and exact partition
controls still run, including positive controls and deliberate rejection
controls. Case-derived mutations are additional when their prerequisite
objects actually exist; otherwise that specific case-derived control is
explicitly not applicable. Missing control objects are never fabricated.

For the first actual applied trim face, the independent process also mutates
copies of real certificates: expand an actual hole-core endpoint, omit its UV
patch cover, omit a retained original edge/vertex, and alter an actual swept
patch endpoint. Each available target must be rejected by the same independent
boundary reconstruction; an absent target is explicitly not applicable. These
planned controls have not run at source freeze and do not themselves establish
native trim membership.

## Required report separation

New phase names are `single_trim_model_cell`, `preflight_trim_model` and
`all_trim_model_frames`. New result fields use `trim_model_conditional_*`.
Every report must keep `conditional_trim_model_only=true`,
`native_trim_class_membership_verified=false`,
`inner_wire_hole_semantics_verified_for_native=false`,
`original_raw_gate_reclassified=false`, and `full_continuous_G2=false`.
Original R4/R5 raw results and the actual V4 stop remain separately available.
The original float64 `1e-7 mm^3` threshold and full original D are unchanged;
passing them in the new model does not establish either native membership
condition, manufacturing tolerances, FE qualification or physical G3--G5.
