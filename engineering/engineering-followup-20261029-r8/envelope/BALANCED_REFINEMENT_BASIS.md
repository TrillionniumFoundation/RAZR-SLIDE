# Balanced original-root experiment

The complete zero-split R8 replay tested 3,215 of the original 4,943 retained
leaves. It excluded 2,944 and retained 1,999, while keeping all 16 exact
positive-volume sums and the original 8/16 pass count. The production run
took 121.3924 s and its independent reader passed in 95.586 s.

The saved remaining volume is concentrated in few coarse boxes. In original
case-028/frame-1, V6 root 76 contributes 0.00431588387528205 of the original
0.004396435272042011 upper bound. Its largest retained node 47 has reached
depth 24 while still spanning approximately 0.06588 by 0.13311 by 0.4 mm.
The old endpoint-first strategy made highly unbalanced cuts. Seven other
nonpassing frames contain large depth-zero leaves because the global split
budget was consumed in the first nonpassing frame.

This named experiment starts again from an original V5 retained root and
retains the previous V6 and zero-split R8 results unchanged. Its work is a
new computation, recorded separately, not a subtraction from prior costs.
The pilot selects the largest remaining leaf, with exact-volume descending
and case/frame/locator lexicographic ties. In the current saved result this
is case-037/frame-2, root 66, with no previous V6 split.

Within that root, use a priority queue keyed by exact pending volume, then
node ID. For each pending box, prefer Cylinder/Circle radial directions in
its actual failed channels. Axis k is scored by the maximum
`(|a_k|+|b_k|)*(box_hi_k-box_lo_k)` over these exact stored dual bases.
Bisect the largest score at the exact midpoint, with the lowest axis index
breaking ties. If there is no failed radial primitive, use the longest
axis. No parameter or material domain changes. This removes the old
endpoint-cut bias while preserving all original carriers, D, source order
and the exact source correlation predicates.

The initial pilot permits 64 new splits, inherited/new depth at most 24,
60 seconds and 805,306,368 bytes. A binary tree with 64 splits has at most
129 tested nodes; the zero-split pilot already measured 64 actual tested
leaves in 3.9602 seconds. The pilot records all nodes, failed observations,
exact partitions, full successful-channel proofs, final remainder and CPU
resource observations. A larger execution is contingent on the actual
remaining-volume trend and timing, and retains a global 4,096 split and
depth-24 limit. It does not claim native-error or full G2 qualification.
