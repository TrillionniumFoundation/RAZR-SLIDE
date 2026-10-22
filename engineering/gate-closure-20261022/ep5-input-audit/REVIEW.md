# EP5 exact native input closure — independent review

Authority: physically copied R4 source tree and matching current integration stage. This review only read source/records and a tar directory; it did not rerun CAD, FE, QP or network retrieval.

## Required payload counts

| Entry | Repository non-code inputs | External inputs |
|---|---:|---|
| Local native | 3 | None |
| Full, original mounted tar | 13 | None |
| Full, explicit verified members | 12 | All 64 original mounted STEP members plus sibling recovery receipt |

All modes read design/product_routing_ep5.json, design/product_routing_ep4.json and design/product_geometry.json. The full-mode engineering payloads are:

| Payload | Required role |
|---|---|
| `engineering/panel-bearing-web-20261015/native-templates.tar.gz` | 34 STEP template bodies plus manifest.json INSIDE this container; outer archive pinned by product_geometry.native_baseline.sha256 |
| `engineering/pawl-actuation-20261015/geometry-manifest.json` | Pawl native archive identity and member byte/hash inventory |
| `engineering/pawl-actuation-20261015/native-geometry.tar.gz` | Pawl STEP members; each named member read and checked |
| `engineering/pawl-actuation-20261015/NATIVE_MANIFEST.json` | Pawl native expected roles, per-STEP metrics and hash |
| `engineering/cam-coupling-20261015/geometry-v5-manifest.json` | Cam-v5 19-member archive identity; used by parent scene and complete KEY reconstruction |
| `engineering/cam-coupling-20261015/native-v5-geometry.tar.gz` | Actual cam-v5 19 STEP members; used twice by parent and KEY factory |
| `engineering/cam-coupling-20261015/V5_NATIVE_MANIFEST.json` | Cam-v5 per-part metrics/hash manifest and cam_coupling source pin |
| `engineering/mounted-mechanism-20261015/geometry-manifest.json` | Mounted archive metadata and original STEP member inventory; exact pinned manifest for alternative |
| `engineering/thin-mechanism-20261015/native-verification.json.gz` | Actual left/right contact profile numbers (seven fields per contact), NOT unused historical evidence |
| `engineering/mounted-mechanism-20261015/native-geometry.tar.gz` | Default original mounted STEP archive; required if no explicit verified-member argument |

The alternative removes only the mounted native-geometry.tar.gz role. It must be explicitly selected; missing tar must not silently select a fallback. The mounted geometry manifest remains mandatory. Verify exactly 64 regular original STEP names/bytes/hashes and all recovery receipt rows, before and after execution; preserve original_archive_sha256_claimed_recovered=false.

## Source closure and actual reads

The JSON lists 26 full-mode project modules (25 for the default tar path), 7 local-mode modules, and two extra engineering Python sources. Captured follower construction dynamically loads captured_follower_assembly.py, checks cam_coupling.py against SOURCE_SHA, and calls pure source_geometry()/body() construction; no captured-follower report or archive is consumed. KEY construction reads the historical key_endcap_local_study.py only to bind its reference hash, reconstructs the geometry itself, and imports the exact cam-v5 STEP source.

The panel-bearing archive contains 34 STEP bodies plus its own manifest.json. Its outside geometry-manifest/NATIVE_MANIFEST are not read by this entry point. Product FPC imports product_interfaces code, but EP5 calls place_endpoint only; the 20-body EP4 endpoint is procedural. No endpoint PCB/mating-map or product_interfaces JSON is consumed. EP4 native_regressions, endpoint_joint.frozen, product_motion and the source OLED comparison are not called.

## R4 source-coverage gap

engineering/thin-mechanism-20261015/native-verification.json.gz is a real consumed input: verify_pawl_actuator.py:63–66 reads seven profile fields per contact to construct the cam profiles. R4 per-scene source_inputs records SHA256 88a8993fcbf5ee41246df2459725e2784ca84c2eacb720850faf0dd6f7e9c77d. The broad top-level snapshot omits .json.gz, so R4 does not establish before/after binding for this file. A new run must include it explicitly; its old report must retain this limitation.

## CI enforcement

- Require every role selected for the requested mode to exist and match its tracked HEAD blob, then compare its before/after SHA. Never create the mandatory set using an if-exists filter.
- Check each full pose’s scene.archive, source_inputs, KEY source records and external verified-source records against the bound role set. Unexpected actual dependencies must trigger an explicit closure update.
- R4 source_sha256 is an availability snapshot (1025 full, 960 local entries), not a dependency trace. Extra already-present historical tracked files can still be validated without requiring absent unrelated archives.
- Preserve source code, reader/helper, runtime lock and entrypoint-sync governance checks. The JSON records those separately from native payloads.
- The other five absent engineering archives are not EP5 payloads. Mounted tar is an EP5 default-path input with an explicit exact-member alternative. All six remain required failures of the existing complete tools/verify suites; do not change those gates.

Complete paths, hashes, source callsites, R4 comparison flags and exact external member inventory are in required-input-closure.json.
