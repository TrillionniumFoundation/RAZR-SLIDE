# Native BM28 endpoint engineering, 2026-10-13

This increment replaces missing endpoint geometry with original, source-bound
land patterns and a parametric static assembly coupon. It does not release a
phone, a PCB, a dynamic FPC, or a manufacturing drawing. `manufacturing_go=false`.

## Acquired inputs

Six exact Hirose PDFs were fetched as native bytes through the authorized
workspace network and transferred, with SHA-256 verification, to:

`/home/qian-qi/Documents/Codex/RAZR_SLIDE_R66/vendor_hirose/native_docs_20261013`

The two exact 2D drawings are EDC-364665-53-00 (DP) and EDC-364666-53-00 (DS),
both revision 1, DIS-H-00010654, engineering date 2021-09-08. The matching
ELC-364665/364666-53-00 specification sheets have reciprocal applicable-mate
entries and revision 1, DIS-H-00019757, engineering date 2024-01-25. The assembly
guideline is ETAD-H1016-00, DIS-H-00011614, revision 1, engineering date
2021-11-08. The current catalog cover says April 2026. An October 2026 website
update or copyright stamp is not a new drawing engineering revision.

`native_source_retrieval.json` records official URLs, byte lengths, and hashes;
`native_verified.json` is the actual qian-qi receipt, including successful
Poppler PDF parsing of all six transferred source files. Raw vendor PDFs and
raw STEP files remain on the authorized source machine and are not in Git.

Direct qian-qi API, wrapper, and old document-route requests returned HTTP 403;
their receipts are retained as `REJECTED_qian_*`. No HTTP error document was
accepted as a PDF. The 998,536-byte guideline initially exceeded an effective
base64-output transport bound; a failed binary write was followed by a verified
four-chunk upload and SHA-256 commit. Other five files used atomic binary writes.

## Exact original land patterns

`build_endpoint.py` generates the two KiCad footprints in
`RAZR_ENDPOINT_RESEARCH.pretty`. The official nominal copper and stencil
geometry is represented separately; dimensions and tolerances are preserved in
`official_dimensions.json`.

| Feature | DP plug | DS receptacle |
| --- | ---: | ---: |
| Signal sites | 24 | 24 |
| Signal pitch / first-last row span | 0.35 / 3.85 mm | 0.35 / 3.85 mm |
| Signal copper land | 0.18 x 0.615 mm | 0.18 x 0.310 mm |
| Signal row centre Y | +/-0.5925 mm | +/-0.745 mm |
| Power fitting copper land, each of four lands | 0.52 x 0.40 mm | 0.53 x 0.33 mm |
| Power fitting centre X | +/-2.515 mm | +/-2.630 mm |
| Power fitting centre Y | +/-0.325 mm | +/-0.785 mm |
| Power stencil aperture | 0.52 x 0.32 mm | 0.53 x 0.33 mm |
| Recommended stencil thickness | 0.08 mm | 0.08 mm |

The DP 4.51-mm dimension is the power-land inner-edge span; the DS 5.26-mm
dimension is the power-land centre span. Confusing these dimensions changes
the footprint. DP power-fitting stencil area is exactly 80% of the copper land
area; DS is 100%. Adjacent nominal signal lands have 0.17-mm copper separation.

The exact drawings provide no numbered pin-1 indication. The catalog explicitly
states that the connector has no polarity. Therefore each footprint uses
coordinate site IDs (`S_NEG_00` through `S_POS_11`, `P_L`, `P_R`), never invented
supplier terminal numbers. Each power fitting has two copper lands carrying
the same site ID: 28 lands but 26 independent electrical terminal identities.
System signals, USB lanes and battery nets are unassigned.

The footprints are marked research and excluded from placement/BOM outputs.
Their explicit zero soldermask expansion is an unqualified coupon hypothesis,
not a Hirose soldermask recommendation. Both KiCad 7-format assets now pass
actual qian-qi **KiCad 7.0.11** loading through its native `pcbnew` engine and
native CLI SVG export. The engine reads 28 copper lands, 26 electrical site IDs
and 28 independent stencil primitives per footprint, plus the DS rule-area
keepout with all four copper/track/via/pad exclusions. `native_kicad_receipt.json`
binds the footprint hashes, engine-read dimensions, native SVG hashes and exact
Ubuntu runtime-package hashes. A PCBA fabrication check remains outstanding.

The native runtime was downloaded with `apt download` and extracted locally;
no package installation, sudo, or mutation of existing user KiCad configuration
was performed. An actual parser rejection uncovered a missing DS zone-closing
parenthesis which the initial dimension tests missed. The rejected original
and engine failure log are retained; the fixed version passes actual loading.
A regression check now verifies complete footprint/zone expression closure.

The DS under-body region is a conservative copper/track/via exclusion. The
DP 7.0 x 1.9-mm minimum no-obstruction region is drawn on `Dwgs.User`; its
side-shaped surface-insulation treatment is not falsely represented as a
complete all-layer rectangle keepout through the actual pads.

## Original static coupon and STEP exports

Three original STEP files are exported and reimported. All 68 solids are valid
and have positive volume. The identical exports were also transferred with
SHA-256 checks and independently imported in qian-qi FreeCAD 1.1.1; the 29/29/10
solid counts and all validity/positive-volume checks pass, as recorded in
`original_step_native_reimport.json`. The first two show exact nominal land positions on
an assumed coupon substrate. The third separates the rigid PCB, static mated
connector reservation, FPC tab/free neck, adhesive, FR4 stiffener, compliant
buffer, removable cover, cover supports, and distal strain-relief clamp.

The connector board gap is 0.6 mm; the **research installed stack is 2.7 mm**
including the assumed 0.8-mm PCB. The FR4 stiffener uses the official minimum
0.3 mm. FPC thickness 0.15 mm, adhesive 0.05 mm, compressed buffer 0.4 mm,
cover 0.4 mm and 8-mm locally free neck are coupon hypotheses. Buffer pressure,
drop-load isolation, flexure force, solder thickness, material specification,
cover retention and production tolerances have not been measured. No routing
is supplied through the coupon neck. These STEP files do not contain Hirose's
native geometry and do not modify, cut, or claim fit in the protected OEM core.

## Native pair and wrong-orientation counterexample

`inspect_native_pair.py` actually ran in qian-qi FreeCAD 1.1.1 against the two
previously verified official STEP files, read-only. The DP model was inverted
about X or Y and translated so its mounting plane is 0.6 mm above the DS plane.
Both transformations give valid shapes and almost identical rigid-model common
volume, 0.01844345672895 mm3. Their native inputs' hashes remain unchanged.
The rigid CAD spring-contact overlap is not proof of actual mating or force.

The two assembly orientations change every one of the 24 signal identities
and exchange the two power fittings. `physical_site_map.json` preserves both
complete geometric correspondences. A symmetric mechanical fit cannot certify
electrical orientation. A fixed-board assembly datum, foolproof carrier feature
which does not rigidly pin the connector FPC, and an actual 26-terminal continuity
witness remain necessary. No electrical pin-1 or successful continuity is claimed.

## New specific source conflicts and remaining blocks

1. The DP connector-allocation inner dimension is **6.32 MIN** on the exact
   EDC page 1, but the same 0.175 x POS + 2.12 expression is **6.32 MAX** on
   guideline page 5. The exact copper/stencil land geometry agrees; the complete
   side-shaped allocation exclusion cannot be frozen without supplier disposition.
2. The guideline's DS recommended paste volumes (0.0048 mm3 per signal and
   0.0131 mm3 per power land) do not exactly equal nominal aperture area times
   0.08-mm stencil thickness (0.004464 and 0.013992 mm3). No silent geometric
   correction or paste-process release is made. Coupon paste transfer and fillet
   inspection are required.
3. The catalog/part-sheet resistance, insulation and shock differences remain
   preserved in the preceding connector review; reciprocal mate confirmation
   does not resolve those qualification-limit conflicts.
4. No native OEM endpoint channel, actual FPC material, complete mounted-stack
   fit, physical static coupon, orientation-keying trial, shock/drop witness,
   dynamic cable force/cycle witness, or installed electrical qualification is
   available. The original phone constraints and protected cores remain unchanged.

Eleven independent dimension, stencil, site-identity, orientation and expression
closure checks pass.
Their scope is recorded in `endpoint_tests.log`; successful computation and
STEP parsing supply geometry evidence only. `manufacturing_go=false`.

Reproduce original exports and tests:

```sh
python3 engineering/native-endpoint-20261013/build_endpoint.py
python3 -m unittest discover -s engineering/native-endpoint-20261013 -p test_endpoint.py -v
```

Replay the native parser on qian-qi using its preserved extracted runtime and
`verify_native_kicad.py` in the corresponding verification directory:

```sh
cd /home/qian-qi/Documents/Codex/RAZR_SLIDE_WORK_20261013/native_endpoint_kicad_verify
LD_LIBRARY_PATH="$PWD/extracted/usr/lib/x86_64-linux-gnu" \
PYTHONPATH="$PWD/extracted/usr/lib/python3/dist-packages" \
XDG_CONFIG_HOME="$PWD/config" XDG_CACHE_HOME="$PWD/cache" \
python3 verify_native_kicad.py
```
