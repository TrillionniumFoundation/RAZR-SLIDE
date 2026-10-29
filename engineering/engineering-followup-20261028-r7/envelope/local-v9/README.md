# Actual V9 local attempt: original ownership failure and saved u = 0

The exact registered V9 driver ran from the real `razr-current` worktree
at commit `65f2a8fbb30d6310c1a69ef37204fa7fa8f32b3a`. It ended with process
exit code 2 after 51.83012109400079 seconds of driver-reported elapsed
time. The sixteen original output files total 2,801,285 bytes. All 146
registered source and input files remained byte-identical after exit.

The producer completed in 5.149013676998948 seconds with 132534272 bytes
reported peak RSS. All eight source plane models applied, including the
two added original Line-plane models; none was rejected. Their complete
UV boundary cover contains 554 pieces. The selected original V6 leaf
was again partitioned into 163 nodes, 81 splits and 82 excluded leaves.
Its retained upper bound is exactly zero, but no new planar `u` proof
appears in a saved excluded-leaf proof. The producer performed 413
successful intermediate planar separations. These are different counts
and do not qualify the original saved-proof gate.

The independent mathematical worker also completed: 46.055000877000566
seconds, 182620160 bytes reported peak RSS. It checked 1296 saved failed
UV-channel records, retained saved `u = 0`, and rejected all 36 applicable
actual negative controls, including the twelve new source controls.
Actual UV-proof mutation targets were absent and remain not applicable.

The original `verify-single` **owned supervisor failed** during process
exit sampling with:

`RuntimeError: still-running owned child RSS unavailable: KeyError: 'VmRSS'`

The worker exit code was 0 and its entry receipt was complete. The
supervisor recorded no resource-stop threshold violation, but its
completion flag is false. This failure is retained without zero-RSS
substitution, retrospective pass, source edit or retry.

Consequently the driver stopped at the failed owned stage before reaching
the original first-leaf `u` gate. The predicate would be false from the
saved worker records because `u = 0`; that is a separate post-exit
observation, not a claim that the driver reached that gate. The all-sixteen
preflight, full refinement and full verification never started. This
attempt establishes no formal owned verification pass, new whole-domain
qualification, native semantics, G2, or physical acceptance.

The authoritative post-exit description is
`R7E_V9_LOCAL_LAUNCH_RECEIPT_V2.json`, with
`R7E_V9_LOCAL_ACTUAL_OUTPUT_MANIFEST_V2.json`. The earlier post-readback
script wrote a receipt containing the actual false supervisor status,
then failed its own mistaken assertion that both supervisors completed.
Its script, V1 receipt, V1 manifest and explicit assumption-failure record
are all preserved. V2 separates worker completion, owned-monitor failure,
the unreached gate, and the false saved-proof predicate.

`MANIFEST.json` enumerates every regular member of this closed directory,
except itself. Later correlation diagnostics and any new supervisor or
entry revisions belong to separately named directories and attempts.
