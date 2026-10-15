# RAZR SLIDE

Private engineering research repository. **`candidate_go=false`; `manufacturing_go=false`.**

## Product constraints

Equal finished A/B dimensions; one approximately 7-inch flexible OLED; no independent rear display; B travels upward 79.75 mm, then seats normally by 8.20 mm; A has priority for the larger battery. 4700 mAh is the unverified TOTAL SYSTEM target; individual A/B cells and capacities are unselected.

## Selected repair branch

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

CAD and software checks can reject a proposal but do not supply actual FPC stackup/fatigue, OEM keep-out permission, BM28 PCB/clamp design, continuous USB SI, battery/BMS short/backfeed/isolation tests, mechanical load/jam/retraction tests, or OLED qualification. STEP exports labelled GHOST are research-only.

Current design repairs and production blockers are recorded in [`engineering/PRODUCTION_BLOCKERS_R6.md`](engineering/PRODUCTION_BLOCKERS_R6.md). R3/R4 status files remain historical. The [`second-round status`](engineering/qualification-readiness-20261013-r2/CURRENT_STATUS.md) and earlier [`PRODUCTION_STATUS.md`](engineering/manufacturing-closure-20261013/PRODUCTION_STATUS.md) remain historical baselines. Native CAD/ECAD verification and machine receipts are kept with each artifact.

The second round recovers six primary-source documents with variant and OLED conflict records in [`controlled-input-recovery`](engineering/controlled-input-recovery-20261013-r2), and adds an editable hardware return-sensing chain with native terminal verification in [`return-sensing-design`](engineering/return-sensing-design-20261013-r2). It retains conductive PCB bypasses, nonzero healthy parallel return, conditional threshold overlap, zero-load blind spots, and unsafe rearm counterexamples. These are research evidence, not physical qualifications.

R3 adds an [actual pin-keyed endpoint carrier](engineering/endpoint-carrier-repair-20261013-r3), [hardware continuity-permission gates](engineering/electrical-isolation-repair-20261013-r3), and [pinned OEM display/touch/USB identities](engineering/controlled-input-recovery-20261013-r3). Complete phone layout, the physical probe source and matching physical qualifications remain unimplemented or unverified.

No complete controlled phone manufacturing package or matching physical qualification evidence exists in this repository. Its research drawings and software passes do not constitute manufacturing release.

R3 捕获实体修复与独立导出检查：[passive-veto-repair-20261013-r3](engineering/passive-veto-repair-20261013-r3/README.md)。

R4 原厂资料与实改：[OLED来源](engineering/oled-controlled-search-20261013-r4/README.md)、[FPC与RA材料](engineering/fpc-controlled-search-20261013-r4/README.md)、[自主干回路与WDI修复](engineering/proof-detector-design-20261013-r4/README.md)。厂家资料请求以[修正R4请求](engineering/production-inputs-20261013-r4/targeted-controlled-input-request.json)为准：4700mAh是整机目标，A优先大电池。

R4 历史冻结状态：[PRODUCTION_BLOCKERS_R4.md](engineering/PRODUCTION_BLOCKERS_R4.md)。

R4 实际[单切断PCB与原生生产格式导出](engineering/pcb-source-repair-20261013-r4/README.md)、[盖紧固与撤钥干涉修复](engineering/mechanical-return-design-20261013-r4/README.md)。两者均是未获实物放行的研究台架。


R5/R6 当前实改与证据：[G2 路线与全部拒绝实体](engineering/fpc-g2-route-candidates-20261013-r6/README.md)、[完整材料运动](engineering/fpc-material-motion-20261013-r5/README.md)、[无损 NPZ 恢复](engineering/fpc-material-motion-transport-20261013-r5/README.md)、[初版 OLED 模组规格](engineering/oled-orderable-module-search-20261013-r5/README.md)、[原厂条件叠层](engineering/fpc-layer-stackup-20261013-r5/README.md)、[四相电气自检](engineering/proof-selftest-design-20261013-r5/README.md)、[A 链四块研究 PCB 与实际原生导出](engineering/power-chain-pcba-20261013-r5/README.md)。

单正实体、零 DRC/ERC 和研究 STEP 不等于完整手机可生产。指定 OLED/FPC、真实整机装配、完整 PCB 及机械/双电池/USB/OLED 实物资格仍按 [当前生产门槛](engineering/PRODUCTION_BLOCKERS_R6.md)约束。`manufacturing_go=false`。

R6 [实际取得的 39 页 OLED 候选原始规格与来源核验](engineering/controlled-inputs-web-20261013-r6/README.md)保留完整40pin事实和动态资格缺口，未替代指定受控OLED。

## Current execution index — 2026-10-15

Start with `CURRENT_DESIGN.md`. The current transmission study is
`integration/cam_coupling.py`: a finite B cam, transverse follower, original-KEY
yoke and three captured telescopic stages. Its native evidence and explicit
remaining constraints are under `engineering/cam-coupling-20261015/`.

The mounted and thin mechanisms, empty-shell study and rejected rigid-link
experiments remain preserved research inputs, not replaced historical receipts.
Actual phone inputs remain in `integration/assembly_inputs.json`, unchanged.
The new shell cuts are project-owned study geometry, not approved OEM changes.

Run `uv sync --locked` and `uv run --locked python -B tools/verify.py`.
Use `tools/test_suites.json` for the current configured scope; use actual reports
and Research validation for results. Local scoped tests are not full CI reruns.

Groove-centerline compatibility is not complete unlock/relock qualification.
Backlash, PAWL actuation, return preload, all-pose interference, assembly and
real phone component/load/tolerance qualification remain open.
`candidate_go=false`; `fixture_fabrication_go=false`; `manufacturing_go=false`.

## Manual PAWL study — 2026-10-15

See CURRENT_DESIGN.md and engineering/pawl-actuation-20261015. Two independent
manual tabs now have actual slot/pin actuation geometry. Nominal paths and
wrong-order obstruction are distinct from endpoint-play failures, assembly
access, detents/preload and real locking qualification. No hardware release.

## Serviceable manual control study — 2026-10-15

The current entry is CURRENT_DESIGN.md. A removable shoulder pin, separate
thumb pad and detachable guide roof replace trapped integral interfaces.
This is a detached-backpanel nominal assembly sequence, not qualified
threads, preload, lock force or complete phone assembly.
