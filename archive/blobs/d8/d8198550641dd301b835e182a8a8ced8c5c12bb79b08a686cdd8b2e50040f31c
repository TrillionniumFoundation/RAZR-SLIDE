# R51｜原厂受控资料请求 / Vendor Native Data Request (READY, **NOT SENT**)

**项目定义不变 / Frozen design brief**：A/B 两舱成品目标同外形；B 由后下方向上移动 Y=79.75mm，终点法向坐实 Z=8.2mm；单块约 7 英寸柔性 OLED，无独立背部外屏；A 舱优先更大电池，4700mAh 是待验证目标。跨舱 USB 全程必须真实铜导体有线连续（包括中途反向移动和终点过渡），不得用 DOCK_ONLY 接触、无线或缓存替代。**这是一份资料请求，未对任何供应商发出，也不是采购承诺。**

**Research frame**: Current negative gate uses frozen R38 research coordinate frame in millimeters: world B = B_local + (0, s, q−8.2), 0≤s≤79.75, 0≤q≤8.2. Please provide an OEM-verified transform, coordinate references, datum scheme and signed, controlled revision. Research BRep / routing proxies are NOT permission to carve OEM PCB, cell, camera, chassis or OLED volumes.

## Requested native data / 必须交付的原生数据

| Owner / 责任方 | Minimum native deliverables / 最低交付内容 | Acceptance evidence / 可核查证据 |
|---|---|---|
| OEM structure / 整机结构 | Full A/B native CAD and STEP; actual PCBA, battery cells/BMS, camera, fasteners, mechanical locks, conductive contacts, thermal limits, service routes; colored non-cuttable vs specifically licensable cutout solids | Part numbers, revisions, CAD hashes, datum/GD&T, written limited modification permission and authentic vendor origin |
| Dynamic FPC designer / 动态排线 | Exact lamination thickness, conductor copper widths/layers, cross-sectional width, neutral axis, both-axis dynamic minimum radii, allowed torsion, bend/straighten forces, strain relief at both ends and candidate 3D serpentine route at 79.75+8.2mm motion | Native CAD/IPC drawing; actual material lot; 300,000 full motion cycles with failure threshold and monitored continuity, contact resistance and signal integrity; temperature/storage conditions |
| Connectors + USB / 连接器及高速链路 | Exact header+mate part IDs, source STEP and PCB footprint/GD&T, retention and service-mating limits; real shield/return and pin/pair mapping, agreed USB version/bit rate | Full-travel and mid-reversal link continuity, TDR/S-parameters, eye/BER, crosstalk, ESD/EMI, intermittency event logs |
| Dual battery + power / 双电池与电源 | A/B cell and BMS specs, peak/inrush loads, contact/fuse ratings, reverse-blocking FETs, precharge/isolator and PCB single-short failure analysis | Hardware witness of loss-of-power-before-release, energized disconnect and arc, thermal rise, reverse feed and minimum discharge time, three single-point PCB bypass failures |
| Mechanical safety / 机械 | Both ends independent structural capture and fail-closed interlock with spring, pins, real stops, fasteners, load path, limit-force retract; all materials & GDT | Force/displacement traces with exposed-contact motion + electrical states, both-side false-open, broken spring/pin, jammed carrier, contamination/impact/thermal cycling; close 36/64 legacy counterexamples |
| OLED OEM / 屏幕 | Specific ~7in module version including COF/FPC/driver/frame edge/seal stackup, full 3D envelope, approved dynamic R and neutral plane, allowable tension/pressure | Long storage residual set/recovery, flattening-force per IEC 62715-6-42:2026 where applicable, full travel repeated life and rejection criteria, actual OEM permitted service routes |

## R51 conflict evidence / 可提供给供应商的碰撞坐标文件

`results/R51_collision_coordinate_register.json` includes seven frozen research FPC alternatives, and each of nine pose conditions. For each five path segment it records a collision-positive coordinate bounding box in **fixed-A research frame** or **moving-B research local frame** (NOT global OEM frame). Also available: `results/R51_segment_conflict_summary.json` plus three *GHOST* positive OCC collision STEP solids. These do not specify authorized cutout geometry or a verified flexible route.

Key negative findings: B-side positive overlaps remain 63/63 pose/family pairs; A positive overlaps remain 49/63. A transition leg touches B 63/63, U-arc touches B 63/63, B transition leg touches B 45/63. This makes simple connector downsizing insufficient. R15, W1.2mm, t0.2mm are unapproved study assumptions; original seven specific route centerlines are **rejected**, no global impossibility proof.

## Suggested reply / 提交要求

Please provide independently attributable **controlled native files**, revision and lot IDs, actual material drawings, testing methods, calibration, traceable raw data and signed design authority. Do not submit marketing renders, catalog dimensions, third-party redrawn proxies, self-filled test claims, or unlicensed OEM internals as authentic source evidence. Put file hashes and references in `R51_VENDOR_NATIVE_INTAKE_TEMPLATE.json`; this form only checks inventory and hashes, never certifies provenance or manufacturing readiness. Direct vendor confirmation and sample witness testing remain mandatory.

**Current result: request READY, NOT SENT; production approval NOT GRANTED.**
