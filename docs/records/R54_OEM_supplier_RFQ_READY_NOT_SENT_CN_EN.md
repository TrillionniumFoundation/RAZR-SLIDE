# R54 资料请求 — READY / NOT SENT（未发送）

本文是向 OEM/供应商索取*受控数据*的技术清单，不是已经取得权限、订单或报告。当前没有明确的、已核实的收件人或正式采购授权。

## OEM / Motorola — 需交付

请提供与同一设计版本一致的 A/B 双舱成品外壳、主板/连接器焊盘、电芯/BMS、摄像头/天线/导轨以及 7 英寸 OLED/COF/封边完整 3D STEP/Parasolid 与原生装配坐标。B 舱从后/下层 Y 向滑出 79.75mm，最后 Z 向坐实 8.2mm。两舱成品外形同尺寸，但内部不对称，A 优先电池，4700mAh 为未验证目标。

请至少交付 4 个非退化空间基准点，给出实测位置、坐标系定义、CAD 版本、4×4 刚体矩阵、单位、原始 SHA256 及独立计量校验记录；受保护及可改设计区域需带签署的版本/零件权限。当前研究碰撞盒不是授权加工区域。

**EN:** Please deliver revision-matched native 3D A/B exterior, PCBA/connector land patterns, batteries/BMS, camera/antenna, rails and complete ~7-inch OLED/COF/seal keep-outs; Y travel 79.75 mm and final Z dock 8.2 mm. Provide >=4 spatially distributed, independently measured fiducial pairs, frame definition, 4×4 proper rigid transform, file SHA256, GD&T and signed permission for each proposed service corridor. The research collision boxes are not cut authorization.

## Hirose — 需交付

准确料号 `BM28B0.6-24DP/2-0.35V(53)` 和 `BM28B0.6-24DS/2-0.35V(53)`，同版本原厂 STEP、2D 工程图、焊盘/应力释放规范、触点分组和每组电流降额、屏蔽接地/差分布线、容差；官网公开 STEP 下载入口，但当前从连接主机下载 HTTP 403，**未获得原始 STEP**。该连接器是舱内静态端接用途，不允许把标称 10 次插拔寿命解释为整机 30 万次滑动寿命。

**EN:** Supply controlled native header + receptacle STEP with current 2D drawings and land patterns, part/revision traceability, contact-specific current derating, shield/return, SI and assembly keep-outs. A connector's advertised data rate is not an end-to-end USB qualification.

## Dynamic FPC supplier — 需交付

请提供完整铜/覆盖膜/屏蔽/粘合剂的真实宽厚、层叠与中性轴、最小动态半径、79.75mm 滑出+8.2mm 法向坐实的扭转和端部应力释放设计，含中途反复反向试验。必须实测 30 万次或约定寿命，连续带载 USB 导通，电源回流、绝缘、电弧和 SI；报告明确样本量、环境、失效判据、失效统计和原始波形。

**EN:** Provide the actual conductor/coverlay/shield stackup, neutral axis, dynamic minimum radius and torsional strain limits, captive guides, both end clamps, 300k motion cycles including midstroke reversals, powered copper USB continuity at ALL positions, differential SI/eye/BER/TDR/VNA and failure statistics. No dock-only substitute.

## Power / OLED / mechanics — 需交付

独立的双电池隔离与 BMS 时序、单点短路反例实物验证；双侧机械坐实/失效常闭/带载限力回缩；OLED 完整带边框的模组 CAD、动态 R、长期收纳残余形变、展平力、温湿循环与寿命。IEC 62715-6-42:2026 只是展平力的测量方法。

**EN:** Separate signed bench reports for mechanical dual-end fail-closed capture; battery isolation/reverse blocking/precharge/hot disconnect/PCB bypass; and exact OLED module bend-radius, residual set, flattening force and service life. Measurement-method compliance is not lifetime qualification.

## 文件回复格式 / deliverables

每个文件需要：OEM/供应商身份、受控文档号及修订、零件料号、单位、坐标基准、SHA256、原始二进制、签署授权和测试原始数据。R54 数值预检通过**不能**代替供应商真实性或制造批准。
