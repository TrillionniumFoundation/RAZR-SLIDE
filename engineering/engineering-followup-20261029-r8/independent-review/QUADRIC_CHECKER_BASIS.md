# Independent R8 exact-source checker

The checker is independently authored and imports only the Python standard
library. It does not import the R8 producer, the earlier primitive helpers,
CadQuery, OCP, NumPy, or a numerical optimizer. All geometric comparisons use
`fractions.Fraction`. The source input remains the complete original record,
including its small nonzero components and original parameter intervals.

## Cylinder inclusion

Let the source cylinder be

\[
p=O+rX\cos u+rY\sin u+Zv.
\]

The stored vectors need not be exactly orthonormal. For nonzero
\(\Delta=X\cdot(Y\times Z)\), define
\(a=(Y\times Z)/\Delta\) and \(b=(Z\times X)/\Delta\).
Exact rational arithmetic verifies

\[
a\cdot X=1,\quad a\cdot Y=a\cdot Z=0,\qquad
b\cdot Y=1,\quad b\cdot X=b\cdot Z=0.
\]

Consequently every point of every original angular or axial patch satisfies

\[
Q(p)=(a\cdot(p-O))^2+(b\cdot(p-O))^2=r^2.
\]

Replacing a trimmed patch with this complete unbounded cylinder enlarges
the source set; it does not omit any parameter or trim boundary. A circle
admits the same enlargement along any third vector making the stored basis
nonsingular. No closed-form claim depends on a rounded vector being unit
length. A singular basis is rejected.

For an original boundary-piece carrier \(B\), a complete exterior channel
\(C\), and the original full displacement box \(D\), every possible source
point contributing to that channel lies in the stationary query box

\[
S=(B\cap C)-D.
\]

The subtraction retains both original endpoints of every coordinate of
\(D\). It is an enlargement when a displacement has correlations beyond
the box, and remains conservative. The checker recomputes this query from
the original piece and channel rather than trusting the claimed query.

## Exact extrema on a box

The function \(Q\) is positive semidefinite of rank two. A convex function
on a box attains its maximum at one of the eight vertices. To obtain the
minimum, the checker enumerates all 27 combinations of free, lower, and
upper status for the three coordinates. On each face with nonsingular
restricted Hessian, rational Gauss–Jordan elimination finds its unique
stationary point. Feasible stationary points and all vertices are evaluated.

This enumeration also covers degenerate and singular faces. If a minimum
lies in the relative interior of a positive-dimensional face whose
restricted Hessian is singular, a nonzero null direction leaves its value
unchanged. Following that direction to a proper face preserves the
minimum. Repeating reaches either a nonsingular stationary face or a
vertex. Zero-width coordinates merely repeat valid candidates.

The resulting minimum and maximum are exact. A producer may report a
looser interval, but it must contain both independently derived extrema.
Exclusion requires a strict inequality: \(\max_S Q<r^2\) or
\(\min_S Q>r^2\). Equality and an interval spanning \(r^2\) remain unresolved.

## Affine primitive checks

For a plane, the checker recomputes \(X\times Y\), its constant support,
and the complete projection of the query by enumerating all eight corners.
Only strict separation certifies exclusion.

For a Line, one shared parameter must satisfy all three coordinate
inequalities and the complete original parameter interval. Each nonzero
direction component gives an exact parameter interval. A zero component
is checked as a constant coordinate. Their intersection must be genuinely
empty; a tangent point is retained. The complete ordered parameter trace
is compared with the producer's trace.

## Source and whole-channel scope

Every claim is checked against the original record's full canonical hash,
kind, index, identity placement, equal local/global source record, unchanged
displacement, and original carrier. The surrounding independent reader must
also reconstruct the original leaf, its complete channel, and all pieces;
one verified primitive claim cannot replace complete channel coverage.

The new support functions establish conditional serialized-source geometry
only. They do not establish exact native BREP filling, a bound on native
kernel error, physical manufacturing uncertainty, contact force, or full
continuous G2. Earlier successful and unsuccessful runs remain separate.
The R8 method does not need a new spatial split to evaluate an existing
depth-24 leaf. Any later split would need an explicit new scope and must
not be credited as preserving the original depth limit.
