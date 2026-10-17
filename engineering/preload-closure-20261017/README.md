# Original preloaded-contact closure work — 2026-10-17

Continues PR27 f7351c3, not the stale draft description. Baseline951/31 has actually rerun locally with unchanged snapshots. The original case4 continuation is active and has not yet passed; cases5..7 are not claimed.

This increment adds an optional factor_reuse=False backend to the existing force-QP solver. Only the original-device resume adapter opts in. Active-set admissions, releases, equalities, energy, finite-point KKT checks and 1e-7mm full-cell audit are unchanged. Cholesky add/delete updates also transform the RHS; full active-system residuals are checked, and failure falls back to the existing pivoted solve/lstsq path without regularization.

All18 existing dual tests and10 new targeted tests actually passed in scoped runs. A real2453-force-column checkpoint was independently re-solved from its previous warm guess: same227 active-set iterations; maximum force difference about1.91e-13. The observed optimized solve was21.34s, versus78.76s for the original solve+field audit observation; this is not a controlled whole-solver speed comparison. Original physical fields still require complete checks.

No CAD, physical input, dependency or workflow changes. The two original full K matrices, original audit polygons and numerical thresholds remain hash-bound. Configured961/31 is not yet a completed regression. All hardware/manufacturing flags remain false.

## Final actual outcome

All961 tests/31suites completed on the functional commit, and cases4..7 now have original-domain independent full-field reports. Earlier draft statements above are preserved as history; see DELIVERY_VERIFICATION.json and METHOD_AND_LIMITS.md for final scope. No physical load or mesh-convergence qualification.
