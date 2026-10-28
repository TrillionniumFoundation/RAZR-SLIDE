# R4E complete-material continuous enclosure results

## Executed conclusion

The complete original tiny-frame method now has an independent exact-real whole-material bound for all 16 saved frames. Four SPRING/STOP frames satisfy the unchanged original float64 `1e-7 mm³` clearance threshold without assuming that the native base `Common = 0` is mathematically sound. Twelve KEY-related frames retain spatial overbounds too coarse to satisfy that threshold.

The separate original `min(original volume) + TOL` guard is satisfied by **16/16** final V4 bounds, up from **4/16** under V2 whole support. This guard is not the clearance gate. The final counts are:

| Original criterion | V2 whole support | V4 exact slab union |
|---|---:|---:|
| `min(original volume) + TOL` | 4/16 | 16/16 |
| Clearance `1e-7 mm³` | 4/16 | 4/16 |
| Declared L2-ball uncertainty diagnostic at stored maximum entity tolerance | 0/16 | 0/16 |

All results remain conditional on complete stored parameterizations enclosing the intended compact material boundary. Native tolerance-based BREP material semantics, compiled curve and transformation error bounds, source-to-binary correspondence, the current complete factory, and overall continuous G2 remain unproved. No finite kernel empty result has been promoted to an exact real set theorem.

## Entire materials and independent verification

The old R3E supplement covered 44 moving-side BSpline pcurves. Whole-material bounds additionally required 44 occurrences on eight fixed-side original inputs. The unchanged archived extractor, complete boundary inventory and extension sources were used with the freshly qualified pinned runtime. Every new complete baseline inventory matched its original canonical inventory exactly. A separate reader process reproduced all 44 full records exactly.

The successful second producer and reader both passed their original owned native supervisors and the runtime's full before/after 8,112 payload and 43 RECORD checks. The first producer worker also completed, but its old supervisor encountered a real terminal `/proc` RSS sampling exception. That controller remains failed; its worker success was not substituted for supervised success.

The final independent mathematical verifier imports neither the producer nor native CAD. It reconstructs complete face, edge and vertex supports from the original inventories and actual 88 pcurves, using an independently implemented integer-bisection radical enclosure. It verifies all original remaining displacement intervals, the exact carrier bounds, topology and directed volume, every fine-slab to merged-run union, and all final intersection cells in an independent X/Y/Z enumeration order. It completed all 16 frames, covering 32 original whole-material records and 116 complete source support records.

V4 completed in 111.142 seconds with 255,623,168 bytes peak worker RSS. Its supervisor completed in 111.357 seconds without a resource stop. Independent V4 verification completed in 55.011 seconds; its supervisor completed in 55.440 seconds. The inherited 600 second / 768 MiB pure-math limits and original native resource limits were retained.

## Tightening achieved

Both original frames and both left/right variants are retained in each row below. Rounded values are displays; exact rational results remain in the proofs.

| Original saved pair family | Frames | V2 whole support upper bound, mm³ | V4 upper bound, mm³ | Original clearance result |
|---|---:|---:|---:|---|
| Back panel / KEY | 4 | about 5,020.19824 | about 18.648 | Unresolved: bound too coarse |
| KEY / STOP 0 | 4 | about 34.21425 | about 1.429134679 | Unresolved: bound too coarse |
| KEY / STOP 1 | 4 | about 18.732 | about 0.795467495 | Unresolved: bound too coarse |
| SPRING OD tolerance envelope / STOP 1 | 4 | `3.006e-15` to `6.290e-15` | same controlling whole-support bounds | Conditional exact-real pass |

These are conservative upper bounds. A bound above the clearance threshold does **not** establish actual material interference.

## Preserved failures and the capacity change

V1 genuinely produced the first coarse 5,020.19824 mm³ bound, then failed on the newly needed fixed-side BSpline parameters. V2 completed the additional input coverage and preserved all 12 coarse whole-support clearance failures.

V3's uncompressed slab enumeration reached the unchanged 600 second wall limit. Its owned supervisor stopped the worker with exit `-15`; `completed` remains false. The first raw slab bound was computed, but the first inflated cover did not complete. That partial result is retained separately. Its exact first raw rational value equals the completed V4 first raw value.

Before V4, a capacity preflight actually processed all 16 frames and all three covers per frame. The finite pair/triple enumeration upper bound decreased from 149,710,667 to 295,804 after exact merging of adjacent boxes whose transverse intervals are identical. The worst individual cover fell to 30,276 checks. The preflight completed in 55.860 seconds with 178,671,616 bytes peak RSS.

V4 preserves every fine boundary cut plane and merges only exact unions of adjacent positive boxes. No original surface, trim loop, curved portion, tolerance gap or material is removed. Each resulting positive cell is a positive-diagonal affine image of an exactly checked outward unit cube; closure, orientation and directed volume follow from that injective map. This avoids reconstructing and integrating twelve equivalent-topology triangles for every rational cell. The new per-cover enumeration limit is 40,000; the original process time and memory limits are unchanged.

## Why smaller time steps alone do not address the remaining 12

The original displacements are already tiny: Y intervals have width `2^-51 mm`, and the affected X intervals have width `2^-50 mm`. A bounded read of the completed proofs recovered the stationary boundary boxes by subtracting those exact interval endpoints. It then exhibited a positive cell of the **stationary spatial enclosure** for each of the 12 unresolved frames:

| Family | A single retained zero-displacement enclosure cell, mm³ |
|---|---:|
| Back panel / KEY, both sides and frames | about 0.308578644 |
| Left KEY / STOP, both STOP types and frames | about 0.0176 |
| Right KEY / STOP, both STOP types and frames | about 0.017207674 |

Every such cell exceeds `1e-7 mm³`. The stationary minimum among the existing whole-support candidates also remains above the threshold. Therefore dividing the displacement interval more finely while keeping these spatial predicates cannot qualify the subinterval that contains zero displacement. These are witnesses of enclosure overcoverage, **not penetration witnesses**. This diagnostic read completed in 3.751 seconds and did not perform a new native operation or a new full-domain run.

The original panel has 278 faces, including 38 faces with multiple trim wires and up to 31 wires on one face. Each KEY has 80 faces, including four faces with multiple trim wires. The producer conservatively replaces a trimmed plane face by its full UV rectangle, a circular/cylindrical portion by full-period radial support, and a material section by its transverse coordinate hull. These relaxations preserve all geometry but discard trim and occupancy correlations. Complete face counts and source identities are retained in the source-feature context record; no unverified assertion that a particular cell is physically occupied is made.

## Minimum justified next strategy

The next spatial refinement should start from the saved positive stationary cell and its complete active boundary-piece lists. It should certify the complete trimmed face domain, including every loop, seam, pole and actual terminal BSpline extension, or provide an independently certified inner-void exclusion from an exact source CSG model. Curved parameter patches need directed trigonometric/affine bounds over their actual trimmed intervals. A vertex hull or unconstrained tessellation cannot replace those surfaces.

A local patch or inner-void certificate must first eliminate one saved stationary overcoverage cell while preserving complete boundary containment, valid topology and signed volume. Its event count, trim complexity, directed arithmetic work and memory requirement must then be measured before a further full 16-frame run. No V5 experiment or new full-domain qualification is claimed here.

The tolerance diagnostic is an independent unresolved qualification issue. Even the four raw SPRING passes have bounds near `1.4792007e-7 mm³` in the declared L2-ball model, above the original threshold. Those failed upper bounds do not prove physical interference, and stored native tolerances have not themselves been proved to bound native classification or compiled errors. Spatial tightening, native material semantics and compiled-error certification therefore remain separate tasks.

## Supervisor and scope corrections

The old pure-math supervisor's direct `/proc/Popen.pid` sampling could substitute zero for missing RSS in a PID namespace. Its original V1 receipt is preserved without retrospective requalification. The new owned supervisor binds the worker source, nonce, namespace PID chain and process identity; missing RSS on a still-running worker is an explicit failure.

Independent source review found two entry binding defects: failure to bind actual worker `--contract`/`--output` to the supervised values, and later argparse abbreviation overriding a checked complete option. Every source version and the actual counterexample are retained. The current canonical entry requires the complete registered option schema, rejects abbreviated, equals-form, extra and duplicate options, reconstructs argv, and verifies the contract digest and resolved output directory. Targeted wrong-hash, wrong-output, abbreviation and duplicate-option controls were rejected before mathematical work. The actual earlier V2/V3 invocations were independently verified to have the correct bindings; they were not rerun merely for the entry repair.

The diagnostic common model is an L2 ball. The slab coordinate cube is only an outer approximation of that ball. Taking the minimum with the whole-support L2 result must not be described as certifying the full L-infinity cube. The separate scope correction preserves all old source bytes and numbers.

Original R3E's 17 saved cases, 25 native abnormal events and 28 conditional method checks remain archived and unchanged. None is relabeled by these new results.
