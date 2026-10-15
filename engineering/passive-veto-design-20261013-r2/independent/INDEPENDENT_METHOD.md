This verifier imports the final 16 actual STEP assemblies. It does not import
or execute `passive_veto.py`. Each individual body must be a valid, single,
connected solid with finite positive signed volume. Components are identified
from their measured bounds; key presence, key withdrawal, stop lift and the
full pawl release stroke are measured again from the imported geometry.

For each exported side, 45 independently reconstructed release positions are
checked against the actual stop, fixed root, both retaining covers and any
present key. The actual stop/pawl common is compared against a separate
rectangular bearing-section overlap calculation. A zero common at the final
release position does not imply that the path is clear. Only a positive common
somewhere along the path proves interception of this rigid research movement.

Another 45 samples per side check full pawl release followed by key withdrawal
from 0 to 0.7 mm, with the stop position prescribed from the research ramp
geometry. Every actual component pair must remain free of positive overlap.
These are geometry tests; prescribed positions do not prove spring return,
force, friction, strength, contamination tolerance or normal physical operation.

The explicit `PARTIAL_BOTH_0p05_FORCE_RELEASE_FAILURE` STEP is deliberately an
invalid forced intermediate state. Besides its positive stop/pawl collision,
the OPEN fixture retains a 0.000060 mm³ key/pawl capture collision. The first
verifier rejected that secondary collision as unintended. Its source, native
exit 1, logs and exact actual-input manifest are retained in
`rejected-partial-force-interpretation/`. The current verifier permits that
specific additional interference only when the independently measured release
path is blocked and the exported stop/pawl bodies also positively intersect.
Normal full-key release, normal withdrawal and all support-clearance tests
remain strict.

The completed second native run exited 0 after 233.364 seconds. It imported
180 valid connected positive-volume bodies across 16 STEP assemblies and
checked 1,440 reconstructed release samples plus 180 normal release-then-
withdraw samples. The final partial forced STOW state also retains a
0.000100 mm³ key/pawl capture collision; the corresponding OPEN state retains
0.000060 mm³. Both are explicitly marked as failed forced-motion witnesses.
Full-key permitted release and normal withdrawal remain collision-free in
the independently checked rigid samples. Actual source and STEP hashes did
not change during this native run.

The jammed-clear, absent-key assemblies preserve the actual escape condition.
They are failed safety counterexamples, even when the independent checker
successfully reproduces them. Connected solids and CAD guide contact do not
prove physical attachment of the unfastened covers or whole-phone load paths.
`fixture_fabrication_go=false` and `manufacturing_go=false` remain mandatory.
