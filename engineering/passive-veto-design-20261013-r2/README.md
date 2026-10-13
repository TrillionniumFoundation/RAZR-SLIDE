# Independent key-presence interposers, research geometry r2

`manufacturing_go=false`, `fixture_fabrication_go=false`. This is an actual
increment of the one-to-one capture bench, not a production latch or qualified
phone assembly. It preserves the exact R25 STOW and R26 OPEN active key/pawl
contact solids, including the original 69.5 mm L/R spacing.

The earlier bench permitted both pawls to move to their parked positions with
no key. Here each pawl has its own fused release tab, each key has its own fused
ramp adapter, and each side has a separate guided interposer and a material
connected support rooted in that side's bench guide. The key ramp lifts only
its own stop. A missing or under-inserted key leaves that side's nominally
closed stop crossing the actual pawl retreat path. No Boolean permission
changes the geometry. There is no common release actuator that retracts both
stops, and no software or power is used to model the cam motion.

Release means retreating a captured pawl to its original parked position. Both
pawls must retreat before the bench has both captures released. With one key
present, its side can retreat; the other side's default closed stop remains in
the other retreat path. This does not prove that one remaining real latch can
retain a loaded or twisted phone.

## Added material and bounded assembly

Each side exports six single valid positive-volume solids with its key, five
without it: key/cam, pawl/tab, fixed root/guide, interposer, original research
cover with new clearance slots, and a separately removable interposer cap.
The existing covers and new retaining caps are unfastened CAD parts. Four
0.15 mm holes in the new cap are interface datum placeholders, not released
fastener holes, selected screws, threads or a justified fastening method.

The interposer can be lowered through the open upper channel before its cap
is installed. The cap then lowers onto the root. Actual sampled assembly
paths are checked against the exported bodies. Original key and pawl solid
volumes are retained in the fused new parts. STOW's copied bench guide/cover
has a new narrow front access opening; its earlier broad research grip was
replaced with a narrow grip and a high cam link. OPEN's actuator link uses a
separate docking plane to avoid the stop crosspiece. These changes alter the
bench stiffness and do not provide OEM shell geometry or an OEM mounting root.

| Research parameter | Value | Evidence boundary |
| --- | ---: | --- |
| STOW pawl retreat | 1.10 mm | Original R25 contact translation |
| OPEN pawl retreat | 0.55 mm | Original R26 contact translation |
| Full key cam lift | 1.20 mm | New research hypothesis |
| Cam lift/insertion ratio | 2.0 | Rigid research ramp |
| Tab top / nominal lifted-stop gap | 1.19 / 0.01 mm | Hypothesis, not manufacturing tolerance |
| Resulting nominal full-seat acceptance window | 0.005 mm | Geometric sensitivity only; not achievable GDT evidence |
| Interposer guide gap | 0.02 mm | Hypothesis; no friction, wear or debris qualification |
| L/R guide roots | Separate connected solids | Material continuity in CAD; no strength proof |
| Key withdrawal tested after full pawl retreat | Start of removal through 0.8 mm | Bounded sampled path; full extraction unproven |

The **0.005 mm nominal seating window is an unresolved design/manufacturing
blocker**, not a new product requirement. It must be redesigned to accommodate
the real seat geometry or supported by actual controlled GDT and measured
assembly/wear evidence. This branch provides no such evidence and cannot be
used as a fixture fabrication release.

`passive_veto.py` binds all prior protected source files by SHA-256 before and
after execution. It checks direct OCC signed commons on each release sample,
STEP reimports, original contact preservation, stop/cap assembly, and coupled
release then key-withdrawal samples. It does not clamp negative signed volumes
or identify zero intersection with physical clearance.

The native builder checks 644 actual release samples, 64 coupled samples and
56 assembly positions, and reimports 16 STEP files containing 180 valid
positive-volume solids. Its source binding covers 1,140 protected prior files.
Independent checks reimport the real STEP bodies without running the builder,
reconstruct each release path, compare OCC overlap with a separately stated
rectangular contact model, and check normal key withdrawal. The independent
material support check additionally perturbs each stop against its actual root
and unfastened caps; common volumes describe rigid contact, not force capacity.

Cloud independent actual STEP checking and all three X230 operations completed
with native exit 0. Each machine checks 1,440 reconstructed release samples,
180 normal release-then-withdraw samples, four material-support contact paths
and the whole STEP payload (180 positive solid leaves, no free non-solid leaf).
The same 24 transferred sources/STEP files were unchanged on X230. Comparison
of the actual results covers 15,051 numerical values and 7,730 identities;
maximum numerical difference is 0.0, excluding runtime identity only. The X230
geometry check took 474.802 seconds, with its actual native logs and immutable
download receipts retained in `x230-independent/`. This is computer
repeatability, not physical test qualification.

**The veto is a path test.** A narrow moving release tab can be beyond the stop
at the final parked endpoint. Zero endpoint common does not mean the move was
possible: the tab crosses the stop earlier. Forced-release failure STEP files
therefore show an intermediate 0.35 mm retreat collision, rather than quietly
exporting only a non-overlapping endpoint.

## Failures retained

`rejected-first-layout` contains actual fixed-root/coupon/cover clashes. The
second layout disconnected a moved actuator stalk from the original pawl and
was rejected before export. `rejected-withdraw-layout` records a long release
leaf that blocked the stop from lowering after the pawl was already parked.
`rejected-fourth-layout` records the high ramp tail crossing the stop bridge,
OPEN's low link hitting its guide, and STOW key/grip withdrawal collisions.
The final layout removes these bounded nominal collisions with physical CAD
changes; none is dismissed by shrinking the collision check or accepting an
invalid solid.

`rejected-missing-lower-support` preserves the first full builder pass and all
16 corresponding STEP exports. An additional actual STEP contact test exposed
the missing STOW lower stop: the release opening had removed its floor. The
new STOW root includes a connected ledge underneath the interposer bridge,
away from the release tab and cam planes. The entire assembly and movement
checks are rerun after this material change. The rejected record demonstrates
why a collision-free nominal pose alone was insufficient.

The intentionally retained `JAMMED_CLEAR_BOTH_ABSENT_ESCAPE` STEP has no keys,
but both stops are held at the lifted position. Both pawls can retreat. The
`JAMMED_CLOSED_FULL` tests instead force fully inserted rigid keys against a
stuck lowered stop and show actual key/cam interference. That forced state
is not a normally assembled scene.

## Unclosed physical qualification

The stop position for a withdrawn/absent key is a prescribed boundary
condition, not a demonstrated return spring. A ramp can positively lift a
stop during insertion; it does not supply the required physical return force
on removal. Return springs, broken-spring response, friction, gravity,
orientation, contamination, impact, wear, material strength, retained caps and
fasteners remain unqualified. No force threshold, spring constant, alloy,
damage load or finite-force return limit is invented.

Real force travels from the pawl/tab into the interposer, its guide and that
side's bench root. Continuity does not prove bending/shear stiffness, capture
strength or cap retention. Electrical safety still requires its separate
qualified containment/interlock system; key presence alone is not permission
to energize BM28 or USB. Both-key identity can also be spoofed by a correctly
shaped foreign object; there is no claimed foreign-object immunity.

For physical closure, measure each side's insertion/retreat/withdrawal force
curves, stop return margin over the full stroke and orientations, cap/root
deflection, missing/partial/one-key behavior, stuck-open/closed and broken
spring cases, twist/impact/debris/aging, and actual weakest key/pawl/OLED/FPC
damage loads. Combine those measured limits with a physical force limiter.
`physical-measurement-contract.json` leaves every absent input/result null.

Neither this branch nor an apparently successful rigid bench releases the
original phone constraints: equal A/B exterior size, one approximately 7-inch
flexible OLED, 79.75 mm upward slide, 8.2 mm normal seating and A-priority
battery volume. OEM physical assembly and complete production qualification
remain required.
