# R40 clean-cell repeat verification (independent from the initial worktree)

**CAD research-only recheck passes; manufacturing remains NO-GO.**

An independent unpack of `RAZR_SLIDE_R40_verified_engineering_package_20261012.zip` was made at `/mnt/data/R40_clean_replay`, not the original R40 generation worktree. The package was first checked via its archive SHA256, full ZIP CRC, per-member SHA256 and the embedded parent R39 original checksum.

The initial one-shot `R40_REPRODUCE.sh` invocation exceeded its bounded execution window during the sacrificial B-chassis OCC pocket cuts. It was **not** marked as a successful end-to-end one-shot run. The remaining steps were then rerun separately and obtained actual zero exit statuses: `r40_pocket.py`, `r40_faults.py`, `python -m unittest -q test_r40.py` (**38/38**), and `r40_attest.py`; the first one-shot run had already freshly completed `r40_prepare.py`, `r40_motion.py`, `r40_occ.py`.

The independent clean-cell result exactly reproduced these numerical outputs:

- `verification/R40_motion.json` **byte identical** to the original;
- `verification/R40_faults.json` **byte identical**;
- `R40_results_20261012.json` **byte identical**;
- all **five** OCC geometric volumes and the full per-obstacle collision matrices match;
- independent B pocket **38.99386693mm³** material cut result matches, negative BRep SHA256 **byte identical** to original;
- three STEP files **reimport 7 valid solids each** and have the same **per-solid volume and bounding-box fingerprints** (1e-6mm³ and 1e-5mm rounding). Their whole-file SHA256 hashes are **not** identical because the exporter reserializes headers/representation; no false byte identity is claimed.

The inherited 697 R21–R38 source tests and 31 R39 source tests were independently run in the original R40 generation session, with logs and exit-code receipts included. In the clean-cell replay, those existing receipts were *validated*, not all freshly repeated a second time. This distinction is intentional.

**The repeat proves deterministic named-solid research outcomes, not FPC durability, contact electrical function, OLED permission, mechanically protected routing or manufacturability.**
