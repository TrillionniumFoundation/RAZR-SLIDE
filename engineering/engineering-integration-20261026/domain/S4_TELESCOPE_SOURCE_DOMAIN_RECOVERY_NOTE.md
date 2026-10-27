# Recovered source telescope domain: scope and proof

This is a new derivation after the transient local runtime was lost. The four original S4 source files and the official CPython 3.12.14 summation source were fetched from fixed public revisions and matched the previously pinned SHA-256 values. The unpublished earlier reports and scripts were unavailable; their earlier hashes remain historical references. The new report carries its own source digest and recomputation timestamp.

No CAD module or physical prototype was run. The fourteen examples execute only the exact scalar guard AST extracted from the original source. The two vertex methods use exact rational arithmetic.

## Three contracts must remain distinct

1. `cam_coupling.stage_allocation` accepts the individual joint interval `[float(0.1-1e-9), float(2.9+1e-9)]`, and tests the original expression `abs(sum(q)-3*STAGE_MIN-p['B_Z_mm']) <= 1e-8`.
2. `product_nominal_motion.telescope_domain` constructs an ideal decimal fixed-sum polytope. Its allocator reconstructs the third joint as `nominal-first-second`; the allocator tests individual limits with `1e-9` and has no separate `1e-8` sum predicate. Its comment does not establish the tolerance used by the full factory.
3. The explicit full-factory input goes through `product_scene → native_scene → cam.prototype`. The supplied left and right three-joint arrays are preserved. The first scalar test uses `abs(sum(values)-8.5+descent_mm) <= 1e-7`; the later prototype uses `abs(sum(j)-.3-(8.2-d)) <= 1e-7`. Both test individual joint limits with `1e-7`. The standalone stricter helper is not applied to these explicit arrays.

The original operation order matters. At d=1 and j=[2.5,2.5,2.500000099999999], the native scalar residual is approximately 9.99999993922529e-8 while the prototype residual is 1.0000000028043132e-7: the first predicate passes and the second rejects. At j3=2.4999998999999997 the first predicate rejects while the later expression, if evaluated, would pass. Both examples are reproduced from the original AST. They are not new native factory witnesses.

## Conservative binary64 outer bound

Let each joint and descent be interpreted as the exact real value represented by its binary64 input. Let E=2^-48 mm. Under the accepted individual bounds and d∈[0,float(8.2)], every arithmetic intermediate relevant here has magnitude below 32.

For the three-float CPython 3.12.14 compensated sum, the first conversion is exact. The two running additions accumulate at most 2E error. In each Neumaier correction term, the running-addition error and two additional rounded operations give magnitude at most 3E. Two updates of the correction accumulate at most 8E. Its final addition contributes at most E, so the deliberately conservative total summation-error bound is 11E.

The native residual subtracts 8.5 and then adds d, giving at most 13E total arithmetic error relative to the exact real sum. Therefore every scalar input admitted by the first source guard lies strictly inside the closed outer band

`abs(d + jS1 + jS2 + jS3 - 17/2) <= H`, independently for S=L,R,

where `H = Fraction.from_float(1e-7) + 14*2^-48`, approximately 1.000000497379915e-7 mm. The extra E preserves a strict margin. The later prototype and any other native construction requirement can only reduce this admitted set.

The joint bounds are the exact binary64 values of `0.1-1e-7` and `2.9+1e-7`; replacing them with rounded decimal surrogates is unnecessary. For a prefix of m joints, an exact real outer interval is

`max(m*lo,17/2-d-H-(3-m)*hi) <= prefix <= min(m*hi,17/2-d+H-(3-m)*lo)`.

For source placement `0.7+sum(prefix)`, retain the binary64 constant 0.7 and an additional 13E bound for summation, the final addition and a strict outward margin.

## Two exact vertex calculations

The scalar outer has variables (d,jL1,jL2,jL3,jR1,jR2,jR3), 18 halfspaces and continuous relaxation dimension 7.

Method A enumerates all possible independent active-normal sets. Of C(18,7)=31,824 sets, 27,216 contain opposite dependent normals. The remaining 4,608 are represented by choosing seven of nine normal directions and one of two bounds for each. Exactly 1,536 are singular; 468 feasible active-basis occurrences give 216 unique vertices.

Method B independently obtains all critical shared-d levels where a clipped side-cube plane meets a cube corner, together with the two descent endpoints. It forms the clipped side-cube vertices from cube corners and edge/plane intersections, combines left and right slices, and keeps full-rank vertices using fraction-free integer elimination. The exact vertex sets from both methods are equal.

The six layers have 36, 27, 45, 45, 27 and 36 vertices, at d approximately 0, 2.5999997999999507, 2.6000000000000503, 5.399999999999951, 5.40000020000005 and float(8.2).

A separate ideal decimal, zero-width control reproduces the earlier 28 vertices with layers 9/9/9/1. Those 28 points describe that ideal projection. They do not enumerate the full factory's nonzero binary64 tolerance bands.

## Geometry and physical limits

The complete independent SLIDE and SEATING control relaxations each retain 15 coordinates: one phase coordinate, two tabs, two flanks, two KEY offsets, two crosshead offsets, and six independent joints. The ideal fixed-sum formulation removes two of these degrees of freedom. A binary64 accepted-input set is discrete; the stated dimensions refer to continuous relaxations.

The 216 rational outer vertices are not automatically native-admissible witnesses. Their convex hull is a conservative scalar outer domain, not an established physical travel domain. Whole rigid-material pair proofs must preserve shared-control correlations over this domain; a union of vertex snapshots does not cover swept intermediate material. Flexible OLED/FPC and varying SPRING material require their own complete source-family envelopes.

K3FULL's ten finite states remain valid as individually checked native states. Their pass does not certify this expanded independent domain, global wall thickness, strength, manufacture or G3–G5.

## Replay

Use CPython 3.12.14. Fetch or verify only the pinned public text dependencies, then execute the pure analysis:

```sh
python3 -B recover_domain_sources.py --root .
python3 -B rebuild_telescope_binary64_domain.py --root .
```

The source downloader never imports the downloaded code. The analysis compiles only selected scalar guard expressions and performs rational enumeration. It intentionally refuses a different Python version or binary64 precision for the source-order examples.
