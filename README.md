# RAZR SLIDE

<!-- current-product:start -->
## Current product integration — 2026-10-19

[Current design](CURRENT_DESIGN.md) · [Machine-readable product state](design/current_product.json) · [Implementation and evidence](engineering/product-integration-20261018/README.md)

PR #36 continues with sequenced separable captured followers, a full common assembly exporter including the explicitly rejected EP2/FPC candidate, and executable donor/physical-record ingestion. Native and canonical verification of this follow-up are pending at this functional snapshot. Main remains a1b3cc1; PR35 remains a separate draft; PR25 is closed without merging its old driver.

The active milestone is a common assembly with flat OLED storage, complete terminations, A/B cell reservations and an operable manual cycle. Measured parts, source specifications and project assumptions retain separate identities.

Configured unit validation: **1297 tests / 33 suites** in `tools/test_suites.json`. Completed execution reports retain their exact commit and scope in `design/current_product.json`; a configured count is not an execution result.

The first canonical execution at b6abcb6326439270ec137cdac00cd6dd7ade4ac7 ran 32 suites / 1220 tests and FAILED; its raw failure remains preserved. The bounded repair at 3eae4e7258814c7f5454937535d6c642dd51662f passed 7 suites / 182 tests. The independently checked canonical selection combines the first run's passing 25 suites / 1058 tests with the repaired 7 suites / 182 tests: 32 suites / 1240 tests, not one fresh full run. The selection report is engineering/product-integration-20261018/validation/canonical-selection.json. This product-branch evidence is published in PR #36 and is not merged into main; accepted main 1187 and PR35 draft 1216 remain separate. New mechanical execution passed 14 targeted tests, 8106 changed/new-part pair checks, 484 OLED enclosures, 9021 added-material non-self comparisons and complete STEP readbacks with 99/99/106 participants. FPC reconstruction rejected all 49 motion plus 15 manual states with zero Boolean-operation errors; the selected-supplier dynamic bend-radius limit is unknown. New electrical/FPC evidence contains 90 files plus its index. The three PCB results reuse retained KiCad v4 zero-DRC/zero-unconnected/zero-footprint-error evidence and were not rerun. Original temporary mechanical/FPC large files were lost; current rebuilt artifacts retain new execution identities. PR25 is closed as superseded by PR36 without merging its old driver; PR35 remains draft. PR36 hosted run 39188719769 failed in all 12 jobs before any step ran; the current platform failure cause is unverified and no hosted test pass is claimed. Follow-up on 2026-10-19 directly retrieved the PR36 497e0da run annotation: GitHub prevented job startup because recent payments failed or a spending limit needs increasing. One full-unit job retry (attempt 2) and its aggregate job again executed zero steps and retained that annotation; ten native results in the attempt are inherited, not new executions. New sequenced assembly, EP2 carrier and evidence-ingestion sources are registered; their configured test count is not a completed result.

Accepted numerical evidence: [PR34 installation/service](engineering/installation-control-20261018/DELIVERY_VERIFICATION.json). Bearing research and the older spring experiment retain their own versioned results in the current product state; historical failures remain preserved.
That FE evidence belongs to the original installation geometry. The newly modified product shells have not been structurally requalified.
<!-- current-product:end -->

Private engineering research repository. **`candidate_go=false`; `manufacturing_go=false`.**

## Product constraints

Equal finished A/B dimensions; one approximately 7-inch flexible OLED; no independent rear display; B travels upward 79.75 mm, then seats normally by 8.20 mm; A has priority for the larger battery. 4700 mAh is the unverified TOTAL SYSTEM target; individual A/B cells and capacities are unselected.

## Historical repair baseline

**R50_20261011 is the integration and rejection-validation base**, original archive SHA256 `86f226f9bce3a3f0659737327c7cc32415eed3b9be3f96f35a746ac32844dfd6`. Its seven routes remain rejected. Selection follows whole-inventory review rather than revision numbering or isolated zero-collision results.

R44_FPC_20261013 is a separate, unterminated rear-loop research input. R79 is a separate conditional scalar mathematics branch. Neither establishes an assembled continuous electrical path.

Read the branch comparisons and current review in `engineering/`; do not interchange same-numbered packages from different dates/hashes.

The current R50 guard continuation is [`engineering/r50-topology-repair-20261013`](engineering/r50-topology-repair-20261013). It rejects loose or repeated Wire content hidden in apparently valid single-solid Compounds. All 42 runner tests pass, with two freshly rebuilt 108-cell poses still retaining their B collisions. Earlier repair code and receipts remain as preserved history.

The 121-pose R44 side audit now uses strict participant and signed-common checks in [`engineering/strict-motion-audit-20261013`](engineering/strict-motion-audit-20261013). AABB shortcuts require validated complete participants and a positive axis gap. Its retained shallow-overlap counterexample demonstrates that a checked zero OCC result does not establish positive clearance or continuous-motion qualification. Existing exact distance measurements remain explicitly referenced prior evidence.

## Original records

- `archive/`: reversible exact-byte originals, identities, independent verification, package lineage, historical failures and restoration tool.
- `docs/records/`: 157 directly readable historical Markdown documents.
- `docs/razr-slide-library-inventory.json`: project records and historical visual candidates.
- `baselines/`: frozen, selected source/evidence views. Nested original archives are restored from `archive/` when a historical reproduction script needs them.
- `engineering/`: new independent CAD, BM28 static termination, separated interfaces and mechanical/power safety reviews.

```sh
python3 archive/restore.py --verify
python3 archive/restore.py --restore RAZR_SLIDE_R50_verified_negative_gate_20261011.zip --destination recovered
```

728 originals (3,552,594,718 bytes) are preserved, including superseded visual concepts and two mismatching historical SHA sidecars. Historical images are illustrative records, not current geometry or qualifications.

Raw vendor CAD remains on its authorized source machine where the supplied Readme restricts redistribution. Its provenance, unchanged hashes, exact dimensions and our original reservation-envelope results are recorded; those models are not included here.

## Engineering limits

CAD and software checks can reject a proposal but do not supply actual FPC stackup/fatigue, OEM keep-out permission, physical BM28 connector/PCB/clamp fit and retention qualification, continuous USB SI, battery/BMS short/backfeed/isolation tests, mechanical load/jam/retraction tests, or OLED qualification. STEP exports labelled GHOST are research-only.

Historical R6 design repairs and production blockers are recorded in [`engineering/PRODUCTION_BLOCKERS_R6.md`](engineering/PRODUCTION_BLOCKERS_R6.md). R3/R4 status files remain historical. The [`second-round status`](engineering/qualification-readiness-20261013-r2/CURRENT_STATUS.md) and earlier [`PRODUCTION_STATUS.md`](engineering/manufacturing-closure-20261013/PRODUCTION_STATUS.md) remain historical baselines. Native CAD/ECAD verification and machine receipts are kept with each artifact.

The second round recovers six primary-source documents with variant and OLED conflict records in [`controlled-input-recovery`](engineering/controlled-input-recovery-20261013-r2), and adds an editable hardware return-sensing chain with native terminal verification in [`return-sensing-design`](engineering/return-sensing-design-20261013-r2). It retains conductive PCB bypasses, nonzero healthy parallel return, conditional threshold overlap, zero-load blind spots, and unsafe rearm counterexamples. These are research evidence, not physical qualifications.

R3 adds an [actual pin-keyed endpoint carrier](engineering/endpoint-carrier-repair-20261013-r3), [hardware continuity-permission gates](engineering/electrical-isolation-repair-20261013-r3), and [pinned OEM display/touch/USB identities](engineering/controlled-input-recovery-20261013-r3). Complete phone layout, the physical probe source and matching physical qualifications remain unimplemented or unverified.

No complete controlled phone manufacturing package or matching physical qualification evidence exists in this repository. Its research drawings and software passes do not constitute manufacturing release.

R3 捕获实体修复与独立导出检查：[passive-veto-repair-20261013-r3](engineering/passive-veto-repair-20261013-r3/README.md)。

R4 原厂资料与实改：[OLED来源](engineering/oled-controlled-search-20261013-r4/README.md)、[FPC与RA材料](engineering/fpc-controlled-search-20261013-r4/README.md)、[自主干回路与WDI修复](engineering/proof-detector-design-20261013-r4/README.md)。厂家资料请求以[修正R4请求](engineering/production-inputs-20261013-r4/targeted-controlled-input-request.json)为准：4700mAh是整机目标，A优先大电池。

R4 历史冻结状态：[PRODUCTION_BLOCKERS_R4.md](engineering/PRODUCTION_BLOCKERS_R4.md)。

R4 实际[单切断PCB与原生生产格式导出](engineering/pcb-source-repair-20261013-r4/README.md)、[盖紧固与撤钥干涉修复](engineering/mechanical-return-design-20261013-r4/README.md)。两者均是未获实物放行的研究台架。


R5/R6 历史实改与证据：[G2 路线与全部拒绝实体](engineering/fpc-g2-route-candidates-20261013-r6/README.md)、[完整材料运动](engineering/fpc-material-motion-20261013-r5/README.md)、[无损 NPZ 恢复](engineering/fpc-material-motion-transport-20261013-r5/README.md)、[初版 OLED 模组规格](engineering/oled-orderable-module-search-20261013-r5/README.md)、[原厂条件叠层](engineering/fpc-layer-stackup-20261013-r5/README.md)、[四相电气自检](engineering/proof-selftest-design-20261013-r5/README.md)、[A 链四块研究 PCB 与实际原生导出](engineering/power-chain-pcba-20261013-r5/README.md)。

单正实体、零 DRC/ERC 和研究 STEP 不等于完整手机可生产。指定 OLED/FPC、真实整机装配、完整 PCB 及机械/双电池/USB/OLED 实物资格仍按 [R6 历史门槛](engineering/PRODUCTION_BLOCKERS_R6.md)约束。`manufacturing_go=false`。

R6 [实际取得的 39 页 OLED 候选原始规格与来源核验](engineering/controlled-inputs-web-20261013-r6/README.md)保留完整40pin事实和动态资格缺口，未替代指定受控OLED。
