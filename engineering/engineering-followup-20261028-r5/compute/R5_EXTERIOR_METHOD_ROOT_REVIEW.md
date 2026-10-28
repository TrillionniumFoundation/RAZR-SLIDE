# R5 exterior-channel source review

This is a source and mathematical review before execution, not a claim that the
new worker has run or that a physical/native clearance gate has passed.

## Mathematical implication

For a compact closed material S and a connected open rectangular channel Q,
if Q avoids every registered closed box covering the complete boundary of S,
then S intersect Q is both open and closed relative to Q. A point beyond the
complete material support box is outside S, so S intersect Q is empty. The
method may remove the open interior of a candidate cell from a volume upper
bound. It must retain its closed boundary as a zero-volume carrier.

For compact S and D, any boundary point of S+D has a representation s+d. If s
were an interior point of S, that point would be interior to S+d and hence
S+D. Thus boundary(S+D) is contained in boundary(S)+D. Expanding each original
boundary box by the entire original D is sufficient under the original exact
boundary-cover premise. No displacement may be rounded to zero for that step.

The source uses interval separation between a closed boundary box and an open
channel: b <= l or a >= u in at least one axis. This correctly retains
zero-width faces, edges and vertices as potential blockers. A positive-volume
intersection test would be unsound here; the source does not use one.

## Review finding and correction

The first independent checker verified the cells in the supplied report but
did not require its complete phase/frame roster. A report missing a frame could
therefore be declared complete by that checker. The issue was reported to the
author before any mathematical worker executed. Named V3 now binds the exact
expected phase and frame sequence, requires all 16 original frames for all_raw,
and includes missing-frame, duplicate-frame and wrong-phase negative controls.
The old versions and their actual resource-admission failure remain retained.

The portable source lock binds the producer, separate checker, driver, method,
input bridge and three unchanged R4 process-control sources. The bridge maps
19 raw/public inputs; decoded JSON equality was actually checked by the author.
The 16 gzip encodings differ, so their physical SHA values must be looked up
explicitly rather than silently accepted under the old raw SHA values.

## Execution requirements retained

The sequence is one stationary cell, independent certificate check, measured
all-frame preflight, all 16 original raw frames, and independent full check.
Each supervised worker retains 600 seconds, 805306368 B RSS, 7301444403 B shared
ceiling, 104857600 B disk floor, 41943040 B output cap, and 4194304 B metadata
margin. Each earlier stage must actually complete before the next one starts.
A blocked resource admission must remain an actual nonexecution.

## Explicit unresolved premises

This review accepts only the conditional exact-real implication from the
complete registered boundary covers. It does not establish native OCCT material
semantics, uniform compiled curve/transform error, current-factory continuous
G2, physical tolerances, strength, electrical qualification, or G3/G4/G5.
Raw-frame refinement also does not change the separate R4 L2 diagnostic result.
