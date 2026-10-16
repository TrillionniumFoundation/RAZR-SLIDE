# Original-body spatial contact: bounded integration, not all-case release

The original dense primal core and41tests are byte-exact. The new18-test
force-space backend minimizes complementary energy from complete K response
columns and preserves rigid equilibrium. The old twelve prescribed-pressure
contact ports are NOT relabeled as displacement stiffness. Every adaptive
point applies opposite original P2 trace loads; full original volume DOFs
are retained. Four inherited bolt pressure shapes and positive linear spring
branches remain conditional. Initial spring force is not installed preload.

All873unit tests reran on the same functional commit with unique31suite
coverage and unchanged snapshots. Case0 used the first driver, cases1..4 the
second. The second driver reused case0 locations but recomputed their full-K
responses. It did not reuse case0's force solution. The first four original
zero-initial-spring-force cases pass all5255common polygon extrema. The first
nonzero-initial-force case reaches the bounded point expansion without
meeting1e-7mm, and the remaining three cases were not started afterward.
Do not describe this as all-eight-case contact completion.

Each of the five returned full fields is independently rechecked without
importing a contact solver. Tetrahedral P2 library functions reconstruct
loads and extremal witnesses; both full K matrices check residuals, numerical
gauge reactions, far-end reactions, work/energy and global force/moment.
The rejected fifth field still fails the same full-cell gap criterion and
is preserved, not silently clamped or trimmed. The finite response matrix,
point sequence and all intermediate counterexamples are preserved for a
controlled continuation instead of rebuilding everything from scratch.

These are fixed-mesh, small-displacement synthetic cases with E=1,nu=.3,
frame farY94.25 ideally fixed. No physical preload, service load, material,
thread strength or continuum contact pressure/stress has been qualified.
Point reactions are not surface pressure. The common planar regions omit
the same edge strips as the original auditor. No new FE/contact convergence.
No CAD, physical input null, dependency or workflow changed. All hardware go
flags remain false. The parallel PR25 candidate uses a different bolt branch
and is kept separate, not merged or described as repaired by these results.
