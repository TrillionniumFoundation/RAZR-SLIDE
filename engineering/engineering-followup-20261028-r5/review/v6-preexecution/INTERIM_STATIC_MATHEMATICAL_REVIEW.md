# V6 independent static review — before final lock/workflow readback

This document records a source review of the proposed V6 primitive support refinement. It is not an execution certificate. No V6 producer, helper, or checker was imported or run by this reviewer. The source-only lossless audit is preserved separately and establishes the original face/material/actual-leaf identities.

## Mathematical findings

### Complete source parameter intervals

The prior R4 `face_domains` implementation includes the stored surface U/V intervals and the support ranges of every original pcurve occurrence. For the V6 targeted cylinder class, the helper and independent checker both retain these surface intervals and extend their hulls with both endpoints of every original Line pcurve over its full first/last parameter interval. They require identity placements and mapped occurrences; unsupported data keeps the complete old face. This agrees with the inherited original-domain interpretation. It does not verify native face-class membership or substitute native error bounds.

The cylinder domain is divided into exactly 64 closed, consecutive U intervals. The original global endpoints, each shared endpoint and full V interval remain present. A patch is removed only when a coordinate interval has strict lower-greater-than-upper inversion after intersecting with the old stationary box. Equality and zero-width intervals remain. Each surviving box and support slab receives the full original D; fixed-material D is exactly zero.

### Rational trigonometric enclosure

The 24-term sine polynomial has degree 47, and the 24-term cosine polynomial has degree 46, which is also its degree-47 Taylor polynomial because the degree-47 coefficient is zero. The common Lagrange error bound `abs(c)^48 / 48!` is valid for both under the exact real sine/cosine model. The dyadic centre changes only the expansion point; it never replaces a source U endpoint.

For `g(u) = A*cos(u) + B*sin(u)`, the constant and first derivative at the centre are enclosed using the rational sine/cosine intervals. For the exact offset interval d, the second-order remainder has magnitude at most `(abs(A) + abs(B))*max(abs(d))^2/2`. Interval multiplication of the derivative range and the entire offset interval therefore conservatively encloses every parameter point. Correlation is allowed to be lost; containment is retained.

The independent checker evaluates the polynomials by reverse Horner evaluation rather than the producer's forward recurrence. It recomputes every patch certificate, unclipped/clipped coordinate box, complete domain and support value and compares the entire source certificate object.

### Exact source support constraints

The plane normal is the exact cross product of the stored X/Y vectors, with nonzero and orthogonality checks. Its stationary support is `n dot O`; sweeping adds the exact support interval of the complete D.

The cylinder radial normal solves `n dot X = A`, `n dot Y = B`, `n dot Z = 0` for exact stored basis vectors. It does not assume the serialized basis is orthonormal. The producer uses cofactors; the independent checker uses rational Gaussian elimination and then checks all three equations. The resulting radial support is enclosed by the same justified trigonometric expression and exact displacement support.

A nonzero normal maps a positive open box to the open interval between its exact extrema. Therefore a closed support slab with upper endpoint no greater than the open lower endpoint, or lower endpoint no less than the open upper endpoint, is disjoint from that open box. The checker verifies these inequalities directly for each saved separation code. It requires one registered slab when a nonaxis code is used. Existing whole-material support boxes remain the known-exterior anchors; a newly smaller hull is not substituted as an unproved exterior premise.

### Complete forest and volume accounting

Each new root is an actual retained leaf from immutable V5 evidence. Existing V5 exclusions stay separate. New full-phase volume is computed from the sum of the new retained leaves, then compared with the old coarse whole-material upper bound. New exclusions are never subtracted from an already selected minimum bound.

All positive tiny leaves, unresolved leaves, pending leaves after a predicate budget stop, and path/split limit leaves remain in the retained volume. Both split children have positive directed measure and exactly conserve their parent. All root/cut boundaries remain closed zero-volume carriers. No omitted, duplicate, unreachable or unfilled tree node may pass independent verification.

### Registered cut selection and controls

Before a cut, the independent checker requires all 12 recorded channel identities in the registered order and verifies that every available axis/slab separator fails on each recorded blocking piece. It independently reconstructs the first-choice interior endpoint. If none exists, it reconstructs the explicit midpoint rule: largest radial-slab variation first, then other slab variation, then longest interval, with the first axis resolving a tie.

The drafted checker separately supports actual and analytic controls. The analytic all-retained/no-excluded case checks a complete closed unit-box boundary, all 12 unresolved channels and the explicit inapplicability of excluded-leaf and split mutations. It does not count synthetic controls as original-case branch coverage. Primitive mutations operate on real copied certificates and report a specific missing-target branch as not applicable.

## Execution contract findings

The current driver orders five stages: selected actual leaf, independent selected-leaf verification, all-frame source-capacity preflight, full bounded refinement, independent full verification. Any nonzero supervisor result, incomplete owned receipt or incomplete scientific report stops later stages. Full work additionally requires a positive excluded amount, a selected-leaf conditional bound within the unchanged original threshold, at least one applied cylinder and independent agreement.

The original owned process limits remain 600 seconds, 805306368 bytes RSS, shared ceiling 7301444403 bytes, free-disk floor 104857600 bytes, output bound 41943040 bytes and metadata margin 4194304 bytes. No missing RSS observation is silently converted to zero. The new algorithm has separate 12000000 piece and 12000000 elementary-inequality budgets, 4096 splits and depth 24. Mid-piece budget exhaustion retains the full leaf. The finite full forest bound is 1537 initial roots plus at most 8192 added nodes and 4096 added leaves.

The producer and driver bind all 25 immutable actual V5 members, complete report/controller/contract identities, the frozen V5 source lock, original R4 inputs, the new full source projection and exact selected root/leaf. Actual source-only recovery does not replace the required independent geometric recheck of prior V5 certificates in the V6 verification stage.

## Status at this checkpoint

No blocking mathematical issue has been identified in the reviewed helper, producer, driver or complete independent checker. The main routine has now been read, including the exact prior archive/contract/owned-receipt bindings, original proof recheck, selected whole root and leaf, complete new root coverage, directed sums, counts, real control applicability and ending source/input hashes. It uses the actual frozen V5 capacity object for inherited V5 routines, separately from the V6 limits.

The final checker delta additionally binds the original R4 whole-volume sanity gate and inherited upper bound. Its Taylor negative control finds an actual patch with positive rational error, deletes that error and preserves its original value in the control record. No actual patch means explicit not-applicable status. The complete checker was parsed as AST only at 95688 bytes / SHA-256 `05f7d1d76096e0518943bbdfbf6d5da7ae6a91248f83ef6e98432ae168df29bd`.

Final complete source-lock and concrete branch-constrained workflow identities remain pending at the creation of this note. A separate bounded final readback will bind this mathematical review to those exact bytes. Static review supplies no actual execution or mathematical qualification result.

The source-only audit result is a provenance closure. Conditional primitive/trim semantics remain explicitly separate from native material membership, original raw qualification and full continuous G2. There is no actual V6 execution result at this checkpoint.
