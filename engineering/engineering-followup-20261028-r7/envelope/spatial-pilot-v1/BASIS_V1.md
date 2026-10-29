# One original spatial split: fixed small-leaf cost diagnostic

## Scope and selection fixed before execution

The capacity question concerns the small retained-volume tail of the
original V6 case-028/frame-1 forest. Existing records contain 3153 retained
leaves with the same exact directed volume (display only:
`1.1087838536643396e-10 mm3`) and 3106 leaves with the most frequent complete
twelve-channel first-blocker signature. Their metadata-only intersection
contains exactly 3097 original locators. Its smallest locator is **[78,375]**.
The complete selected original leaf, every intersection member, exact volume,
source identity, and selection rule are frozen in `SOURCE_SELECTION_V2.json`.

The preceding [78,320] choice used only the blocker signature and selected
a much larger depth-8 leaf. It was superseded before any geometric execution
or source registration and remains in its own unexecuted selection receipt.
The revised selection uses existing metadata only, never a new probe result.

This diagnostic is limited to one parent, one invocation of the original
deterministic cut rule, and at most two child channel attempts. It performs
one freshly counted replay of the parent's actual original failed channels.
No other leaf is tried, no alternative cut is searched, and no result is
transferred to the other 3096 class members or any other source leaf.

## The original depth gate is explicitly exceeded

The selected parent has original V6 depth 24 and was retained for
`path_depth_limit_retained`. One diagnostic split creates children at
inherited depth 24 + local diagnostic depth 1 = **cumulative depth 25**.
Therefore this is **not a pass under the original cumulative V6 depth-24
gate**. The contract fixes `original_V6_depth_cap_exceeded=true`,
`original_V6_depth_gate_passed=false`, and `qualification_claimed=false`.

The historical V7/V9 capacity field is only named `maximum_depth: 24`; it
does not explicitly name an additional or local depth. The historical
source takes each retained V6 leaf as a new refinement root and initializes
its pending local depth to zero. Its basis describes a new forest from all
4943 retained V6 leaves, and its selected-leaf binding explicitly requires
the inherited selected leaf to have depth 24. Thus the implementation has
new-stage local-depth semantics, but it does not preserve a cumulative V6
depth-24 bound. That distinction is recorded in the separate source-based
depth clarification, which is a frozen input to this contract.

The original V6 global 4096-split stage was also exhausted. V9 already
performed 81 additional splits. This probe adds at most one, giving 82 in
the later-stage ledger and 4178 across the original V6 stage, V9 work, and
probe. It cannot claim that the original V6 global split limit stayed intact.

The probe can measure a cost hypothesis for a separately registered future
stage. It cannot qualify V6, V9, the failed first-u gate, a full frame, a
native material model, or full continuous G2. No full-frame run is launched.

## Original method correspondence

The preparation script copies twelve complete function bodies byte-for-byte
from the recovered frozen source files. Their AST identities are checked
both during preparation and before the diagnostic executes. The mapping
receipt lists the full original file identity and original/copied AST hash.

| Original source | Complete unchanged copied functions |
| --- | --- |
| `primitive_refinement_r5e_v6.py` | `need`, `separated`, `attempt_channel`, `choose_cut` |
| `exterior_channels_r5e_v3.py` | `require`, `decode`, `encode`, `volume`, `channel_for` |
| `primitive_support_model_r5e_v6.py` | `add`, `scale`, `project` |

The original producer and primitive helper modules are not imported. A small
namespace exposes the exact copied channel and projection functions to the
unchanged original method functions. No original primitive cover is rebuilt,
trimmed, sampled, reduced, or replaced. Both complete material sources are
read from the original qualified V6 certificate in their original order:
material 3 has 523 pieces and material 2 has 179 pieces. Every original box,
nonaxis slab, zero-width carrier, known whole bound, and full original D is
retained and bound by the complete boundary canonical hash.

The original primitive source lock, all 53 original V6 archived files, the
original producer/independent-reader reports, owned controllers, and pipeline
are bound. The original owned V6 stage must still be a completed 8/16
conditional-model result. That result is not upgraded to native membership.
The existing V9 mathematical-worker completion, owned VmRSS failure, u=0,
and unreached first-u gate are separately bound and remain unchanged.

## Complete one-split experiment

The full original root-to-[78,375] path reconstructs the parent box from the
original root and each recorded exact cut. The path depth, positive directed
volume, original leaf record, and fixed selection all must agree.

Freshly execute the original twelve-channel `attempt_channel` on that parent
and require the exact same complete failure observation as the saved V6
record. This is a real replay and is charged again. It is not free work
silently reused from the source report.

Use the original `choose_cut` exactly once. Its registered endpoint or
midpoint rule, priority, channel order, carrier order, and slab choices are
unchanged. Split into the complete low/high boxes. Both child volumes must
be strictly positive and sum exactly to the parent. The closed cut plane
and all closed boundaries remain retained zero-volume carriers.

For each child, first apply the unchanged exact tiny threshold
`Fraction(1e-7) / 100000`. A tiny child retains its full positive volume
without a channel attempt. Every non-tiny child receives one complete
original channel attempt. A successful original spatial proof excludes
only its open interior. A failed child remains pending with its entire
positive volume; its status is a finite diagnostic stop, not a claimed
V6 depth-gate pass or actual material interference. There is no second split.

The source volume ledger must satisfy

`original parent volume = excluded open volume + pending positive volume`.

No successful result for this one parent establishes a bound for any other
leaf or for the whole frame. A negative result is also preserved without
changing the selection, depth limit, cut rule, or allowed experiment size.

## Original independent proof replay

Only the frozen original `verify_primitive_support_r5e_v6.py` checker is
imported. Its unchanged `independent_cut`, `check_exclusion`, and
`check_unresolved` routines rederive the actual cut and verify each applicable
child record against a separately parsed complete source representation.
The checker never imports the probe producer or primitive helper.

Its `separator_holds` entry is wrapped solely to count each invocation and
call the original frozen function. No mathematical return value or source
function body is replaced. The original checker source hash must remain
unchanged before and after execution. This replay is part of a finite cost
diagnostic, not a new owned scientific qualification.

An actual mutation omitting one parent's recorded unresolved channel must
be rejected by the original checker. If an actual excluded child exists,
omitting one of its complete piece proof codes must also be rejected. If
there is no excluded child, that second control is explicitly N/A and not
counted as a rejection pass. These controls fail before separator evaluation
at the original identity/coverage guards and do not add extra geometry cases.

## Finite work and cumulative cost ledger

The original ordered channels comprise six channels per material. With 523
and 179 complete pieces, three full attempts require at most

`3 * 6 * (523+179) = 12636 complete-piece tests`.

Every spatial piece has at most six coordinate inequalities and two nonaxis
inequalities. The corresponding maximum is **101088 support tests**. The
parent's independent failed-channel checks use at most `12*8=96` original
separator calls. The two children use at most `2*523=1046` calls when both
require complete successful proofs. Thus at most **1142** independent
separator calls are possible. A failed child requires at most 96 instead.

The original V9 spent counters are retained as the starting ledger:
81 splits, 171429 piece tests, and 342440 support tests. Fresh parent replay,
both child attempts, and original independent replay are all charged on top.
No intermediate V9 UV work is removed from the historical cost.

The previous plane-preimage and wire-meaning diagnostics are separately
listed with all recorded counters, actual runtimes, and source-construction
parameters. Conservatively debit their 19928 counted geometric comparisons
to the later-stage support-like ledger, and 1432 piece/curve/wire operations
to a piece-like ledger. The latter includes all recorded UV-piece tests,
complete wire cover tests, Line tests, fixed Circle parameters, and complete
wire traversal pieces. The different units remain named rather than being
presented as original 3D separator tests.

Earlier domain/source validation attempts are also listed with their real
success/failure, runtime, and RSS. Those source diagnostics recorded no
channel searches and did not record a count of their algebraic validation
comparisons. They are not called free, nor relabeled reusable separator
proofs. Exact source validation, file hashing, rational arithmetic, and cut
selection are separately finite work; the original separator counters never
represented total machine instructions.

The bounded maxima including the listed tracked earlier work are therefore
82 later-stage splits, 186639 piece-like tests, and 464598 support-like tests.
Actual tracked totals must remain below the unchanged later-stage limits
4096 / 12000000 / 12000000. The original V6 historical counters remain a
separate visible stage; passing these later-stage accounting checks is not
passing the original cumulative V6 depth/split gates.

The diagnostic is registered for **60 seconds**, **536870912 bytes of address
space**, **67108864 decoded bytes per input**, and **4194304 output bytes**.
The observed earlier V9 producer required about 5.15 seconds and 132.5 MB;
the original owned V6 stage about 62.32 seconds and 183 MB. These observations
and the small fixed work bound support a bounded diagnostic attempt, not a
promise of convergence or a full-frame capacity qualification. All actual
failures and unresolved child volumes must be retained.
