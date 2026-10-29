# V6: bounded primitive-support refinement of actual V5 retained leaves

## Actual evidence and the limited target

V5 ran at commit `2ce252f25d340b056bfd350bdde8c743f915c9a4`, Actions run
`40645988108`, with frozen source lock SHA256
`d05a6f6a69ac5eb627d3d1180ff543c4f9b70c7c424c972dfab2b305b8a21211`.
The complete pipeline and independent verifier finished. Eight of sixteen
frames passed the unchanged threshold in its explicitly conditional model.
The original V3 raw 4/16 and V4 failed attempt are not reclassified.

The eight remaining frames are case-028, case-037, case-063 and case-072,
each in frames 1 and 2. Their retained upper bounds are about 0.016 mm^3.
There are 44 non-tiny retained leaves in these frames; all stop because no
registered box endpoint lies inside the leaf. They did not exhaust the split
or predicate budgets. Their union is approximately the 0.2 by 0.2 by 0.4 mm
box around the STOP pin. The diagnostic records original rational boxes and
each actual blocking piece, rather than inferring interference from a bound.

Each remaining frame names seven KEY faces and STOP face 0 as the first
blockers of its twelve registered channels. In each KEY group, six faces are
planes and one is a radius-0.16 partial cylinder: face 78 for STOP_0 and face
65 for STOP_1. STOP face 0 is the radius-0.1 pin cylinder. Across the eight
frames these are 48 plane records and 16 cylinder records. Original mounted
STEP and the two existing native inventory readers support these primitive
identities. Existing native base-point Common is zero for all eight frames;
that observation is neither a continuous-domain proof nor a V6 premise.

R4's `run_independent_support_r4e_v4.py` encloses every cylinder with the
entire circle's radial range, regardless of its actual U interval. For
example, case-028/material-3 face 78 has U approximately [pi,4.248741371384]
but the original support uses the full circle. The adjacent planes are also
represented solely by axis boxes. These are documented sources of loss of
parameter and spatial correlation. No new hole or outer-wire interpretation
is needed to tighten the already declared primitive parameter models.

## Preregistered first witness and reuse of the actual proof

The first target is the actual retained V5 leaf case-028/frame-1, original
R4 root 8, V5 node 13, with approximately 0.002 mm^3 positive volume. Its
box is approximately x=[-25.09,-24.99], y=[14.7,14.75], z=[3.6,4].
The exact original tree path, source certificate identity, leaf record and
box will be bound in a new selection record. No rounded display coordinate
is accepted as an input.

V6 consumes the immutable actual V5 report, independent report, owned
receipts and complete certificates. It does not rerun the V5 producer.
Existing V5 excluded leaves keep their original evidence. Every retained
leaf remains an explicit root for the new refinement. The full V5 forest
contains 1,537 retained leaves, of which 1,493 satisfy the original tiny-leaf
policy; these retain their entire exact nonzero volume. New bounds are
computed by subtracting only newly certified open-interior exclusions from
the old retained sum. The old closed root and cut-plane carriers remain.

The independent V6 checker may recheck the immutable V5 certificates with
the frozen independent V5 routines. This is verification of existing proof
bytes inside the new owned process, not a rerun or reinterpretation of the
previous experiment. Raw/public path remapping must preserve exact bytes
and SHA256 identities; it must not edit an archived report's old paths.

## Source primitive model and complete domains

Only the actual blocking faces listed above are eligible. Their complete
original face records, including every wire, occurrence, pcurve, orientation,
location and tolerance, are copied losslessly from the original registered
native inventory. Whole-material identities, original complete counts and
all sixteen frame/D bindings remain explicit. All other pieces are preserved.

An eligible plane uses its stored exact affine model

    x(u,v) = O + X*u + Y*v.

An eligible cylinder uses its stored exact parameter model

    x(u,v) = O + Z*v + r*(X*cos(u) + Y*sin(u)).

Exact identity face/wire/occurrence locations and positive cylinder radius
are required. The cylinder's U and V domains are the union hull of the
stored surface intervals and all actual Line pcurve endpoint ranges,
computed with exact rational first/last parameters. Unsupported pcurves
retain the old whole face. No U endpoint is replaced, no periodic seam is
discarded, and a slight original extension past 2*pi is preserved. No use
of a native isClosed flag or Common=0 establishes exact set semantics.

The inherited native/compiled realization premise stays unproved. V6 adds
no claim that a native curve evaluator is exact real trigonometry or that
the actual compiled geometry lies in the ideal primitive model. Its final
scope must keep native primitive/trim membership, compiled-error validation
and complete-factory G2 false.

## Exact rational trigonometric enclosure

Use exactly 64 closed equal-U parameter subintervals for each admitted
cylinder. Their union must equal the complete original U interval, with no
gaps and both original endpoints unchanged. Retain the full V domain on
each patch. This is not a Cartesian subdivision in three spatial axes.

For one U interval [a,b], choose the exact dyadic centre

    c = floor(2^16 * (a+b)/2) / 2^16,

and keep the exact offset interval d=[a-c,b-c]. The original endpoints are
not rounded. Require |c|<=8; otherwise retain the old whole face.

Let Ps and Pc be the 24-term Maclaurin polynomials for sin and cos, of
degrees 47 and 46 respectively. Both are also their order-47 Taylor
polynomials, since the missing odd cosine coefficient is zero. The explicit
Lagrange error is

    E = |c|^48 / 48!.

All values are rational. Consequently sin(c) lies in Ps +/- E and cos(c)
lies in Pc +/- E. This uses the global derivative bound |sin|,|cos|<=1.
It does not require a floating-point pi, argument reduction, a trigonometric
library, or a numerical sampled extremum.

For any rational A and B, enclose

    g(c+d) = A*cos(c+d) + B*sin(c+d)

by exact interval arithmetic on

    A*cos(c) + B*sin(c)
      + (-A*sin(c) + B*cos(c))*d
      + [-(|A|+|B|)*h^2/2, (|A|+|B|)*h^2/2],

where h=max(|a-c|,|b-c|). The last term follows from
|g''|<=|A|+|B| on the entire real line. The certificate records c, both
polynomials, E, d and the resulting ranges. The independent implementation
must reconstruct these from the source and use its own arithmetic order.

For each spatial coordinate k, use A=X_k and B=Y_k, then add O_k and
the exact Z_k*V interval and multiply the radial term by r. Intersect the
resulting closed axis box with the original stationary face box; add the
full original D afterwards. True empty intersections may be omitted only
with their parameter indices and exact empty-box evidence preserved.
Zero-width intersections and every closed parameter endpoint are retained.

## One additional support slab per eligible boundary piece

For a plane, n=X cross Y is an exact nonzero normal. Every point of its
parameter model satisfies n dot x = n dot O. Translation through the full
D yields the closed support interval n dot O + n dot D. Its old axis box
stays unchanged; the extra slab restores this affine correlation.

For a cylinder patch, set A=Pc(c), B=Ps(c) and construct a rational n such
that n dot X=A, n dot Y=B, n dot Z=0, using the exact inverse of the
stored primitive basis. Require a nonzero determinant. The same proven
g-range encloses n dot x after multiplication by r and addition of
n dot O and the complete n dot D interval. This radial slab preserves
sin/cos correlation on this patch; it does not assume the stored basis is
exactly orthonormal. The slab's normal and source dot identities are checked
independently. Every patch has at most this one additional slab.

The new cover element is its closed axis box intersected with the registered
closed slab, when present. Every modeled source face point remains covered.
All old 3D edge and vertex boxes remain unchanged, including terminal
extensions and seams. Whole-material exterior channels continue to extend
beyond the old known whole support box, so no new exterior-point premise is
introduced by a smaller boundary cover.

## Exterior-channel certificate and exact leaf refinement

For any nonzero normal n, the image of a nonempty open 3D box Q under
x -> n dot x is the open interval (l,u), where l and u are exact extrema
over its closed box. A closed support slab [a,b] cannot meet Q if b<=l
or a>=u. Axis separation is the same rule for coordinate normals.

An excluded open leaf therefore has one connected channel reaching the
known exterior, together with a successful axis or registered-slab
separation for every complete boundary piece. The original connected-open-
channel/complete-boundary theorem then applies. Failure of these registered
separators remains an unresolved overbound, never proof of real collision.

New trees retain the original exact positive directed volumes and closed
cut planes. Prefer existing new piece-box endpoints inside a cell. If none
exists, use exact midpoint bisection on the axis with the greatest actual
blocked-slab variation |n_k|*(cell_hi-cell_lo), preferring the registered
cylinder radial slabs when any is available; if no registered additional
slab is available, use the longest cell interval. A deterministic tie rule
uses the first axis. Every split is strictly internal, both child volumes
are positive, and their exact sum equals the parent. Pending, tiny and
budget-stopped leaves are retained in full.

## Hard capacity and measured sequence

The fixed input census is 48 planes and 16 cylinders, at most 1,024 angular
patches per full16 source reconstruction. Sequential producer and independent
verification phases may reconstruct the same fixed source again; 1,024 is
not a claim about the total number of patch calculations in the pipeline.
Each targeted KEY has one cylinder
replacement: its 460 old boundary pieces become at most 523. Each STOP has
one replacement: 116 become at most 179. Existing panel counts remain the
actual V5 counts, whose maximum was 1,590. Keep the 4,096-piece material cap.
Retain at most 4,096 new splits, depth 24, and 12,000,000 complete-piece
tests. Also cap actual elementary support inequalities at 12,000,000, so
adding a slab cannot silently enlarge the search budget. At most eight
registered separating inequalities exist per piece.

For all 1,537 retained V5 roots, the new forest has at most 9,729 nodes and
5,633 leaves. There is no unbounded grid or recursive parameter refinement.
Taylor degree, dyadic-centre precision and angular patch count are fixed.
The original TOL and tiny threshold TOL/100000 remain unchanged.

Actual V5 used 415,024 piece tests and 387 splits, with producer time
3.9882 s/RSS 142,389,248 B, independent time 3.5090 s/RSS 175,013,888 B,
and preflight time 2.8495 s/RSS 138,952,704 B. This is a runtime reference,
not a promise for V6 rational dot products. A single actual retained-leaf
proof and independent controls must complete first, followed by a measured
all16 source/capacity preflight before full refinement. The owned 600 s,
768 MiB, shared ceiling 7,301,444,403 B, disk floor 104,857,600 B, output
cap 41,943,040 B and metadata margin 4,194,304 B are unchanged.
There are five sequential owned stages. Each retains its own original
600-second gate; their combined allowed worker wall time is at most
3,000 seconds, before process startup, reporting and archival overhead.

Mandatory checks include the previous analytic exterior and split/leaf
controls, a new analytic all-retained/no-excluded positive control, and
actual source mutations of a domain endpoint, Taylor remainder, slab normal
or support bound, omitted patch/source piece, and full-D contribution.
Unavailable real-case mutation targets are explicitly N/A; analytic controls
are separate and mandatory. No V6 calculation or new control is claimed to
have run merely because its source or this basis has been written.
