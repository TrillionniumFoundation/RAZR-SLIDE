# R52｜原厂坐标对齐和跨舱动态 FPC 请求 / Native OEM & FPC Datum and Cut-Region Request

**READY — NOT SENT / 已准备，尚未发送。不是采购或加工授权。**

## Frozen phone concept / 产品约束
Two same-finished-envelope functional compartments A/B, moving B travels +79.75 mm longitudinal Y from rear/lower stow, then +8.2 mm Z docking; single ~7-in flexible OLED; no rear independent display; A prioritizes battery. 4700mAh remains an unverified target. USB must have a **live, physical copper path throughout complete slide, mid-motion reversal and docking**, not dock-only contacts, wireless or buffered output.

## Essential OEM reply / OEM 原厂必须确认

Please supply manufacturer-controlled native A/B assembly CAD **in the identical assembly revision** for shell/chassis, mainboard+components, both cell/BMS packages, cameras, locks, retainers, antenna keepouts, the full OLED module and FPC bend path. Distinguish, as separately colored solids, (1) not modifiable protected regions, (2) conditional re-layout regions requiring explicit written engineering authority, and (3) externally allowed service channels. Include native datum scheme, units, GD&T, A-world↔B-local transformation for every motion state, mounting references and written scope-limited cut permission. **We will not modify proprietary mainboard/cell/camera models without explicit permission.**

研究坐标 `B_world=B_local+(0,s,q−8.2)`, `0≤s≤79.75`, `0≤q≤8.2`，属于旧研究 BRep，不是厂家的正确坐标。请先提供 OEM 基准系注册矩阵并由授权设计负责人确认。以下区域是 **7条已否决路径的碰撞包围盒查询**（mm），不是待挖孔：

| Priority | Research frame | Sample collision XYZ envelope, mm | Evidence |
|---|---|---|---|
| P0 | B local, A transition leg | (3.39172,14.50,3.89113) to (24.10755,82.71630,7.20) | 63/63 research route/pose conflicts |
| P0 | B local, rolling U bend | (3.39174,42.35471,3.88955) to (36.99500,93.34503,7.20) | 63/63 research conflicts |
| P1 | B local, B transition leg | (33.39178,18.06877,3.88960) to (35.60787,82.69680,7.20) | 45/63 conflicts |
| P1 | A fixed research | (3.39172,70.06499,0) to (24.10756,79.75,5.60) | 49/63 conflicts |

Request OEM engineers to identify which regions, if any, could become real **continuous physically guarded** FPC routes without compromising the structural capture, OLED or battery goals. Please reply with signed native solids and the allowed volume, NOT by marking these entire boxes as machinable.

## FPC & connector partner / 动态排线、连接器厂商

Please provide exact conductor count, native PCB/FPC materials and RA/ED Cu, copper widths and thickness, dielectric+coverlay and shielding, manufactured cross-section, bend-neutral plane, minimum radius **for both Y bend and Z docking/torsion**, thermal/creep/peel limits, connector header+mate accurate native STEP and landpattern, strain-relief design and full loop mounting. Specify required physical power lane separately from USB/low-voltage signals and include isolation/fault instrumentation.

Acceptance testing: 300,000 complete +79.75mm / +8.2mm cycles with commanded mid-motion reversal under specified temperature/humidity/storage, real-time conductor continuity and intermittent-contact event capture, contact resistance, physical image of deformed cables, USB negotiated link speed plus TDR/S-parameters/eye/BER/crosstalk/EMI/ESD, and A/B BMS reverse feed/overcurrent/PCB bypass tests. **No vendor data may be assumed by entering a hypothetical R15mm or a 24-pin header into CAD.**

## OLED module manufacturer / 显示厂商

Please provide full model/lot/revision-controlled ~7-in OLED envelope including COF, FPC, driver, adhesive/edge seal, layer neutral plane, approved dynamic bend radius, long-term flat-storage residual set/recovery, flattening force vs temperature/age, applied tension and panel fatigue life threshold. IEC 62715-6-42:2026 supplies a measurement method for flattening force, not a life qualification.

## Evidence submission / 原始证据交付

Use the `R51_VENDOR_NATIVE_INTAKE_TEMPLATE.json` for basic inventory, plus R52 native frame registration array `native_to_research_rigid_transform_mm` (4×4 rigid homogeneous transform) for OEM A, B and OLED CAD. Provide traceable manufacturer identities, document numbers, lot/revision IDs and file SHA256. R52 software rejects placeholders and inconsistent hashes; **it cannot authenticate supplier signatures or grant permission**. Physical design authority must separately confirm supplier origin, coordinate registration, allowed keepouts and relevant M/P/S/U/D independent gate approvals.

Contact details and NDA/procurement recipient have not been supplied; no RFQ or email has been sent, and no purchase has been placed.
