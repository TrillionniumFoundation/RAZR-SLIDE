# L5b stage 1: restore the complete original target binding

This narrow change replaces only the seven `original_cases[i].target` values in the published L5 binding. Each replacement is the complete 20-field `target` read from its original L1 result. The original five scientific fields, whole-material input identities, source identities, q intervals, all specifications, and every other binding field are unchanged.

The immutable L5 producer requires exact dictionary equality with the original target. L5a run 40289428756 failed before its `native_started` flag: its binding had a five-field projection while the original result has twenty fields. The producer retained `ValueError` without its message. The precise failing gate is established here by compiling and running the unchanged producer's `require` and exact equality-call AST against the byte-verified originals; it is not represented as recovered hosted exception text.

The pure replay verifies the full 7,379,877-byte original E17 ZIP SHA and CRC, all 39 pinned scientific members, and all 11 pinned S4 source files. All seven incomplete targets fail the original gate; all seven complete targets pass it. The unchanged L5 pure plan is equal field for field for old and complete targets. All 21 negative controls (material, q interval, historical node identity) fail the original gate. No CAD module is imported and no native geometry is run.

The restored binding is exactly 39,348 bytes, SHA-256 `7de2b7f78e18de99a0c084e80e9fbd2a62582d1b6624b4f2ea031f37ccfda2f2`. This matches the identity reported before the old runtime disappeared. The old RAM script, report and unpublished request were not recovered; this reconstruction uses new exact readbacks of the fixed public Git sources and original artifact. The present script, replay report and request are newly generated and have their own identities.

The additional target fields contain original historical failure and fallback-clear records. They remain original history and are not L5 clear results. The earlier L5 workflow-size failure and L5a pre-native failure remain separate. All seven L5 native cases and the current-K1 stage remain unevaluated.

Stage 1 does not change a workflow, producer, algorithm, reader, threshold, process harness or resource guard. It does not request a native run. A later separately reviewed workflow can pin its source downloads to the immutable published stage-1 commit and update only the binding size/SHA.

Scope remains the seven original nominal q=[0,12] cases and their original specification. This does not cover the full factory binary64 acceptance slabs, the independent left/right domain, all 11,781 pairs, K3, OEM qualification or physical acceptance.
