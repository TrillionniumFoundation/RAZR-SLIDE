# Bounded diagnosis of the actual V9 remaining planar blockers

## Original result retained

V9's producer and mathematical checker both completed their worker reports.
They agree on an exactly zero retained upper bound and zero saved new
planar `u` proofs for the selected V6 root 76/node 47. Both added original
Line-plane models were accepted. The independent owned supervisor failed
while reading `VmRSS` during process exit. The driver therefore stopped
before its first-`u` gate; the later three stages never started. This
diagnostic binds that failed supervisor and cannot reclassify it as a pass.

The V9 certificate has 163 nodes: 81 split nodes with saved complete failed
channel prefixes and 82 excluded leaves. Failed prefixes preceding the
successful leaf channels are not present in those 82 leaf records. The
census below covers the 81 actually saved prefixes; it does not claim to
recover missing observations for all 163 nodes.

## Geometric question

The original UV target is obtained by applying the plane's exact left
inverse to every point of a stationary 3D candidate box. Off-plane corners
can enlarge that UV rectangle. The next diagnostic asks whether the true
affine-plane preimage is smaller for the actual unresolved plane attempts
at the first saved root split, node 0.

Keep the original closed stationary candidate

`B = (C - D) intersect original_stationary_face_box`,

including every original component and endpoint of D. For the original
affine plane `P(u,v) = O + X*u + Y*v`, a possible face point in B must obey
all six closed inequalities

`B_lo[k] <= O[k] + X[k]*u + Y[k]*v <= B_hi[k]`.

The existing known UV rectangle R contains the modeled bounded face under
the unchanged explicit realization-class premise. Intersect R with those
six affine halfplanes. This retains every possible modeled face point
whose displacement can meet the original spatial channel. No floating
tolerance, sampled membership, discarded D component, or changed carrier
is introduced.

## Two exact constructions

The first implementation starts with R's closed rectangle and clips its
boundary successively against the six closed affine halfplanes. Crossing
edges use exact rational interpolation; points on an inequality are inside.
A closed point or segment remains nonempty. No test on positive polygon
area is used to discard a set.

The second implementation enumerates every pair of the at most ten
constraint boundary lines, solves each nonsingular 2-by-2 system exactly,
and retains candidates satisfying every original inequality. There are
at most 45 pairs. R makes the feasible set bounded. Any nonempty bounded
polyhedron in two dimensions, including a closed segment or point, has
an extreme point defined by independent active constraints. Thus an empty
feasible-vertex set diagnoses an empty preimage; otherwise the component
minima and maxima enclose the entire feasible set. The independently
computed empty/nonempty result and exact hull must agree with clipping.

For a nonempty new hull, check that every endpoint lies inside the old
inverse-box target. Try the same four original closed UV exterior paths
against every member of the complete original UV boundary cover, with
the same strict coordinate or registered support inequalities. These are
new local plane probes, explicitly recorded as such. They do not establish
that all later pieces of a whole-material channel are separated.

An empty preimage is separately recorded as an exact affine-plane
diagnostic. It is not silently turned into an old UV proof, a physical
clearance pass, or an owned qualification.

## Finite registered scope

The full census reads exactly the saved 81 failed-prefix nodes and their
972 spatial-channel rows. New geometric probes are restricted in advance
to actual failed planar attempts at node 0; at most twelve spatial
channels are eligible. Each uses at most ten affine halfplanes and 45
line-pair intersections. The four original UV paths use at most 225 pieces
per face, giving at most `12 * 4 * 225 = 10800` new UV-piece tests.

The diagnostic caps the combined clipping endpoint, vertex feasibility,
and UV support inequality counters at 100000. Identity, source-census,
and exact algebraic consistency assertions are separate bounded checks.
This is a diagnostic limit, not a change to the original formal
12000000-predicate, 4096-split, depth-24, 600-second / 768-MiB worker limits.
No new whole-material refinement or all-sixteen run is performed.

The source consumes the original reports, saved certificates, failed
controller and frozen source projections. No producer or helper is
imported. Complete model face hashes and original O/X/Y values are checked
against the frozen original source records. All source and input bytes
must remain unchanged afterward.

Five explicitly synthetic diagnostic controls cover a full rectangle,
a closed segment, a closed point, an empty intersection, and a positive
strip of width `1/2^80`. Both exact constructions must agree. These are
separate from the actual saved V9 cases and do not qualify a real sample.

The registered execution budget is 60 seconds and 536870912 bytes of
address space, with at most 67108864 decoded bytes per input and 8388608
output bytes. An actual diagnostic failure remains a separate result.
Native bounded-face membership, full continuous G2, FE, and physical
acceptance remain unverified.
