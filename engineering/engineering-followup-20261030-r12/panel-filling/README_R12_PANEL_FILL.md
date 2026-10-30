# R12 current whole panel / swept KEY: complete boundary filling and exact residual ledger

## Result and stopping point

This package derives and independently checks a conservative full-material intersection bound for each current whole KEY translated through `q in [0,12]` against the current whole `A_BACK_PANEL`, under the explicitly stated complete represented-boundary / compact-filling model. It retains every positive contribution, including very small ones.

The sequence of upper bounds, separately for each side, is:

| Carrier method | Exact rational volume, displayed approximately in mm3 | Original float64 `1e-7` criterion |
| --- | ---: | --- |
| Complete Z-fibre filling | 3.1720800000000042 | Not met |
| Intersection of complete X-, Y-, and Z-fibre fillings | 1.0020000000000029 | Not met |
| Above, with complete two-segment exterior-channel certificates for the diagonal KEY overfill | 0.9600000000000029 | Not met |

All exact rational values are in the reports and compressed ledgers. The positive upper bound is **inconclusive**, not an actual collision or a lower bound. This package does not qualify the native material-set identity, uniformly bound compiled/native evaluation errors, prove the complete current 15-parameter allowable domain, or pass continuous G2. Those fields stay false.

The final bounded trim investigation found the precise remaining obstruction: six guide end faces, indices `104,109,110,115,118,121`, whose full UV rectangles contain their rectangular inner holes. Their 12 native wires are marked closed, but the exact serialized pcurve endpoints have 44 nonzero joins out of 48. No endpoint snapping or presumed trimmed-face filling rule is admitted. The positive full-box residual remains in the authoritative ledger. The investigation ends here.

## Inputs and material identity

`inputs/A_BACK_PANEL.brep`, `inputs/L_KEY.brep`, and `inputs/R_KEY.brep` are byte-preserving copies of the current source-bound K3 panel and K1 whole KEY inputs supplied by the geometry role. `inputs/manifest.json` identifies the initial five copied inputs; the final delivery manifest covers every later support module and artifact as well. The panel is fixed. Both KEY bodies receive the full independent translation vector `(0,12,0)`; this is an entire sweep, not a collection of poses.

`native-boundaries-attempt4/report.json` freshly reads all three original BREP files with OCP. Each is one valid native solid with positive signed volume. The census is complete:

| Body | Planes | Cylinders | All faces | Pcurve edge occurrences |
| --- | ---: | ---: | ---: | --- |
| A_BACK_PANEL | 230 | 68 | 298 | 1336 LINE + 136 CIRCLE + 16 degree-1 BSPLINE |
| L_KEY | 80 | 12 | 92 | 504 LINE + 24 CIRCLE |
| R_KEY | 80 | 12 | 92 | 504 LINE + 24 CIRCLE |

Each complete face record retains native surface parameters, the reported UV domain, every complete trim pcurve occurrence (including opposite cylinder seam orientations), every complete 3-D edge curve, all vertices, exact support intervals, and the full translation interval. The 16 panel splines are nonrational, nonperiodic degree 1, with two poles; the helper explicitly includes all affine pieces and any terminal continuation. Equality between that declared continuation and an undocumented native extrapolator is not claimed. The KEY raw records are checked against the frozen geometry-role v6 census, with equal lengths and exact indexed parameter correspondence; only derived support intervals are excluded from that raw equality check.

The recorded SHA-256 of the complete native report is `47a48bd130b35a8251907a3ab9116c4a7d60c5dc04ed5a2ab0f3d474a9683502`. The copied geometry v6 report is `4cbf0efb172e576cd94f1846efe9764b14a328e98d4a599e6784984cf8c888cf`.

## Why the carrier includes material

Let `M` be a compact material set with its complete boundary contained in the finite union `U` of closed support boxes. For each coordinate axis, fill a line parallel to that axis from the minimum to the maximum coordinate at which that line intersects `U`. Call the result `H_axis(U)`. Then `M` is contained in every `H_axis(U)`.

For a material point, the positive and negative axis rays must eventually leave the bounded material set. Their last material points are boundary points on the same line, and therefore belong to `U`. The material point lies between them. This also covers hollow material: an internal cavity cannot justify leaving filled material unbounded. Taking the intersection of the three independently conservative fibre fillings remains conservative.

For every pose `q`, the complete translated boundary is inside the full swept box union `U_sweep`. Applying the same argument at each `q` gives `union_q M_q` inside the intersection of its three fibre fillings. Thus the whole swept material, including its initial filling, is covered. No separate unproved assertion that only a sampled boundary sweep covers the initial solid is used.

This theorem is exact under its stated complete-boundary premise. Native validity and positive volume are retained diagnostics; they do not by themselves prove the formal identity between OpenCascade's compiled material set and the serialized analytic representation. That bridge remains open.

## Complete cell accounting

`compute_fibre_intersection_r12.py` constructs the exact arrangement of all rational box endpoints and evaluates every positive-width 3-D cell. It does not sample the interiors to guess occupancy. Coordinate planes are retained in the closed carrier but contribute zero three-dimensional volume. No positive-width cell is discarded because it is small.

| Pair | Grid intervals | Every positive-width cell checked | Estimated streaming-array bytes |
| --- | --- | ---: | ---: |
| panel / L_KEY | 304 x 206 x 121 | 7,577,504 | 2,288,456 |
| panel / R_KEY | 301 x 213 x 123 | 7,885,899 | 2,351,748 |

The arithmetic uses `Fraction` for endpoints, widths and integrated volumes. Small integer arrays encode interval indices. X slices are streamed. The compressed ledgers retain the full coordinate grids, all indexed source boxes, every occupied row/run, the exact piece volumes and a SHA-256 of the complete packed occupancy mask. There are 73 positive compressed boxes on the left and 96 on the right in the XYZ ledger. These 169 boxes account for the entire positive upper bound, not a selected subset.

The geometry-role independent full-grid review uses a separate monotone-extension-union implementation, without importing the producer, and compares every cell, exact totals and all packed mask hashes for both Z-only and XYZ methods. Its source and report are retained under `independent-review/` in the sealed package. The original independent review report hash is `a40fd3d187a363200a61168f436b70f3c244d48a91f2b9c060d90bb863daf686`.

The independent exterior-ledger review recomputes all 482 faces in all five projection directions, covers all 169 positive boxes, and rejects five deliberately altered ledgers: a dropped positive box, a dropped boundary face, replacement of one face by a duplicate, reducing a retained positive upper bound by exactly `2^-80`, and a disconnected claimed path. It imports neither producer projection nor producer refinement functions. Its independent projection implementation shares the geometry role's exact outward-square-root primitive, whose rational squared-bound assertions are retained; independence of that primitive is not claimed. The separate pcurve review recomputes all 2,544 pcurve intervals and complete UV unions, then independently recomputes all 48 final trim endpoint joins. The maximum observed exact gap is `3/4503599627370496`, approximately 6.661338147750939e-16.

## Exact exterior channels

For a compact material set, any connected open tube that avoids its entire boundary and reaches a point outside its global support is in the exterior. This certifies a continuous void region, not a void inferred from sampled probes.

`projected_boundary_r12.py` derives support intervals for every complete face in the directions X, Y, Z, X+Y, and X-Y. These preserve the diagonal KEY's correlation that its axis-aligned rectangle loses. Every support includes its complete analytic surface rectangle/cylinder, all complete 3-D edge curves, all vertices and the full translation interval. Full conics are bounded with exact dyadic outward square roots, not floating point root initialization.

`refine_exterior_channels_r12.py` accounts for all 169 original positive boxes. The large diagonal contribution of approximately 0.042 mm3 on each side is excluded by two connected tubes: one extending toward Y=52, and one extending outward in X through Y=(52,53). Each segment explicitly excludes all 92 complete KEY face supports and reaches beyond the global KEY support. Two original compressed boxes per side are discharged. All 165 other boxes retain their full exact positive volume. No Common result supplies the bound.

The proposed panel +Y channel fails the full-support test. Its target X=(10.8,11.4), Z=(1.2,1.6) lies between guide walls, but the guide end-face UV rectangles fill the inner rectangular openings. Rather than assume these holes, `inspect_trim_frontier_r12.py` rereads all six blocking original BREP faces and walks all ordered native wires. It matches every ordered edge back to exactly one original face occurrence. The exact endpoint closure check fails in all twelve wires. This is the explicit remaining proof frontier. Native `Closed()` and vertex tolerances are recorded but are not substituted for a bound on the filled trimmed domain or its endpoint-connection paths.

The unchanged original limits are 4096 adaptive spatial splits, depth 24, and the original binary64 threshold. This method adds **zero** adaptive spatial splits, depth zero. The fixed full arrangement is separately budgeted before evaluation. No subdivision limit is silently enlarged.

## Capacity and real attempt history

The basis files were written before their associated executions. Every process is limited to one CPU and 805,306,368 bytes of address space (768 MiB); the arithmetic jobs have a 180-second cap and the final trim investigation a 60-second cap.

| Execution | Seconds | Peak RSS bytes | Result |
| --- | ---: | ---: | --- |
| Native attempt 1 | Outer 195-second timeout | Not reported | Real failure retained; no report/traceback |
| Native diagnostic attempt 2 | Outer 50-second timeout | Not reported | Last stage before import; no geometry started |
| Native attempt 3 | Outer 195-second timeout | Not reported | Last stage before import; no geometry started |
| Native attempt 4, OCP-only | 3.480116923 | 276,586,496 | All 482 complete faces recorded |
| Complete fibre arrangement | 0.841119828 | 41,906,176 | All cells and exact positive volumes recorded |
| Complete exterior-channel refinement | 0.936466995 | 34,381,824 | Four original boxes excluded; full remaining sum retained |
| Final ordered-wire investigation | 0.704482339 | 246,628,352 | Complete 6-face/48-edge census; exact closure not admitted |

Attempts 1–3 remain in this package with their executed source, progress/log information and interruption records. Their timeout cause has not been established beyond the available last-stage observations. No timeout is attributed to a square-root underflow without evidence. The OCP-only attempt completes under the same cap; it does not increase the resource allowance. The earlier square-root helper is retained alongside the separately supplied exact exponent-scaled helper used for attempt 4.

## Replay

Use Python with OCP 7.8.1.1 and NumPy available; no CadQuery import is needed by the successful native extractor. In the original environment the interpreter was `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python`. Run with `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. Each output directory must be new.

1. Run `extract_complete_boundaries_r12_v4.py --output NEW_NATIVE_OUTPUT` to reread all originals and rebuild the complete face records.
2. Run `compute_fibre_intersection_r12.py --native-report NEW_NATIVE_OUTPUT/report.json --output NEW_FIBRE_OUTPUT` for every exact grid cell.
3. Run `refine_exterior_channels_r12.py --native-report NEW_NATIVE_OUTPUT/report.json --coarse NEW_FIBRE_OUTPUT --output NEW_EXTERIOR_OUTPUT` for the complete positive-box ledger.
4. The frontier inspector is intentionally bound to the frozen attempt-1 exterior ledger and original BREP under this directory; run `inspect_trim_frontier_r12.py --output NEW_FRONTIER_OUTPUT` to reproduce the exact closure refusal.

Compressed-file byte hashes include gzip serialization metadata, so a fresh replay need not have the same compressed-file byte hash. Compare the exact records, volumes, face correspondence and packed complete-grid mask hashes, while retaining each run's own byte identities. The delivery manifest verifies the immutable archived files themselves.

The independent reviewer sources are preserved byte-identically with their original execution identities. They originally ran from `geometry_review/` beside `panel_fill_work/` and `geometry_work/`; the exact square-root source they read is also present here as `inputs/complete_surface_support_v3.py`. Their frozen reports contain original absolute evidence paths. To rerun those unchanged reviewer scripts, recreate that sibling layout and original referenced paths, or execute a separately recorded path-adapted copy. Do not silently edit the archived reviewed source or its claimed execution hash.

## Scope kept separate

This current whole-panel bound is additional to the nine original L1 local filling certificates in the separate `envelope_work` deliverable. It does not replace the original L1 counterexamples or native failures. It does not repair physical geometry, establish manufacturing wall thickness, define a supported multi-axis mechanical allowable domain, recover the original numerical qualification, authenticate OEM parts, or supply G3/G4/G5 measurements. Its useful advance is the complete, non-sampled filling argument, exact full-domain carrier accounting, a rigorous correlated exterior-channel reduction, and a precise finite stopping point for the remaining trim-domain proof.
