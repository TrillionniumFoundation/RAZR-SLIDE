# Exact parsing cache cost pilot

The first local-gradient 64-split pilot completed in 13.0249 seconds and retained
1.3283819456541791e-6 mm³, compared with the old width pilot's
1.8265251752744962e-6 mm³. Its 27.3% smaller bound is still above the unchanged
1e-7 gate, and does not itself justify expanding any execution budget.

Most piece predicates repeatedly parse unchanged exact rational source boxes
and slabs. This pilot memoizes only that parsing, retains the original objects
to prevent id reuse, and applies the same coordinate and slab inequalities in
the same order. There is no new rounding or geometric predicate. The existing
independent exact reader will check every actual inequality after execution.

The same original case-037/frame-2/root66, 64 splits, depth24 and fullD are used.
The cap remains 60 seconds/805,306,368 bytes. The time measurement decides whether
the new selector can support a complete original-budget all16 run. The output
retains the full node tree so its exact equality with the uncached pilot can be
checked before relying on the speedup.
