# Full-energy spatial contact integration study

Imports the previously delivered spatial_contact.py and its 41 tests byte-exact.
Adds an 18-test feasible working-set solver for complementary energy in force
coordinates, with explicit rigid equilibrium. This is not interpreting the
old twelve prescribed-pressure port compliance as primal stiffness.

For full-scale use, each interface point applies exactly opposite P2 trace
loads to the complete unchanged panel and frame K. An elastic response cache
and exact generalized complementary-energy equations avoid materializing an
800k-by-800k dense primal operator. Every supplied common polygon is audited
with the unchanged quadratic extrema routine; a negative region adds its
actual extremum position and repeats equilibrium. No displacement clipping,
penalty stiffness or extra physical anchor is introduced.

Current 59 new tests passed locally, including original 41 tests and 18 new
backend tests. Complete 873-test/31-suite regression and the original device
cases are pending, not inferred from the configured count. CAD, actual
material/load inputs, dependencies, workflows and old counterexamples remain
unchanged. Current diagnostics retain the ideal remote frame end, conditional
four axial bolt pressure shapes/spring values and small-displacement pairing.
Point contact forces are not a resolved area-pressure field or stress rating.
Physical and manufacturing go remain false.
