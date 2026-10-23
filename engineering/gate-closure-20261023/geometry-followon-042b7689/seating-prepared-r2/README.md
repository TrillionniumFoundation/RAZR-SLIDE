# Historical SEATING r2 preparation

This directory preserves the original 25-test r2 preparation and first preflight-only refusal. The unchanged original documentation is in [original-prepared-r2-README.md](original-prepared-r2-README.md); its original bytes also remain inside results.tar.gz.

After that package was frozen, a second native-requesting invocation was refused before worker startup for memory; see [the second refusal](../seating-attempt2/SUMMARY.json). Neither invocation started native geometry.

The old supervisor used namespace-local Popen.pid directly for procfs reads. That mapping could yield empty worker RSS observations in this environment. Future monitored native attempts should use the separately source-bound [reviewed r3 successor](../seating-prepared-r3/README.md). Its original geometry and resource thresholds are unchanged, but it has no native execution result yet.
