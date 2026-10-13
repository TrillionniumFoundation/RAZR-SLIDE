# RAZR SLIDE

Private engineering research repository. **`candidate_go=false`; `manufacturing_go=false`.**

## Product constraints

Equal finished A/B dimensions; one approximately 7-inch flexible OLED; no independent rear display; B travels upward 79.75 mm, then seats normally by 8.20 mm; A has priority for the larger battery. 4700 mAh is an unverified target.

## Selected repair branch

**R50_20261011 is the integration and rejection-validation base**, original archive SHA256 `86f226f9bce3a3f0659737327c7cc32415eed3b9be3f96f35a746ac32844dfd6`. Its seven routes remain rejected. Selection follows whole-inventory review rather than revision numbering or isolated zero-collision results.

R44_FPC_20261013 is a separate, unterminated rear-loop research input. R79 is a separate conditional scalar mathematics branch. Neither establishes an assembled continuous electrical path.

Read the branch comparisons and current review in `engineering/`; do not interchange same-numbered packages from different dates/hashes.

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

No physical manufacturing, powered assembly or product qualification is authorized by this repository.
