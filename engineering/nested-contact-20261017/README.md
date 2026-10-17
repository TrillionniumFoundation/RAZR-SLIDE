# Nested-volume re-equilibrated contact — 2026-10-17

See DELIVERY_VERIFICATION.json for actual outcomes and resolved-level-comparison.json for all metrics. case4..7 at level1 and level2 contain full retained-trace fields, raw gap arrays, independent scalar/tetrahedral checks and internal-recovery identities. Large recovered-interior fields and final response checkpoints remain on the authorized host with hashes in durable-fields-and-checkpoints.json. Prior matrix copies were independently hash-rechecked, not duplicated.

The original fresh level2 run recomputed every seed response with the new stiffness. A second current-source replay restored only this same-energy state and independently solved every requested load again. Level1 used its own prior matched-energy state. No old force solution was accepted without new equilibrium and polygon audit.

The source change is limited to the existing enriched driver and its fifteen input-identity tests; no parallel contact model or new geometry was introduced. All1004 tests have current canonical passing coverage with one explicit timeout/retry. Diagnostics and failures are outside that unit count.

Reproduce in the recorded numerical environment using the existing enriched driver with --inputs, --volume-level and a new --output. --resume-state accepts only exact matched-energy hashes. verify_enriched_contact.py must independently check each result and recover all interior unknowns. compare_resolved_levels.py requires completed independent results at each requested level. Scripts retained here include the exact executed paths; portability requires explicit path rebinding and hash verification, never hidden substitution.
