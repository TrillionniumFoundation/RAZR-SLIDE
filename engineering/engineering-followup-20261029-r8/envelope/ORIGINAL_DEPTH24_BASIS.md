# R8 original-depth primitive correlation

The first new execution is the saved V6 case-028/frame-1 retained parent
`[78,375]`, at cumulative depth 24. No new split is allowed. Its original
12 channel directions, 523/179 ordered boundary pieces, complete original
displacement box and `1e-7 mm^3` criterion remain fixed.

The original V6 axis/slab predicate is tried first. Only an unresolved piece
is intersected with the closed channel box. The full original displacement
box is subtracted by outward interval subtraction. This box contains every
stationary source point that could enter the channel under any displacement.

For a stored cylinder `p=O+r X cos(u)+r Y sin(u)+Z v`, invert the exact
stored matrix `[X Y Z]`. Its first two dual rows `a,b` satisfy
`a.X=b.Y=1` and the four cross identities zero. Consequently
`Q(p)=(a.(p-O))^2+(b.(p-O))^2=r^2` without assuming floating-point
orthogonality or normalizing any axis. A circle is contained in the same
unbounded cylinder, so this necessary equality also safely applies to its
complete angular domain. No angular or axial subset is selected.

The first bounds are the exact sum of squared affine interval ranges. If
that bound is inconclusive, evaluate the convex quadratic at all eight box
vertices, all valid stationary points on 12 edges and six faces. The maximum
is attained at a vertex. Since the rank is two, an interior minimum has a
nonzero null direction that leads to the boundary with unchanged value.
On a singular face the same argument leads to an edge; on a flat edge its
endpoints suffice. These candidates therefore give exact extrema even when
one or more box dimensions is zero. Only `minimum > r^2` or `maximum < r^2`
excludes a piece; equality is retained.

For a stored Line, intersect its complete original parameter interval with
each coordinate inequality after full displacement subtraction. An empty
intersection proves no point can enter the channel. Tiny nonzero direction
components participate exactly. For a Plane, use the cross product of its
stored two basis vectors and test the entire unbounded plane; this is a
superset of every original bounded face.

The complete original records must have identity placement and identical
local/global extraction. Unsupported or degenerate records retain the old
predicate. All old boxes and slabs remain. Every source record is compared
between the saved original native producer and separate reader; no new
native computation is performed in this pure rational diagnostic.

This extends the explicitly conditional serialized-source primitive model.
It does not certify native evaluation error, bounded-face filling, native
trim membership, an entire tolerance tube, whole-domain G2 or physical
clearance. The two finite factory passes and historical failed runs are
unchanged. Full channel success would prove only the selected open cell
interior absent from one conditional whole-material model; closed partition
boundaries remain as zero-volume carriers.

## Capacity basis before execution

The preceding saved Line run read both complete 65 MB native inventories,
checked 118 inputs and one 523-piece channel in 1.683 s, with peak RSS
315,944,960 bytes. The proposed parent run reads the same two inventories
sequentially, retains only two whole source records, and parses one saved
V6 certificate. At most 12 channels and 4,212 pieces are visited, with no
new source tessellation and no new split. An unresolved quadratic requires
at most 26 candidate points, each formed by fixed-dimensional rational
arithmetic. The initial execution has a 60-second wall limit and a 768 MiB
address-space limit, with actual peak RSS and elapsed time recorded.
These are capacity bounds for a new diagnostic, not changes to original
V6 acceptance or permission to infer all-frame convergence.

The complete original V6 all-frame experiment's 600-second, 805,306,368-byte,
4,096-split and depth-24 limits remain unchanged. Any broader new execution
must first use this actual cost and retained-volume evidence to justify its
scope and must keep unresolved volume in the exact total.
