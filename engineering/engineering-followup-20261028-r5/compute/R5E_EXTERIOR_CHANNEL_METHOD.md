# R5E: exterior channels through complete boundary covers

## Registered next method, before its first mathematical worker run

R4 kept a conservative box around every complete stored boundary piece and
intersected three independent coordinate-slab covers. Those slab covers use
transverse hulls and therefore lose spatial connectivity. This R5 method uses
the **same complete boundary boxes**, the **same original remaining displacement
boxes**, and the **same original float64 `1e-7 mm^3` threshold**. No native Common,
new geometric approximation, displaced endpoint sampling, trim-loop deletion,
or material change is required.

Let S be a compact closed material whose entire boundary is covered by the
registered closed boxes B_i. For a positive-volume candidate box C, choose one
coordinate and extend its open interior in one direction beyond the complete
material support box. The resulting open rectangular channel Q is connected,
contains the interior of C, and contains a point outside S. If every B_i is
disjoint from Q, then boundary(S) is disjoint from Q. The relatively open and
closed subset S intersect Q of connected Q must therefore be empty. This
certifies that the **open interior** of C is outside S. All C boundary faces
remain as zero-volume carriers; this method does not claim that the entire
closed C is disjoint from S.

For the translated union S+D, compactness gives
boundary(S+D) subset boundary(S)+D: if x=s+d were represented using an interior
point s of S, a neighborhood of x would lie in S+d. The existing boundary boxes
expanded by the entire original D therefore remain sufficient. No displacement
component is rounded to zero. For each intersected-material candidate cell it
is sufficient to find one exterior channel for either material.

A closed interval [a,b] misses an open interval (l,u) exactly when b<=l or a>=u.
Thus a complete boundary box misses an open channel if such separation holds
in at least one coordinate. Degenerate boundary boxes (including planar faces,
edges, and vertices) are retained and checked; the algorithm must not use
positive intersection volume as a test of boundary intersection. For a
successful channel the certificate records a separation coordinate and side
for **every** original boundary box. A failed channel records an actual
blocking box. Failure to find a channel is an unresolved upper bound, not a
material-intersection witness.

## Finite capacity basis

The existing R4 report registers 16 raw frame proofs with 1,474 positive cells
in total and at most 230 in one frame. The initial local witness is the saved
case-001/frame-1 stationary enclosure box, about 0.308578644 mm^3. For each
candidate cell the first version tries at most two materials times three axes
times two directions. Each candidate channel checks at most the complete
boundary-piece count. This is a finite O(sum_cells * sum_pieces) predicate,
with at most three exact rational interval comparisons per tested box.

The preflight worker will re-read all 16 original compressed proof identities,
count exact cells/pieces and the static comparison upper bound, and report its
actual time/RSS before an all-frame attempt is authorized by a new named
contract. A one-cell execution must precede that attempt. Each frame is read
and released sequentially; only compact output records are retained. The
original pure-math 600-second and 768-MiB limits, shared-memory ceiling,
disk floor, output cap, owned-child supervision, and canonical argument
bindings remain in force. An environment resource rejection is an actual
nonexecution; it cannot be called a mathematical pass.

## Qualification boundary

The proof retains R4's explicit premise that the complete stored
parameterizations cover the intended compact material boundary. It does not
establish OCCT native material semantics, native transformation/rounding error,
source-to-binary correspondence, physical tolerances, current-factory G2, or
G3--G5. The separate L2 tolerance diagnostic, if processed later, must retain
its original interpretation; this first raw-frame method does not requalify it.

All earlier actual failures, timeout records, coarse enclosures and exact
scientific originals remain unchanged. A separate verifier will reconstruct
channels and check every recorded separation directly, without importing the
producer or running a CAD kernel.
