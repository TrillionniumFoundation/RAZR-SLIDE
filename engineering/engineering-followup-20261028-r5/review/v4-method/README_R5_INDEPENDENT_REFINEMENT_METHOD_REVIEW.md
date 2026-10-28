# R5 V4 endpoint refinement: independent method and source review

## Result and boundary of this review

The reviewed method preserves the conditional volume upper bound. Its exact binary partition, positive directed volumes, retained closed carriers, full treatment of tiny leaves, and treatment of pending leaves at budget limits are consistent. A source-level prerequisite-binding gap was identified, reported to the author, corrected by the author, and then read back. No static blocking finding remains in the source snapshot identified by the adjacent JSON report.

This is a cross-author review of the method, producer, independent checker, and portable driver. The reviewer did not import or execute the V4 producer/checker and has no V4 result to certify. Existing V3 records were only read back. Formal execution, actual negative-control outcomes, owned resource qualification, and frozen source identities still have to support any subsequent result. The review does not declare a native material, full G2, FE, or physical gate pass.

## Why the partition is conservative

For a positive parent box `B = [l0,u0] × [l1,u1] × [l2,u2]`, a cut `c` strictly inside one axis interval creates two closed child boxes by replacing that interval with `[l,c]` and `[c,u]`. Their union is exactly the parent. Their intersection is the closed cut rectangle, which has zero three-dimensional volume. Each child retains positive diagonal side lengths, and exact rational arithmetic proves `V(left) + V(right) = V(parent)`. The separate verifier reconstructs these child boxes from the original root and the split record; it does not accept arbitrary declared child geometry.

A finite full binary tree therefore preserves the root's complete closed set when its leaves and cut carriers are considered together. Root faces and all cuts are implicit, exactly reconstructible carriers; explicit flags require them to remain represented. An excluded leaf loses only its open interior, and only after the separate V3 complete-boundary channel checker proves a path to known exterior with every source boundary box accounted for. An unresolved leaf stays at its entire positive exact volume. Conditional on the original raw-cover and material-boundary premises, the material intersection is covered by retained leaves plus finitely many zero-volume carriers. Its volume cannot exceed the sum of retained leaf volumes. Taking the minimum with the independently established original coarse support bound is also conservative.

This argument establishes a finite affine box complex and a conditional measure bound. It does not construct or validate new native CAD solids, certify the inherited boundary semantics, or turn an unresolved bound into a material collision witness.

## Thin layers, limits, and complete coverage

The `Fraction(1e-7)/100000` condition stops refinement of a small positive leaf; it never discards that leaf. The producer adds its whole exact directed volume, and the checker reconstructs and checks that volume. Clearance is still compared to `Fraction(1e-7)`, the exact value of the original binary64 threshold. The full displacement intervals are matched against the original R4 proof, and the source covers are reconstructed with `stationary=False`.

The limits are 4096 global splits, depth 24, and 12000000 global complete-boundary predicates. If a predicate budget is exhausted partway through a channel search, the result is unresolved. The leaf is retained, not given a false all-blocked or exclusion certificate. The pending stack is processed to exhaustion, and later roots and frames are still visited. Split/depth limits prevent further subdivision but do not omit children. Each original root must occur exactly once and in the original order; each allocated tree node must be reached exactly once. The independent checker rejects missing roots, missing/duplicate children, cycles, unreachable nodes, incorrect directed volumes, and lost carrier flags.

For the original 1474 roots, the binary-tree identities give at most 5570 leaves and 9666 nodes. These are algorithm bounds. The rough 36.73-second estimate in the basis is not a runtime proof. The original owned supervisor, time/RSS/shared-memory/disk/output limits, and actual preflight remain qualification conditions.

## Real counterexample and prerequisite-chain correction

The saved selection for `case-001`, frame 1, original cell 202 was checked against the actual V3 certificate from run `40641230212`. Its full record is exactly equal, its disposition is retained, and the saved pipeline/all-raw/independent report and certificate size/SHA identities match the actual local records. This was a readback of an existing remainder, not a new generated witness or new material Common.

The initial V4 worker checked that prior producer phases had completed but did not require the selected-cell clearance pass or bind the completed single independent verification and its owned receipt. The portable driver had the proper ordering, but a later worker contract did not carry the full independent prerequisite chain. After feedback, the author added `independent_single_verification` to later contracts. The worker now requires the original single pass and an actual split, the independent single phase/pass, successful owned receipt/exit/resource state, contract and output binding, and exact identity of the producer report that the independent checker verified. The independent checker records its contract SHA and verified producer identity and checks its contract again at completion.

The driver deliberately runs independent verification of a completed single result even if its clearance gate fails, preserving a checked failure certificate. It then withholds preflight and all16 work unless the selected cell passes the unchanged threshold. This correction was reviewed in source; its runtime behavior is not claimed as executed here.

## Negative controls and remaining interpretation limits

The checker contains 16 targeted controls: three phase controls, two original-root coverage controls, seven partition controls, and four complete-boundary channel controls. Added cases mutate an actual tree to omit a pending leaf and to replace the actual smallest positive leaf volume with zero. Their actual execution and rejection outcomes are pending. The smallest-leaf case records its actual kind and exact volume; it must not be described as a tiny-retained-leaf control unless the eventual result demonstrates that classification.

The checker proves geometric coverage independently of the producer, but it does not independently replay the full channel exploration count or every reason for conservative retention. An inaccurate stop-reason label would affect trace provenance, while keeping the entire exact volume remains mathematically conservative. This distinction should remain explicit in downstream reporting.

All original failures, unresolved bounds, displacement intervals, thresholds, and source records remain unchanged. Successful qualification of a V4 conditional raw bound would still leave native material semantics, compiled error, the separate L2 diagnostic, the full current mechanism domain, FE/tolerance work, and physical G3–G5 to their own evidence and gates.

## Review artifacts

`R5_INDEPENDENT_REFINEMENT_METHOD_REVIEW.json` records all source hashes, function locators, readback identities, exact constants, method checks, the corrected finding, and explicit non-claims. `R5_INDEPENDENT_REFINEMENT_METHOD_REVIEW_MANIFEST.json` binds this note and the machine-readable review. Source-lock changes or edits to the reviewed methods require an addendum rather than silently treating a different source as reviewed.
