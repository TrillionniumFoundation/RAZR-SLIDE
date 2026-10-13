# RAZR SLIDE — r3 双独立 STOP 与实体闭槽回位研究台架

`manufacturing_go=false`，`fixture_fabrication_go=false`。本目录是新的研究台架派生设计与实际 CadQuery/OCC/STEP 证据，不是整机生产图，也未集成到 OEM 主机 CAD。两舱同尺寸、单块约 7 英寸柔性 OLED、B 舱上滑 79.75 mm 后法向就位 8.2 mm、A 舱优先大电池的产品约束没有被改动。

## 实体增量

每个端位的左右两侧各有独立承力 ROOT、两件独立 STOP 与两条真实闭槽。钥匙上的闭槽以圆柱销驱动 STOP；在完整、未卡滞且按所测路径运动的假设下，撤钥会迫使销回到低位。ROOT 内的实体下支承接住低位 STOP，退爪时其 gate 与 PAWL tab 发生真正材料交叠。左右根部和各 STOP 都有独立实体，没有用共用执行器或软件许可位代替材料锁止。

这是 1:1 尺寸的研究台架。固定帽和原盖仍标记 `UNFASTENED`，没有受控螺钉、预紧、材料、制造公差、供应商曲线或手机实际安装证明。接触面积与交叠体积都不能证明强度。新尺寸全部是 research hypotheses。

为研究原先极窄的就位窗口，原捕获 pawn 和导向件沿 q 正方向派生移动 0.15 mm；原钥匙接触形状与历史文件保留。结果把名义捕获空程增至约 0.18 mm，相对 q 误差最差 -0.05 mm 的实际碰撞探针约 0.23 mm。BM28、OLED 和跨舱 FPC 可允许的真实捕获空程未知，因此这个修改不是整机合格结论。旧 0.05 mm 捕获探针在新设计上不通过，新 0.25 mm 探针仅是研究判据。

R2 的 0.005 mm 名义全就位窗口仍没有制造公差资格；R3 的派生捕获接触扫描没有关闭新闭槽总成的制造公差门槛。

## 执行与保留的失败

`rejected-lowlink-layout/` 保存已经正常结束的原统一执行：644 个退爪样本、204 个撤钥样本、14 个 STEP 及回执。正常撤钥扫到 12 mm，两种单 STOP held-clear 撤钥故障都保留真实 KEY/STOP 碰撞路径，双 STOP 同时卡在放行位置的 absence 逃逸也保留。

独立槽间隙试验从该轮精确源码快照实际构造出 q=0.15 mm、两个 STOP 均 lift=1.20 mm 的退爪路径。OPEN 全路径无交叠；STOW 却在新低连接片上与 KEY 交叠 0.000360 mm³。这是新增结构的正常路径缺陷，不能被计作安全捕获。最终仅把 STOW 低连接片前沿从 Q-0.05 改到 Q+0.10，使其与已移动的原 stem 同步。`verify_lowlink_repair.py` 对全部受影响 STOW PAWL pairs 重算，并再次构造该 q=0.15 mm 的完整两侧路径，最终 STEP 从修复后的实体重新导出。

未变 pairs 的复用有受控依据：精确源码只允许上述一行变化；未改变静态参与实体先比较原生 BREP，序列化不同则双向真实 OCC material cut 都必须完全空，包括零残留拓扑。随后才复用原 native 回执。第一次要求所有 BREP 字节相同的验证器确实拒绝了独立重建的 STOW R KEY，其 native 1 和源码保留在 `rejected-brep-serialization-check/`。未用几何相等的假设绕过该拒绝。

更早两类实体失败也保留：`rejected-initial-layout/` 的盖体连接及初始碰撞，以及 `rejected-full-withdraw-layout/` 的 OPEN 完整撤钥受导向底板、盖体和横梁阻挡。最终设计有实际通道和相连盖体上拱来处理这些具体干涉。

## 槽自由位置、捕获与公差的界限

cam 的 0.10 mm 平段是设计中心线，**不是实际释放许可窗口**。销半径 0.10 mm，槽半径 0.16 mm，真实径向自由度 0.06 mm。斜率 2 的槽段使相应竖向自由范围可达约 0.134 mm，不能只扫描名义 `lift(q)` 就宣称欠插安全。`independent/slot-clearance-*` 保存实际圆距、实体布置、全 pair 矩阵、真实 STEP 与源码 SHA。

在 q=0.20 mm、两 STOP 实际 lift=1.11 mm 时，pin/key 和 stop/pawl 都可清空，但原捕获 KEY/PAWL 已相交，STOW 最大 0.003800 mm³、OPEN 0.001920 mm³（STOW 值还含被修复前低连接片的附加交叠）。因此这个反例证明了 gate-only 假设的不足，**不构成整条可行的逃逸**。也不能把意外材料相撞归为已验证的安全捕获。

独立原捕获接触扫描有 12,956 逻辑位置与 5,204 实际接触 profile；在所试 ±0.05 mm 刚体偏移下，原非负 q 公共带为空。派生接触扫描的 1,188 个状态使所试 q=0…0.10 mm、XYZ 各 ±0.05 mm 的原接触组合在新 0.25 mm 反向探针下成立；这只覆盖隔离的捕获接触，**不覆盖新闭槽、导向、盖体、螺钉或内部特征的 GD&T**。负 q 从未用于扩大合格就位带。整体制造公差、实际装配和可接受空程仍是硬阻塞。

## 保持未通过的实物门槛

低位 absence STOP 是扫描边界条件，没有实体弹簧或失电回位力证据。闭槽证明了所测完整几何的正向运动约束，未证明摩擦、卡滞、断销、断簧、冲击、磨损或失效常闭。单 STOP held-clear 的钥匙路径可被材料阻止，两个 held-clear 又能让无钥匙状态放行，真实双故障反例保留。共用钥匙/cam 的单一损坏原因没有被排除。

两件独立 STOP 不等于两个独立故障域。同一 KEY 双 cam 破裂、共同支承或未紧固盖失效，可能同时留下 clear 位置；不能把所有逃逸都归为两个独立故障。单 STOP absent 扫描中另一 STOP 位于 0 仍是边界条件，未证明弹簧或破裂后的物理归位。

有限力回缩安全阈值、限力器参数、材料强度、弹簧 force curve 和 fastener clamp qualification 均为 `null` 或 `false`。不凭空选择安全 N 值。真实捕获、限力回缩、双电池、USB、OLED 资格以及受控 OLED/FPC、真实装配与完整 PCB 均不能由本目录几何证据代替；整机保持 `manufacturing_go=false`。

历史 r2、R25/R26、冻结基线及几何 guard 的全部字节在 native 执行前后绑定 SHA 并检查不变。最终回执 `r3-receipt.json`、`lowlink-repair-result.json` 和独立 STEP 检查结果应配套读取；`final_manifest.json` 冻结本目录可交付文件并排除 `__pycache__`。

## 最终实际 STEP 与跨机结果

独立 checker 不导入 builder。它递归遍历 14 个 STEP 的完整导入 payload，拒绝任何非 Solid 叶、空 Compound、free face/wire/edge/vertex、非法节点或非有限/非正签名体积，确认共 212 个有效正体积实体后才识别部件。完成 868 个退爪样本、92 个实体单侧缺钥重构样本及 164 个正常撤钥样本；边界条件与 retained double-jam safety failure 随报告保留。

Cloud 与真实 X230 均原生退出 0，耗时分别约 106.437 s 与 225.433 s，错误输出都为空。X230 使用同 3 份 checker 源码和 14 个 STEP 的受控包，18 个传输输入（另含 native runner）的执行前后 SHA 全部不变，所有取回 chunk 与完整文件 SHA 均匹配。逐项比较 19,603 个数值和 19,949 个身份/布尔/null 值，最大数值差为 0，仅跳过主机名与 Python 版本；CQ 都为 2.7.0。`x230-independent/Cloud-vs-X230-comparison.json` 给出精确比较回执。两个计算环境一致不能替代实物资格。
