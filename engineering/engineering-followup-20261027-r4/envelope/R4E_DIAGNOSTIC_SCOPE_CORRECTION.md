# R4E diagnostic scope correction: one Euclidean uncertainty ball

This clarification applies to the frozen V2/V3 executed sources and all of their existing numbers. It does not change any mathematical result, threshold, actual failure, or original geometry.

The common declared diagnostic model is a Euclidean `L2` ball of radius `epsilon` for each material, where `epsilon` is that material's maximum stored face/edge/vertex tolerance. The whole support method expands support in direction `n` by `epsilon * ||n||2`.

The slab method encloses the same Euclidean ball by the coordinate cube `[-epsilon, epsilon]^3`. Its boundary-piece boxes are consequently expanded by `epsilon` in each coordinate. This coordinate cube is an outer approximation used by the slab method. Taking the smaller of the independently valid whole-support bound and slab bound is conservative for the common **L2 ball** model.

The minimum must not be interpreted as a bound for every independent coordinate perturbation in the full `L-infinity` cube. For example, in direction `(1, 1, 0)`, the cube has support `2 * epsilon`, while the Euclidean ball has support `sqrt(2) * epsilon`. The old whole-support calculation therefore does not qualify the larger cube model. No new L-infinity qualification is claimed or inferred from the all-fail diagnostic results.

The earlier proof document's phrase "expands each material boundary piece ... in each coordinate" describes the slab outer approximation. It does not define an alternative common perturbation model for the minimum of the two methods.

All raw exact-real bounds are unaffected. Neither the L2 model nor its slab cube outer approximation is a proved native BREP classification or compiled transform error bound. Those semantic and implementation premises remain open.
