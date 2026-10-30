# Independent source review of the frozen-participant acceleration

This review concerns `geometry/frozen_predicate_v2.py`, the v2 finite-factory
producer, and the exact S4 `integration/product_assembly.py` and
`integration/straight_envelope.py` sources. It is a source-level justification;
the completed producer, independent readback and row-by-row comparison reports
remain necessary for the actual finite-state result.

The original `single` predicate validates the complete topology through
`whole_material`: every material leaf is a valid solid with positive finite
signed volume, aggregate and raw directed volumes agree at the original
tolerance, and exactly one complete solid is present. It returns the input
shape without repair, orientation normalization or material extraction.

The original `bounds` routine uses `BRepBndLib.AddOptimal_s` with both
triangulation and shape-tolerance flags false, and returns the same axis order
used by `strict_common`. The new frozen table calls those unchanged predicates
on every complete participant before retaining its bounds. A strict positive
axis gap therefore applies the same broad-phase criterion to the same validated
material. Neither a zero gap nor a negative gap becomes an exclusion.

For all other pairs, the new code calls the original `strict_common` on
explicit deep geometry copies. The inspected CadQuery copy source calls
`BRepBuilderAPI_Copy(self.wrapped, True, mesh)`. The source check is fail-closed
when this implementation cannot be recognized. No original participant is
passed directly into a Boolean by the frozen module. BREP bytes are hashed
before and after the complete pair matrix; any changed participant invalidates
the frozen-state claim.

The actual separate-process reader must reopen the saved STEP and BREP files,
check the original participant signatures and all original early contact gates,
reconstruct the complete unordered pair roster, evaluate every pair, retain
all directed Common differences and failures, and recheck its own frozen
participant fingerprints. Reusing the small predicate implementation does not
make this a second CAD kernel. A complete matrix includes native Common calls
and strict positive-axis-gap exclusions; its row count is not a Boolean-call
count.

The v2 pilot uses the genuinely saved first v1 factory. It must not be described
as a second factory construction. The v1 and pilot pair records must be compared
row by row, including method, signs, Common values and failure sets. The original
four-state v1 campaign remains incomplete if it is stopped after its first
complete state; successful state records do not rewrite that campaign status.

This reasoning does not qualify continuous motion, actual independent actuator
reachability, native swept-envelope filling, physical materials, minimum wall
strength, preload or G3–G5. Those retain their original separate obligations.
