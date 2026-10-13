# RAZR SLIDE R53 — Native datum screening and research-collision localization

**Manufacturing: NO-GO (`manufacturing_go=false`).** This increment is a **replayable negative engineering gate**. It does not manufacture an FPC, obtain Motorola/OLED OEM design permission, certify USB/data, or establish a physical two-battery power path. All dimensions below refer to inherited research-coordinate models, not original Motorola production parts.

## Nonnegotiable concept

Two equal **finished-exterior** functional modules A/B, B rises 79.75 mm in Y and then docks 8.2 mm in Z, single flexible ~7-inch OLED, no separate outer display, A prioritizes battery. 4700 mAh remains a target, not a verified battery. USB must remain continuously wired by physical conductors through STOW, travel, reversals, docking, and OPEN; a dock-only, wireless or buffered bridge **does not** satisfy the requirement.

## Frozen provenance and independent replay

- R50 original (41 ZIP members): SHA256 `86f226f9bce3a3f0659737327c7cc32415eed3b9be3f96f35a746ac32844dfd6`.
- R51 original (47 ZIP members): SHA256 `3b31d2f3c3ae869a35953dd7d183e1ade05f5aa0c3c1ca1ae7ac5295a098dbb5`.
- R52 original (35 ZIP members): SHA256 `ba0731232b3edaf67cc40a6bf5e29707660ec96c6692db00d74e1e377ff68dcc`.

All original ZIP SHA256 and ZIP CRC checks passed. **No source archive was edited.** An isolated R52 extraction (`replay_R52`) ran the original `R52_RUN_REPRODUCE.py --r50 <frozen R50.zip>`, returned **exit code 0**, and freshly executed R47=40, R48=48, R49=27, R50=23, R51-collision=14, R51-native=5, R52=40: **197/197 passed**. This includes negative assertions.

R53 has **30/30** separate freshly executed tests: tampered local/world XYZ sign, swapped or missing witness, duplicate positive event, nonpositive volume, unapproved STEP, symlink/traversal, unit scaling, mirroring, wrong fiducials, absent OEM files, and an importable **synthetic STEP that must not establish vendor provenance or release**. Overall **227 research-level assertions across two suites**; this is not 227 different physical qualifications.

## Quantitative B/A frame bloodline and priority

R52's 7 route families × 9 sampled poses were not reinterpreted as continuous motion. R53 independently recomputed for **all 220 positive body/segment witness records**:

- Fixed A frame: `A_local = A_research_world`.
- Moving B frame: `B_local=(x_world,y_world-s,z_world-q+8.2)`.
- XYZ finite, bounding box extrema ordered, positive intersection volume bounded by reported box, unique `(route,pose,body,segment)`, B collisions for every route/pose, and exactly 7 × 9 pose coverage. Round-trip tolerance: **2×10⁻⁵ mm**, to accommodate R52's serialized decimals, not a manufacturing GD&T.

| Research collision group | Positive witness route-poses | Envelope of witness **bounding boxes** in its own research frame (mm) |
|---|---:|---|
| B-local, A endpoint Z transition leg | 63/63 | (3.39172,14.50,3.89113) to (24.10755,82.71630,7.20) |
| B-local, rolling U loop | 63/63 | (3.39174,42.35471,3.88955) to (36.99500,93.34503,7.20) |
| B-local, B endpoint Z transition leg | 45/63 | (33.39178,18.06877,3.88960) to (35.60787,82.69680,7.20) |
| Fixed A research frame, A endpoint Z transition leg | 49/63 | (3.39172,70.06499,0) to (24.10756,79.75,5.60) |

B has 63/63 positive route-pose body clashes, A 49/63, in **this frozen research family only**. The segment labels are **not separately manufactured components**. Rectangular overapproximation with 1mm-cell rounding covers 6,782 research-B and 540 research-A XYZ cells; these are **not volumes of material to remove**. The sample peak B overapproximation covers 45 route-poses in one cell (e.g. B-local voxel origin [34,21,4] mm). Repeated boxes, states and routes substantially overlap, and their volume sums are not additive unique material. Neither cell heatmaps nor the four min/max boxes grant any OEM machining/laser/cut license.

The inherited R50 finite ribbon is **W1.2×t0.2mm, 109 nodes/108 ruled lofts per studied path**, not OEM FPC. The 220 R52 positive witness segments cover **nine snapshots**. No claim that 7 routes span all conceivable 3D topologies; no full continuous 79.75+8.2 motion sweep with actual valid material, no 300k dynamic specimen.

## R53 supplier native geometry preflight

New `src/r53_native_alignment_preflight.py` consumes controlled manifest+quarantined STEP and **four or more independent CAD fiducial pairs**. It rejects non-rigid matrices, mirror/scale, missing units, duplicate/collinear anchors and mismatches exceeding **0.02mm synthetic screening tolerance**. A parsable STEP is inspected by OpenCascade as a numerical solid (solids count and local bbox), but **manufacturer provenance, authenticated OEM coordinate system, authorized cut regions and all safety sign-offs remain permanently false in this software stage**, even with perfect synthetic documents.

**Actual receipt: 0/12 OEM/FPC/USB/electrical/mechanical/OLED source classes.** No OEM registration, no authorized modification. The two official Hirose BM28 header+mate product pages advertise STEP downloads, but a direct download attempt from the connected Linux host returned **HTTP 403** (21-byte response, not ZIP); no genuine Hirose STEP was imported or included. The header/mate remain research proxies. Site catalogue cites 20Gbps *connector capability*, 24 positions, and only **10 mating cycles**; none proves a functioning complete USB path or 300,000 motion cycles. Supplier-specific current ratings are pin-dependent: do not convert one catalogue number into a whole-device battery supply rating.

## Hard release blockers, individually required

1. **M mechanical:** 36/64 original combined unsafe unlock scenarios; A/B actual two-end fail-closed capture, guided limit-force retraction, load/retention/fatigue still unproven.
2. **P power:** three known single-point PCB bypass hazards; genuine BMS, reverse blocking, precharge, FET welded and dead-contact isolation tests, peak current, thermal rise and hot-unplug arcs absent. TE 2199001-1 Signal 1.5A is not a complete main-supply rating.
3. **S/U signal/USB:** Hirose accurate header+mate STEP and PCB footprints, actual physical dynamic FPC stackup, 79.75+8.2mm continuity with mid-motion reversal, differential impedance, TDR/VNA/eye/BER/EMI/ESD, 300k cycles absent. NO `DOCK_ONLY` substitution.
4. **D OLED:** controlled actual 7-inch module with COF/FPC/adhesive/seal, minimum dynamic R, long stow residual shape and flattening force, aging and fatigue data absent. IEC 62715-6-42:2026 is a **flattening-force method**, not fatigue certification.
5. **E OEM dimensions/permissions:** actual A/B PCB, battery, cameras and full finished equal-module BRep, manufacturer datum and GD&T, **signed allowed cut regions** not delivered. Research collision boxes must never be interpreted as a cut plan.

## R54 qualification order

**Stop geometry-cutting guesses.** Obtain exact same-revision native OEM CAD/controlled datum and independent signed permissions, supplier FPC neutral axis/torque-bend and accurate BM28 pair STEP, then run true 3D finite-section full-trajectory collision/strain evaluation, coupled with separately accredited M/P/S/U/D physical benches. If the owner refuses service-channel space, reject the continuous-FPC architecture under this packaging rather than silently relaxing USB's live-copper requirement. A redesigned topology may be explored but remains unapproved until equivalent continuous wired functionality is proved.

**Final: manufacturing_go=false. No manufacturing or energization authorization.**

### Independent branch caveat
R40's separate G1 `W2.0×t0.15mm` 193-state finite ribbon gate and R50–R52's `W1.2×t0.2mm` seven-family nine-snapshot gate do **not** represent the same test family or cross-section. R53 only reconciles the latter; their counts must never be summed as though they were one sampled continuous motion test. Both report research-shell clashes and both leave native OEM/FPC hardware absent.
