# SLIDE v2: actual second attempt, interrupted

This is the actual frozen v2 execution at functional commit
`042b768903cccbd7a0995317c8598401e0318e2a`, distinct from later r3 preparation.
The worker completed five factory construction probes, then was terminated and
reaped after 388.385801 seconds when the unchanged shared-memory guard exceeded
6.8 GiB. All 11,781 persisted pair rows remain `not_evaluated`.
The number of any completed in-memory pairs before the 128-result flush is unknown.

The external worker RSS samples were empty. Only the construction phase has a
worker self-reported high-water mark; a whole-run worker peak was not measured.
The shared-memory guard was actually observed and enforced.

`results.tar.gz` contains the exact raw controller, full saved report, native log,
all eleven executed scratch source copies, their manifest, and independent
post-stop source/lock and raw-reader reviews. The raw reader rejected completion.
`readonly-cost-review.json` is a separate source-only cost analysis and does not
identify the active pair or prove the cause of its cost. No CAD was run by that review.

These incomplete records cannot resume native geometry and do not establish any
continuous-motion, physical, fixture, or manufacturing qualification.
The original startup refusal and v2 preparation remain in `../slide-prepared-v2/`.
