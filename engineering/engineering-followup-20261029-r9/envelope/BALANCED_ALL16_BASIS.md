# R9 balanced all-frame computation

The R8 balanced64 pilot used the original largest root of case-037/frame-2,
without changing the full nonzero displacement. At 64 midpoint splits it reduced
the root's retained bound from 0.010882104898799036 to 1.8265251752744962e-6 mm³,
with maximum depth 16, 72,044 actual piece tests, 9.082437155 seconds and
194,891,776-byte peak RSS. This result is a capacity/trend observation, not a pass.

The next computation restarts from all original V5 roots carried by the V6
certificates, rather than from the V6 tree whose endpoint-first cuts used the
global split budget in the first failed frame. The original complete root census,
boundary source pieces, coordinate/slab predicates, exact stored primitive
parameters, full displacement boxes and exact binary64 1e-7 threshold are kept.
All 16 frame certificates are included. There are 1,640 roots, only 44 of which
exceed the original tiny-leaf threshold; tiny roots remain included in the sum.

A single priority queue selects the largest exact retained volume across frames,
with frame, root and node indices as deterministic ties. Each selected box uses
the R8 radial midpoint rule. An already passing frame stops splitting while
retaining its complete residual bound. No positive volume is discarded. Every
parent is partitioned exactly into two equal-volume children. Closed partition
boundaries remain zero-volume carriers under the conditional source model.

The new computation has its own full cost record and retains the original
limits: 4,096 global splits, maximum depth 24, 12,000,000 boundary-piece tests,
600 seconds and 805,306,368 bytes address space. At most 44+2*4096 non-tiny nodes
are tested. The R8 measured 72,044 tests/129 nodes indicates about 4.6 million
piece tests for this ceiling; the complete 9.08-second pilot scales to about
580 seconds, including repeated pilot input setup, while this run loads each
frame once. These are conservative count/time estimates, not guarantees.
Actual exhaustion, failures and partial bounds remain recorded as unresolved.

An independent process will reopen the original inventories, use the existing
independent exact-arithmetic source checker, reconstruct every root and child,
check all complete exterior-channel claims, sum every remaining positive leaf,
and enforce the unchanged total split/depth/volume gates. A valid conditional
bound does not establish native BREP error bounds, valid envelope topology,
bounded-face filling, complete continuous G2, or current K1/K3 structural safety.
