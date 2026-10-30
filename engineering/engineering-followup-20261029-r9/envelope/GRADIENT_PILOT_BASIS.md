# Local sensitivity pilot

The concurrent full16 balanced-width run reached 2,048 splits in 266.60 seconds
with all eight initially failing frames still at 1.39e-6 to 2.73e-6 mm³.
Its unchanged 4,096 split cap may therefore leave the original 1e-7 gate unmet.
The driver retains that complete outcome. This separate 64-split pilot asks
whether local radial sensitivity is a better axis selector than basis width.

It uses precisely the original case-037/frame-2 root66 from the R8 balanced64
pilot, with the same root, source pieces, fullD, exact predicates, 64 split
budget and depth24. Only axis selection changes. The score uses local exact
quadric gradient plus the one-axis quadratic variation, normalized by radius².
The score is a heuristic for selecting a midpoint, never an exclusion proof.
The complete actual-D predicate remains authoritative at every tested child.

The prior identical root/64-split work took 9.08 seconds/72,044 piece tests.
This pilot allows 60 seconds and 805,306,368 bytes; at most129 nodes are tested.
Its cost and all exact-node evidence are additional to the all16 computation.
An improvement alone does not grant clearance, native inclusion or fullG2.
