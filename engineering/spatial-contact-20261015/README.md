# Spatial unilateral contact study — current execution pending

Continues PR24 without changing CAD, material inputs, old meshes, springs, fixture assumptions, dependency lock or CI workflow. The previous mean-pressure field is retained as a failed local-contact control.

`integration/spatial_contact.py` implements an equality-constrained convex dual with nonnegative independent spatial normal reactions, unilateral tensile springs and explicit rigid modes. Each finite contact point is tested; a separate whole quadratic-cell audit is mandatory. Missing support is rejected, not numerically grounded. Bounds or iteration limits never constitute success.

The driver reassembles and factors the complete existing quadratic-displacement/linear-geometry body matrices, computes true new load-response columns, and inserts negative-gap extrema as extra constraints. Point-force multipliers are a discrete weak reaction, not a smooth continuum pressure/stress distribution. Both the finite constraint solve and the 5255-cell between-point audit must pass before any discrete-field acceptance. The common mesh domain excludes documented edge strips; finite rotations, material, actual preload, full-device contacts and FE mesh convergence are not qualified.

21 new unit tests pass; 24 shared-domain cases agree with the previous exhaustive solver. Full835/31 and adaptive full-field diagnostics are pending at this functional commit, not inferred from configured counts. No hardware, procurement, supplier, billing or branch-protection action. All hardware/manufacturing go flags remain false.

Primary formulation references: https://getfem.org/userdoc/model_contact_friction.html ; https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html . These support the discretization/optimization background, not this product or its unmeasured materials and loads.
