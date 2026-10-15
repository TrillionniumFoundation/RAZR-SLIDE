# RAZR SLIDE upper-branch comparative review

Reviewed read-only on 2026-10-13. No project source, baseline archive, CAD, or supplier input was changed. This is a source/evidence comparison, not a hardware qualification.

## Coverage and integrity

- All 97 standalone Markdown files matching R49–R79 or supplier/trust/vendor/RFQ/RFI were read in full; scope extends back to R31 for supplier documents. Their names, sizes, SHA-256, and available packaged counterparts are in `file_coverage_hashes.json`.
- All 37 R49–R79 ZIP files were indexed, hashed, and checked with ZIP CRC. They represent 33 different archive byte identities: R50 and R52 each have three identical top-level copies. No duplicate ZIP member names or CRC errors were observed.
- 1,207 declared member-hash comparisons, including duplicate archives and inherited manifests, matched. This count is comparisons, not 1,207 unique new experiments. R66 and the four-member R69 package do not contain a full member-hash manifest; their archive hashes and CRC were checked separately.
- Every matching standalone Markdown/package counterpart is byte-identical. The R59 RFQ deliberately carries the R58 document text and title; it is a copied request, not an additional supplier reply.
- Mathematical boundary roots were independently recomputed with standard-library Decimal at 100-digit precision, without importing R77–R79 solvers. Values agree with the frozen reports. This numerical check is not a formal directed-rounding proof or a 3D existence result.

## Branch topology and substance

| Branch/range | Actual contribution | Qualification boundary |
|---|---|---|
| R46→R47→R48→R49→R50 | R38 research A/B BRep; seven five-section routes; R49 off-grid finite-section witnesses; R50 full-length W1.2×t0.2 finite ruled-loft OCC compounds | Seven routes × nine poses: B positive overlap 63/63, A 49/63. R50 is a negative solid-check framework, not a usable cable. |
| R50→R51→R52 | Five-segment positive-volume attribution, intersection STEP, fixed-A/moving-B collision coordinates | Useful diagnostic extension to R50. R52 bounding boxes are query regions, not exact authorized cutouts or full-motion envelopes. |
| R53→R54→R55→R56 | Native datum screening, independent rigid fit, noncoplanar fiducials, motion witness inclusion, task-contract validation | Mostly software/data gates. R56’s 7,133 rows are planned jobs, not 7,133 executed OCC checks. |
| R57→R58→R59→R60→R61 | New actual research OCC: R57 14 old-route poses; R58 four new routes × three poses and single-transform correction; R59 voxel/sphere diagnostics; R60 directional prisms; R61 C1 fillets/Bishop frames | All remain negative/partial diagnostics. None defines one installed material-coordinate-preserving cable across motion. |
| R62→R63→R64→R65→R66→R67→R68 | Signed supplier admission, immutable snapshots, fatigue data formatting, material-station binding, portable gateway, isolated receipt writing | Software security/traceability, no new OEM/FPC CAD. R66 regressions and R67 unsafe output overwrite are preserved as counterexamples. R68 guards receipt writes; it does not grant physical qualification. |
| R68 requirements→R69→R70→R71 | Separate procurement/preflight protocol; R69 forged nonempty metadata; R70 actual byte/signature checks; R71 class-specific operator/license pins | R70/R71 is a separate protocol, not a replacement for R65/R68 geometry/material checks. It uses synthetic fixtures; actual supplier inputs remain zero. |
| R39 FPC motion + R71→R72→R73→R74→R75→R76→R77→R78→R79 | R72 joins sources for tangent/material-parameter rejection; R73 curvature/chord necessary conditions; R74–R79 scalar cassette rate, tolerance, start/stop bounds and interval witnesses | Not the CAD ancestry of R50. No STEP/BRep members in R72–R79 incrementals, and R77–R79 report zero new 3D FPC sweeps. |
| R41 FPC hardgate delta / R42 relay CAD | Parallel OCC negative evidence referenced by R75–R79 | R41 is corroborating spatial failure evidence, explicitly not an ancestor of the scalar math chain. No combined physical pass can be inferred. |

The R70/R71 narrative references an older small R39 anchor archive with SHA-256 `345b76461ecefbd0900934872c7f8c122e3638251de9eeb216947cfd74f0be2b`. R72 instead pins the 37-member R39 FPC-motion archive `6eb43c691f7ec900f63006f837667c55cbf9137ac0a49067a93e61f12e14a4fd`. These are distinct artifacts despite sharing R39 labels.

## R50 repair-base recommendation

Use **R50’s full-span finite-solid checking machinery** as the strongest reusable qualification framework among these upper branches. Preserve its existing seven failed candidates as baselines. Add R51/R52’s segment/body/frame diagnostics. Import a new topology, such as the separately audited R44 20261013 research proposal, as an expressly unqualified candidate rather than silently substituting its evidence for R50’s own lineage.

The complete R50 archive is SHA-256 `86f226f9bce3a3f0659737327c7cc32415eed3b9be3f96f35a746ac32844dfd6`, 41 members. Its embedded immutable chain was directly rehashed and CRC-checked:

| Archive | SHA-256 | Members |
|---|---|---:|
| R49 | `494fbdb0b726f068dc5e72903ca4c99a4f188835929e8b22a6e339e89f8ba00d` | 25 |
| R48 | `b9a2904ea79e348576120e63f24cdebc2efd2b6bf68ff40f9cdad1fe544d2e72` | 29 |
| R47 | `25af6127c7bc51b0f62deaef86963f3fed818e93d14ff7dd7a9240afcb692f45` | 28 |

Frozen A BRep SHA-256 is `500fd5446d63d0ea8291b2edf4c86abcae4f917f65d8716b2b0ac12f29082cf0`; B is `e9ee0f36a61142efa5c557c53ff23e2486bd74b71705ce86181acb10ad2250c7`. R58’s `baseline/R50_frozen_source.py` was directly compared to R50’s `src/r50_full_span_finite_ribbon.py`: identical bytes, SHA-256 `a364447413ca409dffb58436763ccc9b1eadd4bfb8de130a8d46127a685e4142`.

R50 already reports both **whole proxy** and separately trimmed free-span intersections. The 6 mm trim at each end does not certify connector roots: source explicitly sets `connector_stubs_intentionally_sharp=true` and lacks real stackup, neutral axis, strain relief, end fixtures, and USB. Its three full-length GHOST STEP scenes are 108 ribbon cells plus A/B solids; they are not 110 qualified hardware parts. Full-path checking must continue into actual end fixtures once supplied.

R58 is a useful additional failed-route library and coordinate regression: its mistaken double B translation produced a false zero overlap, while the correct raw-B single transform gives 24.94164306 mm³ for the mirrored STOW case. Do not use the withdrawn zero as a passing layout.

R61 contains richer continuous-width-frame **within-pose** geometry than R50, but is unsuitable as a cable base: it uses independently chosen R59 voxel paths, an unapproved R0.4 fillet, six segmented GHOST strips, and differing pose lengths 91.141593/51.141593/26.656637 mm. STOW/MID best tested frame still intersects B in 15 segments; OPEN zero intersection is local only. R62 proves these endpoints drift by A 0.200 mm and B-local 0.650 mm. Reuse its Bishop-frame method if appropriate, not its unconnected per-pose route or its tiny radius as a material rating.

## High-value archive identities

| Milestone | Complete archive SHA-256 | Why preserve |
|---|---|---|
| R51 | `3b31d2f3c3ae869a35953dd7d183e1ade05f5aa0c3c1ca1ae7ac5295a098dbb5` | Five-section OCC attribution |
| R52 | `ba0731232b3edaf67cc40a6bf5e29707660ec96c6692db00d74e1e377ff68dcc` | 220 collision witnesses in A/B frames |
| R58 | `1e021d6673e5d394df4073ad4d320c57fb4be3f2421b00ce0b4f0f32965f1886` | New failed families and double-transform counterexample |
| R61 | `653de4a62a145ddd49fc6bc94c2ec627c575fa4f5d7de16c83170eaa05228654` | Bishop-frame negative geometry and length inconsistency |
| R68 | `5a6cd0c21377acdaa59b6547e81d1679141a1ab6d0bd2f7b8f89341e3fae8a11` | Protected supplier originals/receipt output separation |
| R71 | `37d8d456601b8babdd6b59ba705989742c4b55acf66dfb17305a176596035525` | Role/license byte-pinning; review-only exit 3 |
| R72 | `d81841efd7ed3b4d6919daa06720421a8031ed5af2ee623fa2f07c1b230a7039` | Distinct R39/R71 cross-branch comparison |
| R77 | `43a61e1afd43d075d35638dcb683eefe1682a3cdae65f916e1409c44ae3abee2` | Nominal scalar C1 minimum-rate witness |
| R78 | `7f6cc2be3f0bd08879b39db48ef85b292a43b344947b932ea2aeb21512f7ea52` | Independent-error scalar model |
| R79 | `e35e055ecfe0141ed2b06780a58fdec9e02d6c27f0bd9f0092e4a2c0eafaed22` | Rest/acceleration scalar certificate; no CAD |

The separate R77 complete-offline-math replay bundle is `d7f535db5e9918347d81d786194f117de0f4302866aad85058716ad04671d526`, eight members, with the original R77 and four source archives. It is useful for reproducibility, not a more recent physical design.

## R77–R79 math limitations

Independent values: nominal R77 `k=0.9251629638709196333`; R78 with E=0.05 `k=0.9277021685718771388`; fixed-command E limit `0.0797309136042153663`; R79 terminal necessary A `0.1879838760810540636`; at assumed A=0.30 the starting-rest necessary k is `0.9644012635024692221`.

These are legitimate values for the frozen **scalar necessary-length-window** problem under L70/R15, specified anchors, forced short-arc branch, and stated error model. R79’s K0.98/A0.30 witness has approximately 3.5 μm conservative scalar-window margin. Its derivatives are with respect to mechanical path length; a real time-domain acceleration additionally depends on actual slide speed and acceleration. The code uses floating arithmetic and analytically conservative second-derivative envelopes; independent high precision is not a formally outward-rounded interval verifier. It cannot establish a 3D cable curve, finite ribbon clearance, fatigue, realizable storage volume, material transport, friction, actuator execution, or electrical qualification.

## Real stopping gate

Do not continue manufacturing additional signature/manifest gates or repeated random centerlines as a substitute for missing product input. Supplier drafts remain unsent, and the later 0/13 inventory is an inherited frozen observation rather than a fresh external search. The historical R38 directory-box modeling and missing-model statements do not establish current acquisition status. The current connector review found the R66-provenance native BM28 pair files on qian-qi, verified their hashes, and read them twice with FreeCAD 1.1.1: each is a valid solid, the two shape records match, original bytes are unchanged, and the real repeat-run exit is 0. See `../connector-review-20261013/BM28_machine_execution_receipt.json`. Native models remain on qian-qi without geometry transfer/publication; installed PCB/FPC, mating alignment, reinforcement, clamps, strain relief, and physical qualification remain incomplete. No real mechanical/electrical/OLED qualification is supplied by the acquisition or read-only shape check.

Next substantive work needs actual same-interface A/B/PCB/cell/OLED/rail/end-fixture geometry, material stackup and allowable dynamic bend/twist/strain, usable protected service volume, real power/USB topology, and bench evidence. An evidence-based research framework/candidate can be prepared beforehand, but a claimed repaired installed cable, force-limited mechanism, supply isolation, or real USB channel must stop at those absent inputs. Preserve all failures and keep `candidate_go=false` where geometry is rejected, `CAD_modify_go=false` for protected OEM changes, and `manufacturing_go=false` throughout. The historical 36/64 unsafe mechanical combinations and three single-point PCB bypass classes remain open; changing to static BM28 endpoints does not erase them.
