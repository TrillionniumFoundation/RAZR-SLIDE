# Face-preserving volume enrichment — 2026-10-17

Base main: 85a86ce6e15e48186afcdf36ec665ebb7a902653. CAD, material/load inputs, 3mm screws, original contact surfaces and numerical gauges are unchanged.

Every original P2 tetrahedron is split through its centroid into four child tetrahedra. A second nested level splits each child again. Original faces and their six P2 trace nodes remain unchanged. Each first-level parent introduces five internal scalar nodes / fifteen vector DOFs. These unknowns are solved locally and statically condensed, not constrained to zero. Level2 recovers top and child internals recursively. Complete local child strain energies and internal residuals are checked after reconstruction.

The original coarse stiffness is independently reassembled with explicit degree-two tetrahedral quadrature, then compared with the frozen whole K. Unit cases cover symmetry, rigid modes, affine energy, nesting, orientation, positive/negative input controls and recovery. A separate scikit-fem script explicitly meshes all four/sixteen children and independently integrates and eliminates its internal DOFs for 12 nondegenerate shapes. This is a numerical implementation check, not physical validation.

Only volume-interior approximation changes. Face traces are deliberately held fixed so the contact domains and force maps remain directly comparable. This is NOT uniform h refinement: original face edge lengths do not shrink. The three nested spaces cannot establish surface/trace or continuum convergence. No pressure/stress or error bound is inferred from differences between two responses.

The frozen nodal input vectors contain nonboundary entries of order1e-17. The first overly strong surface-only assertion refused these. All entries are retained unchanged on the original skeleton DOFs; new internal DOFs have zero applied loads. No round-to-zero modification of the old loads occurs.

`frozen_load_response.py` holds prior contact/bolt forces fixed while changing the elastic volume space. It is deliberately a sensitivity experiment, NOT a new unilateral-contact solution. All such fields undergo the original whole-quadratic gap audit. Any negative-gap witnesses remain failures; old same-grid passes are not transferred to new energies.

Local u.T K u can lose relative precision when local rigid displacement dominates strain. The first recursive scalar-energy check exposed this cancellation. Final recovery evaluates strain directly on the finest tetrahedra, without changing any displacement, stiffness, contact tolerance or force. Both the finest integral and the full global work/energy check are retained.

`solve_enriched_contact.py` recomputes every C.T K^-1 C entry with the new complete condensed energy. It imports no old response matrix; old case6 points and forces serve only as starting guesses. The unchanged unilateral QP, explicit rigid equilibrium and1e-7mm whole-domain audit remain. `verify_enriched_contact.py` independently reconstructs tetrahedral point-force maps, audits all5255 shared regions and recovers the added interior displacement DOFs. A completed result requires this check; syntax or frozen-traction checks cannot substitute.

Physical E, material batch, installed preload, stiffness/torque/strength, actual support conditions, friction and loads remain unknown. E=1 and nu=.3, initial spring force, linear positive bolt branch, neutralY mode and ideal remote-frame fixation remain stated model assumptions. Existing uncovered edge strips remain uncovered. No geometry, machining, powering, torque, procurement, supplier or billing/protection action.

Implementation reference for exact elimination and recovery, not copied results: NGSolve static-condensation documentation, https://docu.ngsolve.org/nightly/i-tutorials/unit-1.4-staticcond/staticcond.html . The scikit-fem API `condense` (prescribed-DOF elimination) is not confused with the internal Schur complement used here.

Actual completion status belongs in DELIVERY_VERIFICATION.json when generated; configured test counts alone are not pass evidence. candidate_go=false; fixture_fabrication_go=false; manufacturing_go=false.
