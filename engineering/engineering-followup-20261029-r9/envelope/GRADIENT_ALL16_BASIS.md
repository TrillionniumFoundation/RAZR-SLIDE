# Locally sensitive original-budget all16 run

The original-root width strategy remains preserved as its own all16 run. At
2,048 splits it retained 1.39e-6 to 2.73e-6 mm³ in the eight nonpassing frames.
A same-root 64-split gradient pilot reduced the R8 comparison bound by 27.3%,
to 1.3283819456541791e-6 mm³. Exact parsing memoization reduced that pilot's
13.0249 seconds to 7.4629 seconds. The entire serialized tree, including every
node, cut, failed channel, successful proof and rational volume, is byte-identical
between the cached and uncached gradient pilots; the comparison and hashes are
in EXACT_CACHE_PILOT_COMPARISON.json.

This second all16 strategy uses that same local-gradient selector and exact
parsing cache, with unchanged mathematical predicates and full displacement
boxes. Each selected cut remains an exact midpoint. The heuristic affects
only the cut axis; every claimed exclusion still requires the complete original
boundary source and a strict exact mathematical separator.

The original limits remain 4,096 global splits, depth24, 12,000,000 piece tests,
600 seconds and 805,306,368 bytes. The 7.4629-second pilot scales by the maximum
8,236 tested nodes /129 pilot nodes to approximately477 seconds, conservatively
repeating its input-read overhead at each block. This is a capacity estimate,
not a promise. The full driver reads all16 frames once and retains 1,537 roots,
including all44 non-tiny roots and every tiny positive volume. No positive root,
failure, full-D component, original source piece or threshold is removed.

All cost is recorded separately from the width run and the pilots. The independent
reader reconstructs the complete forest and requires strict quadric exclusion;
an enclosure classified unresolved cannot support an exterior-channel proof.
Conditional source-model progress does not qualify native BREP tolerance/error,
native bounded-face filling, native envelope topology or full continuousG2.
