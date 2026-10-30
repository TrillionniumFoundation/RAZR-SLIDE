# R8 independent geometric readback

The new exact-source Cylinder/Line correlation has a verified positive result
at the original depth-24 parent and a verified, limited improvement over all
16 saved frames. **The all-frame conditional pass count remains 8/16.**
Native error bounds, native bounded-face filling, full continuous G2, current
candidate mechanics, and physical G3–G5 are not qualified by this result.

## What the independent implementation checks

`quadric_checker_r8.py` derives Cylinder extrema from the exact stored basis
using independent rational Gauss–Jordan active-face enumeration and all
eight corners. It checks Line parameter feasibility using one shared original
parameter, and Plane support by independent corner enumeration. It does not
import the producer, old primitive helpers, CadQuery, OCP, or NumPy.
The inclusion argument and handling of singular faces are recorded in
`QUADRIC_CHECKER_BASIS.md`.

The surrounding readers reopen the full original native producer and reader
inventories, compare all selected complete records, bind the old V6 certificate
hashes, and rebuild every relevant original tree box and its inherited depth.
They then reconstruct each full exterior channel and check all recorded
coordinate, slab, and newly derived primitive proof codes. A positive result
requires complete boundary coverage, not only one successful primitive.

## Original parent at depth 24

`attempt-depth24-1/report.json` checks the producer's
`envelope/attempt-depth24-2/report.json` against original parent `[78,375]`
of `case-028/frame-1`. The parent has inherited depth 24 and is not subdivided.

| Independent result | Count |
| --- | ---: |
| Complete original channel observations | 12 |
| Valid recorded piece proofs | 787 |
| Unchanged coordinate/slab proofs | 783 |
| New exact Cylinder proofs | 4 |
| Complete successful channels | 2 |
| Preserved failed channels | 10 |
| Additional splits | 0 |

The successful channels are the fixed source's +X and +Y channels, each
covering all 179 original pieces. Both original material sources retain their
523/179 piece counts. The new proof excludes this original parent's open
interior under the new serialized-source model. It does not reuse the older
depth-25 child as a depth-24 qualification.

The independent run completed in 5.732644608 seconds. Seven actual mutations
were rejected for the expected source, complete-coverage, displacement, depth,
or mathematical reason. Seven analytic controls also passed.

## Complete all-16 zero-split reread

`all16-attempt1/report.json` checks all 16 complete reclassification gzip files,
not sampled summaries. It checks 32 whole original native material records
against the producer and separate-reader inventories.

| Independent result | Count |
| --- | ---: |
| Original retained leaves accounted for | 4,943 |
| Original pass/tiny leaves preserved without a new test | 1,728 |
| Retained leaves actually retested | 3,215 |
| Newly excluded leaves | 2,944 |
| Remaining retained leaves, including pass/tiny leaves | 1,999 |
| Complete or failed-prefix channel observations | 26,486 |
| Valid piece proofs | 1,485,914 |
| Original coordinate/slab proofs | 1,482,970 |
| New Cylinder/Circle quadric proofs | 2,878 |
| New Line proofs | 66 |
| Preserved failed-channel prefixes | 23,542 |
| New splits | 0 |
| Conditional frame passes, before and after | 8 / 16 |

The 1,485,914 valid piece proofs plus the 23,542 tested blocking pieces equal
the producer's 1,509,456 piece-test count. Each original retained leaf has one
and only one result. The reader verifies exact rational conservation in every
frame:

`old retained volume = new excluded volume + remaining retained volume`.

Every inherited depth remains at most 24. The previous 4,096 splits remain in
the original tree and no new split is added. The acceptance threshold is the
unchanged exact rational value of the original binary64 `1e-7`, not a rounded
replacement. The original tiny-leaf rule is unchanged.

The independent full readback completed in 95.586165548 seconds with peak RSS
313,294,848 bytes, using Python 3.12.14. The run qualifies this standard-library
exact-arithmetic reader; it is not a rerun of the older 43-package CAD runtime
qualification.

## Remaining positive upper bounds

The largest change in the deeply subdivided frame is
`case-028/frame-1`: its conditional upper bound decreases from
`0.004396435272042011` to `0.0043538410885977895 mm³`. The original
`1e-7 mm³` gate remains unmet. The complete exact rational values are retained
in the producer and independent reports.

| Still-unqualified frame | Remaining upper bound, mm³ (display only) |
| --- | ---: |
| case-028/frame-1 | 0.0043538410885977895 |
| case-028/frame-2 | 0.0057292132493690145 |
| case-037/frame-1 | 0.011729213249363043 |
| case-037/frame-2 | 0.011729213249362309 |
| case-063/frame-1 | 0.005729213249367756 |
| case-063/frame-2 | 0.005729213249367601 |
| case-072/frame-1 | 0.01172921324936327 |
| case-072/frame-2 | 0.011729213249362509 |

A retained upper bound is unresolved enclosure volume; it is not a measured
collision volume. Newly excluded leaves cannot be counted as full-frame passes.

## Actual Line controls

`actual_line_controls_r8.json` retains an actual original edge189 Line claim
and four mutated claims. Dropping an axis from the shared-parameter trace,
changing the empty-axis identity, incorrectly substituting a zero-direction
reason, and omitting the original nonzero displacement all produce the expected
specific rejections. The original positive claim still verifies.

No original failure, source record, displacement component, parameter domain,
material identity, or qualification threshold was modified by this review.
