# Correlated cylinder and plane-channel volume bound

## Original observations motivating the method

The full original-budget midpoint run ended with eight conditional nonpasses:
2.0226e-7 or 3.5546e-7 mm³ after4,096 splits. Its largest saved cell in
case-037/frame-2 has volume3.23146e-9 mm³. A complete twelve-channel scan found
that one source's +X channel is obstructed only by its original cylinder face0,
while the other source's −Y channel is obstructed only by original plane64 and
line154. The old prefix tests discarded this correlation.

The original exact source basis and complete nonzeroD yield a common projection
width2.71162e-15 and a conservative cell-volume bound8.97391e-20 mm³. This is an
exact-source calculation, with an outward rational square-root bound. It is
not a measured native gap or a native-material error certificate.

## Inclusion argument under the retained boundary-source model

Every channel starts in a boxB and reaches beyond the known whole-material box.
Every original boundary piece is accounted for, including faces, edges and
vertices. The existing coordinate/slab and exact primitive proofs exclude the
pieces marked with those proofs from the complete channel.

For a cylinder channel, every remaining piece lies on the same exact stored
cylinder. Write x=O+Xu+Yv+Zw using the inverse of the stored, unnormalized basis;
the surface satisfies u²+v²=r². The exact derivative of u²+v² in the outward
channel direction is nonnegative over the entire shifted channel, including
all originalD. A point with u²+v²>r² can therefore reach the known exterior
without crossing any boundary. Material inB must satisfy u²+v²<=r².

For the other material, choose a nonzero plane normaln for which the outward
channel moves strictly toward decreasing n·x. Bound the projection of every
remaining boundary piece from below byL. Plane and complete original Line
parameters provide exact bounds; other pieces retain their complete old carrier
projection. A point with n·x<L reaches the exterior without crossing a boundary.
That material inB therefore satisfies n·x>=L.

For all points of the first material inB, Cauchy–Schwarz gives

    n·x <= n·O + r sqrt((n·X)²+(n·Y)²) + max(w n·Z) + max(n·d) = U.

The complete boxB−D bounds the axial coordinatew using the exact third dual
basis. The square root is rounded upward as a rational number and checked by
squaring; no normalization or dropped small coordinate is permitted. Thus the
intersection lies in B intersect {L<=n·x<=U}. If U<L it is empty. Otherwise,
integrating along any axisj with n_j nonzero bounds its volume by

    min(volume(B), (U-L)/abs(n_j) * product(width(B_k), k!=j)).

This upper bound is nonnegative and conservative; it need not equal the exact
volume of the clipped polytope. Closed surfaces and cell boundaries are retained
as zero-volume carriers. Box partition volumes remain separately exact. The
sum of the per-cell upper bounds is tested against the unchanged binary64
1e-7 mm³ gate.

## Scope and cost

The assumptions are precisely the existing conditional serialized boundary
source model and its exterior-channel topology. Native bounded-face filling,
compiled geometric error bounds, valid native envelope BREP topology and full
continuousG2 are still unqualified. This method never converts a finite native
Common result into a continuous proof.

The complete new run starts from all1,537 original roots, not from a free cached
four-thousand-split result. It retains the original total4,096-split, depth24,
12-million-piece, 600-second and805,306,368-byte limits. A bounded pilot on the
actual saved cell must independently verify its channels and bound before the
new whole-root strategy is admitted. All prior computations and failures keep
their separate complete costs and original identities.
