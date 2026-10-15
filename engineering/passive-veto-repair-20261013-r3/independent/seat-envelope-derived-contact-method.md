The original A-key was preserved. Both original engaged and parked pawls were
translated by +0.150 mm along the key-withdraw direction (STOW −Y, OPEN +Z).
The independent contact pilot executed on actual CadQuery/OCC bodies and exited
0 after 15.601 seconds. It used 11 nonnegative q values from 0 to +0.100 mm in
0.010 mm increments and all 27 injected XYZ offsets at ±0.050 mm.

All 1,188 logical states had zero actual material intersection throughout the
23-point original X retreat path. Each had positive actual interception under
the new 0.250 mm reverse-withdrawal probe. Minimum measured positive commons
were 0.003100 mm³ for STOW and 0.001860 mm³ for OPEN. The full calculation used
756 unique actual geometry profiles, 864 signed OCC commons and 18,036 proven
zero AABB comparisons after input-solid validation.

The original 0.050 mm probe remains a counterexample. No q sample passed it
for all 27 injected offsets. Only 18 of 297 individual offset/q states per
port/side had positive common under that original probe; the nominal states
did not. The new 0.250 mm witness must never be reported as an original probe
pass or as equivalent mechanical retention behavior.

A separate native first-contact witness exited 0 after 2.135 seconds. For all
four original port/side contact pairs it directly checked actual signed OCC
common at q=0.175, 0.180 and 0.185 mm. Common remained zero at the first two
positions and became positive at the third. An injected −0.050 mm key error
along the withdrawal coordinate shifted that bracket to q=0.225, 0.230 and
0.235 mm. The resulting isolated-contact free-withdrawal boundaries are
nominally 0.180 mm and 0.230 mm for that adverse error. This is a larger loss of
initial restraint, not an unqualified improvement.

The isolated contact pilot does not include the complete r3 stops, guide,
chassis or force-bearing supports. It does not qualify the larger free motion
against FPC strain, BM28 mating retention, OLED deformation, torsion or impact.
Those interactions remain unknown. Source bytes stayed unchanged and the
injected errors are not supplier GD&T. `manufacturing_go=false` remains
mandatory.
