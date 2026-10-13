# RAZR SLIDE

Private engineering research repository. **`candidate_go=false`; `manufacturing_go=false`.**

## Product constraints

Equal finished A/B dimensions; one approximately 7-inch flexible OLED; no independent rear display; B travels upward 79.75 mm, then seats normally by 8.20 mm; A has priority for the larger battery. 4700 mAh is an unverified target.

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

The current production blockers and concrete required inputs are recorded in [`engineering/manufacturing-closure-20261013/PRODUCTION_STATUS.md`](engineering/manufacturing-closure-20261013/PRODUCTION_STATUS.md). This increment adds original static endpoint land patterns and STEP coupons, a guided dual capture fixture with retained escape counterexamples, explicit battery/USB terminal paths, and fixed-material FPC bend-axis analysis. Actual native engine verification and machine receipts are kept with each artifact.

No complete controlled phone manufacturing package or matching physical qualification evidence exists in this repository. Its research drawings and software passes do not constitute manufacturing release.
