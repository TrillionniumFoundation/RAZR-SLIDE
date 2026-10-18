# Current research: original loadcases and unloaded assembly reference

See engineering/loadcases-20261018/DELIVERY_VERIFICATION.json, nine-case-summary.json and METHOD_AND_LIMITS.md. Eight original normalized loadcases and an unloaded assembly reference now have independent whole-field evidence on the same fixed 86-face/258-coefficient L2 space with 512-sided prescribed load domains and 1e-7 mm gap target. This is not global trace/volume convergence or hardware capacity.

The initial spring parameter is distinguished from equilibrated assembly force; per-bolt transfer ratios are not equal-sharing assumptions or installed preload measurements. A residual-checked small-Schur solve handles dependent active equalities only in optional qr_pivot mode. All original support/equality/contact conditions remain. Fresh complete 1157 tests / 31 suites on 26539a7 and explicit e54d71c identities for the eight loading fields are preserved. The original unloaded-reference timeout is not a pass; its separately verified replacement is used.

Next define actual frame restraint, head/nut contact and installation/load path, and obtain real thread/preload/material data before applying normalized responses to a service-load budget. Current CAD, 3 mm screws and actual unknown inputs stay unchanged. candidate_go=false; fixture_fabrication_go=false; manufacturing_go=false.
