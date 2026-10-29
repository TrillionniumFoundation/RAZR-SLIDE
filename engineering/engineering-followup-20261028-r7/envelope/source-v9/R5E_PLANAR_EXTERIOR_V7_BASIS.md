# R5 V7: bounded planar exterior-channel certificates

## Actual failure motivating this new method

V6 attempt-1 is a completed local experiment, not a proposed or GitHub run.
Its producer and independent checker agree on 8/16 conditional passes. The
original V3 result remains 4/16, and V4's true mathematical and checker failures
remain unchanged. V6 spent its fixed 4096 new splits on case-028/frame-1. Its
0.004396435272042011 mm3 retained bound includes 0.004316242220346019 mm3 in
3184 depth-24 leaves and about 0.00008019305168412208 mm3 in 14 leaves retained
at the global split limit. Later frames retain their significant remainder
at the exhausted global split limit. This distinction prevents a budget-only
explanation for the first frame.

The first V7 witness is the largest actual V6 depth-limit leaf: case-028,
frame 1, V6 root 76, node 47, prior V5 locator [28,17]. Its directed volume is
0.0035074449511051124 mm3 (the exact rational is bound in the selection file).
The recorded KEY z channels are blocked by plane faces 37 and 39. Their
complete outer wires each contain 15 Lines and 3 Circles. The corresponding
other STOP cases use plane faces 31 and 33. The r=0.1 STOP cylinder blocks
the other material's paths. The actual D widths in all eight unresolved
frames are at most 8.881784197001252e-16 mm; no displacement component is
removed, but this record does not support attributing the large remainder to
displacement correlation.

These conclusions are readings of existing V6 records. The separate bounded
source diagnostic took 1.9535737599944696 s, 173162496 B peak RSS, processed
88781379 decoded bytes, and performed no new channel search, curve enclosure
or native operation. The V6 actual certificates, source, false gates and
resource-budget exhaustion remain immutable.

## New proof rule

The new rule can prove that a spatial channel misses one bounded planar
trimmed face even when it intersects that face's old rectangle and plane
slab. It does not replace the whole material by sampled geometry and does
not change the old 3D faces, edges or vertices.

Write the stored plane as `P(u,v)=O+X*u+Y*v`. Every stored scalar is interpreted
as its original exact rational representation; the real trigonometric model
is stated separately below. Use the exact left inverse
`L=(A^T A)^(-1) A^T`, where `A=[X Y]`. Reject a singular basis. No assumption
that stored direction vectors are perfectly orthonormal is needed.

For a closed spatial channel box C and the complete original displacement
box D of this material, form the closed stationary candidate box

`B = (C - D) intersect old_stationary_face_box`.

The interval subtraction is `[C_lo-D_hi,C_hi-D_lo]` on every axis. The fixed
material uses the exact zero box; the moving material uses all original D
components. Strictly inverted B is empty; equality and zero-width ranges are
retained. Subtract the plane origin before projection: the closed UV
rectangle is `Q = L(B - O)`, evaluated by exact interval arithmetic. This is
a superset of all UV points whose source-plane point, after any allowed D,
could meet C. Off-plane points may enlarge Q; none are discarded by a
floating-point plane-membership test.

The exact projection `R = L(old_stationary_face_box - O)` supplies a finite
UV rectangle containing the modeled face. For each of the four UV axis/end
choices, form a closed rectangle joining all of Q to a coordinate strictly
outside R (R's bound plus or minus one). This is the candidate exterior path.
It must be strictly separated from every member of the complete UV boundary
cover. Coordinate or registered support intervals must have a strict gap;
touching is not accepted. Equality therefore cannot silently discard a
closure, vertex, seam or projected boundary.

If such a closed path exists, its connected set contains a point outside R
and meets no modeled face boundary. Every point of Q is consequently outside
the bounded face region. The spatial channel misses this planar face for
the complete D. This supplies a new per-piece separation certificate inside
the existing complete-material exterior-channel proof. Every other spatial
piece still needs its original coordinate/slab separation or its own new
complete planar certificate.

This is an exterior-connectivity theorem. It never classifies a point by
sampling, never infers the filled side from an approximate polygon, and
does not require a numerical winding number or an unproved Jordan curve
test. It cannot qualify a bounded cavity that has no certified exterior
path. A failed or unsupported planar certificate leaves the original piece
and positive volume retained.

## Exact source curves and closure uncertainty

Every original wire and every original occurrence is required. Identity
locations, mapped edge indices, recognized FORWARD/REVERSED orientations,
and the complete first/last parameter intervals are checked. The first
registered class supports only original Lines and Circles. A missing or
unsupported field leaves that whole plane piece unchanged.

A Line's entire closed parameter interval receives its exact affine box
and its exact 2D normal support constraint. Each Circle is covered by exactly
64 closed consecutive angular patches, retaining both source endpoints and
all shared endpoints. Circle placement is `C+r*(X*cos(t)+Y*sin(t))`, with the
original rational C, r, X and Y. The stored axes need not be ideal unit axes:
the rational dual normal, when used, is verified against those same axes.

For each angular patch use 24 sine/cosine Maclaurin terms at a dyadic centre
with denominator 65536, the degree-47 common error bound `abs(c)^48/48!`,
the full exact source offset interval, and the same valid second-derivative
remainder used in V6. Endpoint boxes use the same real-function enclosure
over their actual singleton parameter values. No endpoint is moved to a
sampled point. The independent checker recomputes polynomial enclosures by
reverse Horner evaluation and independently reconstructs all boxes/supports.

After each occurrence is oriented, connect its terminal endpoint interval
to one uniquely closest initial endpoint interval. The chosen upper bound
on L-infinity distance must be strictly smaller than every competing lower
bound; the successor relation must be a bijection and one directed cycle
over the complete wire. Each connection is enclosed by the coordinate hull
of the two complete endpoint boxes, expanded in both coordinates by that
hull's largest width. These closed gap boxes remain in the boundary cover.
An ambiguous association or incomplete cycle rejects the new face model.
No real/native endpoint closure is asserted from this construction alone.

The explicit additional realization-class premise is that the bounded
planar material region, contained in R, has its whole topological boundary
within the complete original real pcurve images and the specified closure
boxes. Native membership in this class is unverified. Native face-side,
native curve semantics, corner-closure behavior, compiled transforms and
their errors are not established by this proof. Wire direction is used to
bind endpoint succession; it is not used to guess which sampled region is
material. Completeness of the boundary and boundedness are premises, not
conclusions of a numerical winding calculation.

## Finite scope and unchanged gates

The lossless original projection already independently checked for V6 has
48 candidate planes, 48 wires, 472 Line occurrences and 48 Circle occurrences:
520 original occurrences total. Replacing each Circle by 64 patches and
adding at most one closure box per occurrence gives the finite maximum

`472 + 48*64 + 520 = 4064 UV boundary pieces`

over all 48 plane occurrences. Plane outer wires have 4, 12, 14 or 18
occurrences. Their maximum is `15+3*64+18=225` UV pieces per face. Rejected
faces retain their full old pieces. V6's complete 3D boundary counts are
unchanged; UV pieces belong only to the new per-face separator proof.

The actual V6 forest has 5633 positive leaves, 690 excluded and 4943 retained.
V7 refines only those 4943 retained source leaves. At the unchanged global
4096-new-split cap, its full forest has at most 13135 nodes and 9039 leaves.
All prior exclusions and all closed zero-volume carriers remain separately
bound. The original float64-derived TOL `1e-7` and tiny-retained TOL/100000
threshold remain unchanged. Pending, tiny, depth-stopped and budget-stopped
positive leaves are retained in full.

The total registered boundary-piece-test budget includes both spatial and
new planar pieces. The total registered elementary support-inequality
budget likewise includes every spatial and UV inequality. Both remain
12000000. Partial UV work stopped by either budget cannot exclude a leaf.
The fixed 64-patch and 24-term construction has no recursive angular grid.
The inherited original 600 s, 805306368 B worker RSS, 7301444403 B shared
ceiling, 104857600 B disk floor, 41943040 B output cap and 4194304 B metadata
margin are unchanged. A successful old V6 run is not a V7 runtime estimate.

Five owned stages must run sequentially: the selected original V6 leaf;
independent verification including actual and analytic controls; measured
all-16 source/capacity preflight; bounded full refinement; independent full
verification. The selected positive leaf must actually be reduced below
the unchanged TOL with a positive new excluded amount and at least one
actual planar-exterior separator before later work may start. A real
failure stops later stages and remains a failure record.

## Required independent controls and preserved scope

Keep the previous complete-box, exact partition, tiny retained volume and
all-retained/no-excluded analytic positive controls, with applicable actual
case controls explicitly distinguished from synthetic controls. New controls
must reject an omitted original pcurve/closure piece, a shortened angular
domain, a deleted positive Taylor remainder, a false strict UV separator,
an exterior path that fails to reach outside R, an incorrect inverse/full-D
projection, and a changed closure association/cover. Unsupported or absent
actual mutation targets are N/A, never counted as a rejection pass; the
registered analytic controls remain mandatory.

Every V7 report retains `conditional_planar_exterior_model_only=true`,
`native_planar_region_semantics_verified=false`,
`native_primitive_semantics_verified=false`,
`native_trim_class_membership_verified=false`,
`original_raw_gate_reclassified=false`, `full_continuous_G2=false`.
The original V6 eight conditional passes and its actual failures to clear
the other frames are never reclassified. No V7 mathematical run or positive
qualification is claimed merely by writing this basis or source files.
