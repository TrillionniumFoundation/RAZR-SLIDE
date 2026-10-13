# RAZR SLIDE R58｜OEM / FPC / Hirose / OLED 原厂受控资料询证（READY / NOT SENT）

**文件状态：可发送草稿，未发送、未获得样品或授权。** 本报告中的坐标来自非 OEM 研究 BRep，不能解释为已取得 Motorola / 面板厂的切削许可。

## 中文技术询证

目标产品保持 A/B 两个外形相同的完整功能舱、单块约 7 英寸 OLED、B 舱向上滑 79.75mm、终点前后坐实 8.2mm、A 舱优先电池，无独立外屏。要求滑行、换向、伸出、回缩、末端坐实的**全程真实 A/B USB 铜导体在线**，不能仅在端点连通、使用无线传输或靠缓存代替。

请以**同一受控版本**、原厂坐标系/单位/公差、签字的可改区域提供下列 **12 类**原始二进制 CAD/测试文件（每类请附发行方、料号/修订、受控文号、签署的使用与修改许可、SHA256）：

1. `OEM_A_fully_finished_shell_native_CAD`：A 成品外壳及内部壁厚、装配边界。
2. `OEM_B_fully_finished_shell_native_CAD`：B 成品外壳及上下两个终点的装配边界。
3. `OEM_PCB_battery_BMS_keepouts_native_CAD`：PCB、两电芯、BMS、摄像头、导轨及不可侵入体积、4700mAh 可实现性。
4. `OLED_full_module_native_CAD`：约 7 英寸单屏完整模块（封边、COF、FPC、驱动 IC、触摸、保护层）3D 外包络。
5. `OLED_fatigue_residual_shape_and_flattening_data`：动态 R、长期收纳残余形变和恢复、展平力/张力、温度/循环、失效判据与寿命试验原始数据。IEC 62715-6-42:2026 仅可作为展平力测量方法。
6. `HIROSE_BM28_header_native_STEP`：header `BM28B0.6-24DP/2-0.35V(53)` 同修订版 STEP/图纸/焊盘/禁布区。
7. `HIROSE_BM28_mate_native_STEP`：mate `BM28B0.6-24DS/2-0.35V(53)` 同修订版 STEP/焊盘/受载保持、10 次配合目录寿命与整机动作隔离设计。
8. `FPC_actual_stackup_neutral_axis_dynamic_radius`：PI/铜/胶/覆盖膜/屏蔽/回流及外形宽厚、中性轴、动态 R、双轴扭转和拉伸允许值、弯折/导向机构安装建议。
9. `FPC_300k_cycles_live_copper_test`：前进/后退/换向/坐实全程 30 万次或协定寿命，带实际铜线路连续性/开短路、温湿度、载荷、样本量及失效统计。
10. `MECHANICAL_two_end_fail_closed_test`：双端实体坐实、失效常闭、受载限力回缩、断簧断销/异物/磨损、针对既有 36/64 联合误解锁反例的实体故障证明。
11. `POWER_two_battery_isolation_fault_test`：独立额定跨舱电源方案、熔焊/逆灌/预充、三类 PCB 单点旁路、真实断接电压及电弧/热升波形。
12. `USB_full_stroke_SI_EMI_continuity_test`：目标 USB 速率、线路拓扑、差分阻抗、TDR/VNA、眼图/BER、屏蔽 EMI/ESD 与全过程供电及通讯实测。

还请附**至少四个非共面且可独立复核的 A/B 共同三维基准点**，标记允许切除的材料与禁止进入的区域；没有该授权，不会依据研究碰撞坐标建议削切机芯或 OLED。

### 本次新增的研究干涉见证（仅供厂家对位）

下列点都来自 R38 冻结研究坐标系，并非 OEM 真实机身碰撞结论；目标是请厂家在原厂 CAD 中**独立验证**：

- 收纳 s=0/q=0：候选 X15/α1 的 B 过渡段与 A 壳相交位置之一约 `(30.0, 69.737, 5.631)mm`；与 B 壳相交位置之一约 `(30.0,35.331,-1.048)mm`。
- 中程 s=39.875/q=0：B 过渡段与 A、B 均有研究实体相交。
- 完全展开 s=79.75/q=8.2：B 壳与 A 过渡段、U 回弯段及 B 过渡段均相交；本候选 B 总交叠约 14.1977mm³。
- 现有七条旧路线已在冻结研究壳中失败。本轮在同类 R15 平面 U 回环家族再进行 660 组中心线参数筛查，找不到三姿态零占体且零包络超出的候选；这不限制贵方提出**新的三维走线/独立平储线盒拓扑**。

**目前状态：上述资料真实验收 0/12；本行动单未实际发送。** 资料通过 SHA256 只能证实字节未改，不能自动认证签署者身份或寿命资格。

---

## English request for controlled supplier deliverables

Please provide **one coherent released revision** of native OEM A/B enclosure and PCB/battery/BMS/camera/rail keep-out CAD, the complete 7-inch OLED envelope including COF/FPC/seals, and both Hirose BM28 connector 3D/land patterns. We require at least **four non-coplanar measurable registration fiducials**, signed change/keep-out permissions, authoritative document numbers, original files and SHA256 hashes.

The end-to-end USB copper path must remain physically present and electrically operational during the entire **79.75 mm vertical slide plus 8.20 mm normal docking motion**, in both directions and under reversals. Endpoint-only mating, wireless bridging and buffered transfers are not substitutes. Request the real FPC layer stack, copper/polyimide/adhesive/coverlay/shield, neutral plane, minimum dynamic bend radius, torsion/tension limits, strain-relief drawings and representative endurance data (target 300,000 cycles, subject to written agreement), as well as TDR/VNA, eye/BER, EMI/ESD and continuity traces.

Separately provide dual-battery power-isolation fault test records, the two-end fail-closed mechanical lock/forced-retraction results, and OLED dynamic curvature / flattening force / long-storage residual deformation and life evidence. This RFQ contains **research-only collision witnesses**; no cut-out authorization has been obtained, and no physical certification is asserted. **READY—NOT SENT.**
