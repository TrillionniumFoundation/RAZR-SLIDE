# Remaining actual inputs

This list points to the existing R5/R7 requirements. It adds no new requirement,
measurement, threshold or physical pass. The two R7 finite factory poses and the
original N15 numerical contract already have their recorded qualified scopes.

| Delivery | Actual input needed | Existing handoff |
| --- | --- | --- |
| Candidate and sample | One specimen ID linked to the current candidate, geometry, assembly/BOM, material/process and firmware revisions; original source/native payload identities | H00 |
| Same specimen identity and parts | Unedited labels/photos and original runtime logs for ten missing identities; seven roles with PN/revision, dimensions and uncertainty, orientation/removal/tail directions, and original-device function | H01–H02 |
| Actual interconnect and selected revisions | Twelve original terminal maps with source/sink connector and pin identities, direction/returns/shields, measured original function and sourced electrical limits; selected OLED/COF, FPC stack, paired connectors and material/process sources | H03–H07 |
| Current structure and real motion | Material/contact/friction/preload/load inputs, actual travel-stop support and independent left/right reachable domains, correlated tolerances and worst cases for current K1/K3 geometry | H08 |
| Physical test contract | Current as-built binding, sourced thresholds, sampling/synchronization, calibration and revision-bound G3/G4/G5 plans | H09 |
| Actual staged tests | Same-candidate/same-specimen G3 acquisition and pass, then G4, then G5; retain missing tests, failures, repairs and replacements separately | H10–H12 |

The unchanged fact accounting is **228 unique requirements**: 10 identity,
77 seven-role part, 120 twelve-interface and 21 selected-revision facts.
207 require the same specimen; 21 require the actually selected PN/revision.
Current qualified new bindings and physical G3/G4/G5 passes are zero.

Use the existing original contract and receipt implementation:

- [R5 complete handoff](../../engineering-followup-20261028-r5/handoff/R5_EXTERNAL_BLOCKER_HANDOFF_V2.json)
- [R7 current blocker ledger](../../engineering-followup-20261028-r7/independent-review/blocker-ledger/R7_BLOCKER_CLOSURE_LEDGER_V2.json)
- [Existing original-evidence receiver](../../engineering-followup-20261028-r5/real-sources/receive_evidence_r5.py)

Generic model literature cannot fill same-specimen observations. Actual input
reception does not itself prove OEM applicability or grant a physical pass.
Current geometry FE remains separate from the restored original K/b/C results.

No external message or device command was issued by this metadata update.
