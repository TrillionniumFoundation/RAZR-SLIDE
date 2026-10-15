This is a source-constructor counterexample pilot, not final independent STEP
verification. It compiled the exact preserved old r3 builder bytes under a
non-main module name, keeping the original source pathname for its historical
dependencies. The executed snapshot SHA-256 is
`71e91ef0dae9a5fac1eee06615d54a08955c56c546c8fa45754d201efe2a30f4`.
The pilot did not edit the live builder or execute its main routine.

The native pilot exited 0 after 362.050 seconds. Eight 23-point motion paths
were evaluated with every actual component pair, alongside 48 independently
calculated circle/segment-distance cases checked against actual key/stop OCC
common. Six actual counterexample STEP assemblies were exported and reimported
with unchanged valid positive component counts and volumes.

| Old-source condition | Actual interposer/pin path | Actual whole-assembly retreat |
|---|---|---|
| q=0.200 mm, both stop lifts 1.110 mm, STOW | Clear | Blocked by key/pawl overlap, maximum 0.003800 mm³ |
| q=0.200 mm, both stop lifts 1.110 mm, OPEN | Clear | Blocked by key/pawl overlap, maximum 0.001920 mm³ |
| q=0.150 mm, both stop lifts 1.200 mm, STOW | Clear | New low-link/key clash, maximum 0.000360 mm³ |
| q=0.150 mm, both stop lifts 1.200 mm, OPEN | Clear | All component pairs clear throughout the sampled path |

The q=0.200 mm poses already overlap the original capture geometry at the
engaged pawl. Interposer clearance at those prescribed poses cannot be called
a complete physical escape. The q=0.150 mm OPEN poses allow retreat outside the
0.100 mm cam centerline plateau; that does not itself make them unsafe, because
the derived original contact is still within its nominal captured range.
The plateau is not the complete admissible stop-position set.

The separate frozen-source collision-localization run exited 0 after 7.303
seconds. The STOW q=0.150 mm collision is on the added low link: actual world
bounds Y=−0.095 to −0.050 mm and Z=+0.150 to +0.230 mm, with X width 0.100 mm.
That location corresponds to the new link at canonical r=−9.85 to −9.77 and
its forward q edge. It is not the original intended capture face and must not
be reported as qualified retention. Routing that link behind the shifted
original stem remains a new candidate requiring fresh actual checks.

The independent circle test is a sufficient single-capsule containment test;
it is not a necessary test for the union at capsule junctions. Actual OCC
common determines the observed shape clearance. Radial pin/slot slack and cam
slope define a set of admissible stop positions rather than a single
centerline value. No friction, force, material, spring, actual jam, chassis,
FPC, BM28 or OLED qualification follows from this pilot.
`manufacturing_go=false` remains mandatory.
