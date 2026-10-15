# BM28 static continuity coupon PCBA candidates

Two actual KiCad schematic/PCB projects route every independent BM28 coordinate
site to a probe hole. Native KiCad 7.0.11 loads both boards, reports zero DRC
violations, zero unconnected pads and zero footprint errors, and exports the
research Gerbers, drills, placement and BOM. Native schematic XML and native
board data independently agree on all 26 electrical nets per board. This is a
passive continuity-coupon design candidate, not the complete phone PCB.
Independent pocket4 KiCad 9.0.8 native ERC also reports zero violations on both
schematics after a real off-grid failure was corrected.

`manufacturing_go=false` and `coupon_fabrication_go=false`. Material, copper
weight, soldermask process, mating orientation and real assembly qualification
remain unverified. Nothing was ordered, fabricated, energized or measured on a
physical coupon in this work.

## Actual source and output files

Open `endpoint_DP.kicad_pro` or `endpoint_DS.kicad_pro`; each has a native
`.kicad_sch`, `.kicad_pcb`, local footprint table and owned symbol library. The
schematic contains one connector and 26 passive probe features. Probe features
are PCB copper and plated holes, not 26 discrete parts to purchase.

| Design feature | Each board |
| --- | ---: |
| Board outline, research hypothesis | 40 x 36 mm |
| Thickness, research hypothesis | 0.8 mm |
| Copper layers | 2 |
| Signal coordinate sites | 24 |
| Fitting terminal identities | 2 |
| Connector copper lands | 28 |
| Probe holes / copper features | 26 / 26 |
| Probe drill / pad diameter | 0.5 / 1.0 mm |
| Asymmetric fixture datum NPTH | 3 x 2.0 mm |
| Total native pad objects, including NPTH | 57 |
| Native track segments | 80, on F.Cu |
| Proposed minimum clearance / signal trace | 0.10 / 0.10 mm |

The 26 plated probe holes expose copper on both faces, allowing access from the
outside faces after two boards mate. A first layout with only front-side probe
pads was corrected because the inward faces would impede probing. No impedance,
current capability, high-speed operation or manufacturing process is qualified
by the above dimensions.

The two footprint copies in `RAZR_ENDPOINT_RESEARCH.pretty` are byte-identical
to the frozen prior endpoint source. `RAZR_ENDPOINT_ASSEMBLY.pretty` changes
only research BOM/placement exclusion flags. Board-instance reference text and
position are annotations; nominal copper, independent stencil rectangles and
the DS under-body copper/track/via/pad keepout stay unchanged. The DS keepout is
transformed into the actual board datum and checked by the native engine at
`[97.635, 99.410, 4.730, 1.180]` mm bounding rectangle. DP's 7.0 x 1.9-mm
minimum no-obstruction drawing is preserved, including its distinction from
an all-layer copper prohibition through its own lands.

## Coordinate identity and assembly datum

`C01` through `C26` mean continuity only. The supplier provides no pin-1
designation for these mechanically unpolarized connectors. `S_NEG_00` through
`S_POS_11`, `P_L` and `P_R` are our coordinate IDs, never invented supplier pin
numbers or Motorola net assignments. Two lands on each fitting share one
terminal ID. For example, our chosen pairing maps DP `S_NEG_00` to DS
`S_POS_00`; DP TP01 and DS TP13 both carry C01. All 26 pairings and actual probe
IDs are in `mating_site_map.json`.

The upper DP board uses the derived X-axis 180-degree transform
`diag(1,-1,-1)` with nominal 0.6-mm mating-plane translation. Native PCB-read
hole coordinates match all three DS datum holes under that transform and fail
the opposite Y-axis 180-degree orientation. This is a fixture datum proposal:
matching locating pins and a physical assembly trial are still required.
Silkscreen or intrinsic connector polarity alone does not prevent mis-mating.
The nominal translation is not the entire installed stack height.

New Motorola service evidence identifies SCA8D57591 24-pin/H0.6-mm/pitch0.35-mm
receptacles but does not give a Hirose series part number. Equal pitch, height
and pin count do not prove BM28 compatibility. No OEM assignment was transferred
to this coupon. See `../controlled-input-recovery-20261013-r2` for that evidence.

## Native evidence and retained counterexamples

`native_pcba_receipt.json` contains engine-read pads, tracks, hole coordinates,
the DS rule area, native netlists and exact export hashes. `native_execution_proof.json`
records the authoritative remote process exit, log offsets and transferred
archive SHA-256. `verify_native_pcba.py` never imports the builder.

The real missing-route negative control reports an unconnected pad. The actual
C01-to-C02 copper bridge reports four fatal native errors, including 0.0000-mm
cross-net copper clearance. Native DRC's Boolean report-writing return was
never treated as a passing result; report contents must show zero violations.
The rejected native boards and reports are retained.
Each DRC now runs in its own fresh native process from a serialized board and
checks that the proposed 0.10-mm clearance / 0.25-mm hole rules actually load.
The in-memory multiple-board path produced only one mask error on the same
shorted board; independent reload restored the four fatal errors. The exact
engine cause is not established. Both reports remain available; no constraint
or negative-control assertion was relaxed to accept the incomplete check.

Other retained failures include the initial 83/84 DRC warnings, an incorrect
native API call, local/global net namespace mismatch, missing export directories,
and a verifier's wrong assumption about a KiCad version's short-error label.
SVG output exposed another real failure: PCB SVG output needs an explicit file
name; a directory argument returned zero without replacing an old preview.
Current verification requires separate native board and schematic files,
existence and unequal byte hashes. Stale parent-directory previews are retained
as `REJECTED_svg_stale_parent_*`.

`verify_exports.py` independently parses the actual Gerber stencil polygons and
PTH/NPTH coordinates, checks 24 signal plus four fitting rectangles, checks all
probe and datum holes against native PCB data, and verifies that placement
contains only J1. `independent_export_receipt.json` records these results. The
absolute native export uses `x=board_x, y=-board_y`; negative export Y is a
coordinate convention.

The KiCad7 CLI does not have an ERC command, so the KiCad7 receipt truthfully
records `native_ERC_executed=false`. `pocket4_ERC_receipt.json` and the two
`endpoint_*_native_ERC.json` files provide the separate actual KiCad9 ERC runs:
zero errors, warnings and exclusions on both schematics, exit zero, and all 13
frozen input SHA-256 values unchanged. The initial real ERC found 79 off-grid
warnings per board. Symbol origins, label anchors and wire ends were moved to
the standard 1.27-mm connection grid; board geometry and all 26 nets stayed
unchanged. The original 13 input files are preserved in
`REJECTED_ERC_offgrid_inputs_v1.tar.gz`; failure reports reside in the adjoining
qualification evidence. `ERC_INPUTS_FROZEN.json` binds the repaired inputs.
Actual rendered schematic review then found overlapping probe references and
values despite the zero ERC result. Row pitch was increased to 5.08 mm, duplicate
displayed pin numbers hidden, connector attributes moved outside the symbol,
and probe reference/value text placed in separate columns. Current native7
exact-net verification and current independent native9 ERC both pass on those
final readable source hashes. The earlier ERC-pass source package and the real
overlap SVG/PNG are retained. `verification_summary.json` binds the current
combined result; `visual_review.json` records inspection of both final native
schematics and both final native board images.

## Remaining physical and controlled-input blockers

The original DP 6.32-MIN versus guideline 6.32-MAX authority conflict and DS
paste-volume discrepancy remain unresolved. Nominal 0.08-mm stencil arithmetic
is not a process approval. Zero soldermask expansion is explicitly an unqualified
hypothesis, not a supplier recommendation. Actual board process capability,
reflow/inspection plan, mating force and orientation, locator fit, buffer/preload,
connector availability and physical continuity measurements remain absent.

The three datum holes do not qualify a moving FPC strain-release design. The
flex stack, copper neutral axis, clamping details, voltage/current assignments,
USB lane routing, batteries, OEM electronics and final phone PCB are not present
in this coupon. They remain separate unresolved engineering inputs.

## Reproduce

Generate candidates with `python3 build_pcba.py`. In qian-qi's previously
extracted KiCad7 runtime, set `LD_LIBRARY_PATH` and `PYTHONPATH` to its preserved
`extracted/usr/lib/x86_64-linux-gnu` and `extracted/usr/lib/python3/dist-packages`,
and set `RAZR_KICAD_CLI` to that runtime's `extracted/usr/bin/kicad-cli`.
Run `python3 verify_native_pcba.py`, then `python3 verify_exports.py`. These
scripts create only local engineering evidence and research export files.
