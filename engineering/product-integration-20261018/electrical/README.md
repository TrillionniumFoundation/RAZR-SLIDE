# Rebuilt electrical evidence

This directory contains a new execution after loss of local 2026-10-18 output bytes. The new run, source identity, environment and artifact hashes are recorded in rebuild-receipt.json and artifact-index.json.

Source assembly SHA256: `695073e313dae45edbb7cf8c305d31c167b4e24e1731bf8be8f1a91a77dbd77b`. Source Git commit: `3eae4e7258814c7f5454937535d6c642dd51662f`.

Completed 49 moving states and 15 manual states; rejected 49 moving and 15 manual states. The three full endpoint/material STEP files each underwent the source generator's 41-solid reimport check; the standalone bench clamp contains eight solids. No phone assembly or manufacturing release is issued.

Native KiCad v4 checks were not rerun. The three regenerated PCB byte hashes match the retained v4 input boards; DRC, Gerber, drill and measured STEP-thickness evidence remains in the existing main checkout. No historical execution log or test result is relabeled as part of this execution.

See source-design-notes.md for the preserved design narrative, and research-BOM.csv for a newly derived two-end research bill of materials. These notes and material quantities are definitions, not physical stock or fabrication evidence. Actual donor identity, OEM pin mapping, FPC material qualification and installed phone circuitry remain unverified.
