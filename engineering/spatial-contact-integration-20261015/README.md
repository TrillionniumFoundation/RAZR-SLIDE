# Original panel/frame spatial contact: verified bounded delivery

Current result: complete local 873 tests / 31 suites pass. Original cases0..3
also pass the unchanged 1e-7 mm criterion on all5255 common polygons per case,
with independent full-field and tetrahedral P2 reconstruction.

Case4 is NOT accepted: after72 finite-QP/audit cycles with2193 contact points,
2261 regions remain below the same criterion; independently recomputed minimum
is -6.89005779769651e-7 mm. Cases5..7 were not run after this bounded stop.
Full volume energy and point equilibrium do not override that failed gap test.

See DELIVERY_VERIFICATION.json, METHOD_AND_LIMITS.md and each case directory.
The exact bounded force-response matrix and contact-point locations are
included for continuation, together with hash-pinned complete meshes/loads.
Large full stiffness and solution fields remain at documented host paths.
No CAD, real physical inputs, dependency or workflow changes. No continuum
pressure, stress, mesh convergence or hardware release is claimed. All go=false.
INITIAL_README.md preserves the original draft note, not the current status.
