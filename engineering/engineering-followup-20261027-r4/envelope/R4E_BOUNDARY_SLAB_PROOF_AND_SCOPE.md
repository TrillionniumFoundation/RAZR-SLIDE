# R4E complete boundary slab enclosure: theorem and limits

## Purpose

The R3E tiny displacement method needed the original native base `Common = 0` as an assumption. R4E instead encloses the entire intersection of the two compact materials, including the complete remaining displacement box. It performs no native Boolean. The original float64 threshold `1e-7 mm³`, the original `min(volume) + TOL` upper gate, all 16 original frames, and every original displacement interval remain unchanged.

The first whole support strategy has a genuine overbound failure: the first panel/KEY frame has a bound near `5020.19824 mm³`. V1 then stops on the previously unnecessary fixed-side BSpline pcurve parameters. These events remain recorded as actual failures. V2 completes the additional fixed-side parameters and repeats the whole support method across all original frames. V3 adds the slab enclosure below; it does not remove either V1 event or V2 coarse bounds.

## Exact compact-section lemma

Let `S` be a compact subset of three dimensional Euclidean space. Fix a coordinate `k` and a value `t`. The section `S_t = S ∩ {x_k = t}` is a compact subset of a two dimensional affine plane.

Every relative boundary point of `S_t` belongs to the ambient boundary of `S`. Indeed, an ambient interior point of `S` has a ball lying in `S`; intersecting the ball with the plane makes the point a relative interior point of `S_t`.

For each transverse linear coordinate, its maximum and minimum over a nonempty compact `S_t` occur on the relative boundary. If a maximizer were relative interior, moving a sufficiently small distance in the increasing coordinate direction would remain in `S_t` and contradict maximality. The argument also covers sections with empty relative interior, because every point of such a section is a relative boundary point. Thus transverse extrema of the section are bounded by the complete ambient boundary on that plane. No convexity, connectedness, face orientation, or Boolean result is required.

Suppose a finite collection of closed axis boxes contains the complete boundary of `S`. Partition coordinate `k` at all box endpoint coordinates and at the finite pair-domain endpoints. For an open slab between consecutive cut values, every boundary box meeting a section at an interior `t` appears among the boxes whose coordinate interval overlaps that open slab. The componentwise extrema of all these boxes therefore bound the entire material section. If no boundary box is active, that section is empty. The same conclusion holds independently for each of the two materials; intersecting the two resulting outer boxes remains conservative.

Cut planes are explicitly retained as closed carriers over the global transverse domain. A boundary box supported on a cut plane must not be treated as a positive-width box, and the cut plane must not be discarded from the set enclosure. Finitely many such planes have zero three dimensional measure, which is the only reason they contribute zero volume.

## Entire remaining displacement box

For compact `S` and compact displacement set `D`, the Minkowski sum `S + D` is compact. If `y` is a boundary point of this sum, choose a representation `y = s + d`. The point `s` cannot be interior to `S`: otherwise a ball around `s` in `S`, translated by `d`, would put a ball around `y` inside the sum. Therefore `boundary(S + D) ⊆ boundary(S) + D`.

Each stored boundary piece box is added to the entire original exact displacement box by interval addition. Those boxes contain the complete swept boundary under the stated material-boundary premise. This includes every original later X interval and both signs of the tiny Y intervals. Neither a rounded endpoint nor a zero displacement replaces the actual interval.

## Combining the three coordinate coverings

The X, Y and Z slab constructions independently enclose the entire material intersection. Their intersection is again an outer enclosure. Every positive cell is indexed by exactly one X interval, one Y interval and one Z interval. Distinct index triples differ along at least one partition coordinate, so the corresponding open cell interiors are disjoint. Exact positive volumes therefore add. The common partition boundary planes remain retained and have zero volume.

Each positive cell is a closed exact rational box with 8 vertices, 6 outward quadrilateral faces and 12 outward triangles. The implementation checks opposite oriented edge incidences, the Euler identity, and the positive divergence volume against the exact interval product. The union can be disconnected; no false claim that it is one native solid is made.

## Complete boundary boxes

Every original face, three dimensional edge and vertex is included. Plane faces use their full stored UV bounds enlarged by every complete pcurve range. Circle edges and cylinder faces use complete radial support with directed rational square-root bounds; seam vertices are never used as a replacement for curved geometry. Nonorthogonal stored frame vectors and their actual tiny components are retained.

The original two-pole, degree-one, nonperiodic, nonrational BSpline class uses its exact source-level affine terminal extension at the actual trim endpoints, including the original overshoots. It is not clamped to its knot interval. R4E independently extracts and reads back the 44 additional fixed-side pcurve occurrences needed to extend the old moving-side coverage to both entire materials.

## Remaining semantic premises

This is an exact-real set argument conditional on each intended compact material having its complete boundary inside the stored complete parameterizations. The old native shell closure flag and successful native material guards do not prove that premise for tolerance-based BREP solids with mismatched seams.

The source-level affine extension and circle/cylinder parameterizations are not a proof of the installed compiled kernel's floating point behavior. The source-to-binary correspondence and a uniform compiled evaluation/transform error bound remain unresolved. Whole-basis exact support and the slab method do not infer those facts from the repeated inventory or from another `Common` call.

A second, separately labeled diagnostic expands each material boundary piece by its maximum stored face/edge/vertex tolerance in each coordinate. This is a declared uncertainty model. It does not prove that native classification lies within that model. Raw and expanded bounds and their original-threshold classifications are retained separately.

## Capacity and negative controls

The implementation uses only standard-library exact rational arithmetic. Its finite work is bounded by the complete boundary-piece counts, all endpoint cuts, and an explicitly registered maximum box-intersection count per covering. The process remains under the inherited pure-math 600 second / 768 MiB RSS / shared-memory / disk / output gates. A capacity rejection is retained as a real unresolved computation rather than silently dropping boxes or coarsening the original geometry.

Known controls include two disconnected unit boxes whose whole convex hull overlaps a middle box, their positive whole-self intersection, retained touching planes of zero volume, and two nonzero `2^-51` overlap strips. In addition, each original moving material is enclosed against itself at zero displacement; that bound must reject clearance under the same original `1e-7` gate.

Execution and verification receipts, rather than this mathematical description, determine which original cases have actually run and passed. No result from this document alone changes strict native continuous G2 or the overall blocker ledger to true.
