# 2026-10-26 全量推进：真实结果、原件与未决门槛

**两个原中途完整 factory 见证已闭合。K1 具名 KEY 修复连同 K2 四个端点，六个有限姿态共 143,570 次 fresh factory / STEP 体对评估全部 clear。新增实体行程止挡 K3 已完成两个先行姿态的材料、接触、越程与 changed-panel 全对读回；10 姿态完整矩阵另行实跑。原数值五探针仍有一项拒绝；连续包络的剩余交叠、真实器件、当前 FE 与实物 G3–G5 均保持未决。**

功能基准固定为 S4 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`，tree `cdd9e2c41216201b6cd04dd610d45fde80499045`。本次是 E3 `133bad5c5dddbf14fe466a23080b6e2e72ea3cb6` 的工程证据后继。具名候选与算法位于独立诊断路径，未替换生产默认 factory；唯一候选 ref 和 main 均保持原值。历史 S4 的 36 套 / 1,654 项测试不被改称本次新源码的完整测试。

[结果索引](SPRINT_RESULT_INDEX.json) · [源码与实际运行台账](SOURCE_AND_RUN_LEDGER.json) · [首个证据检查点验证](INTEGRATION_VERIFICATION.json) · [本次逐文件增量验证](CHECKPOINT2_INTEGRATION_VERIFICATION.json) · [PR #39](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/39)

## 1. 两个中途完整几何见证：验收闭合，原几何拒绝

F1a run `40273568199` 实际从 S4 构造两套完整的 154 体 factory，并在另一进程中独立读取全部 STEP。每个姿态分别执行 11,781 个 factory 体对和 11,781 个 reader 体对，共 **47,124 次 fresh 体对评估、94,248 条 start/result journal 记录**。journal 行数不是体对数。

| slide / q，mm | 完整实体对 | factory Common，mm³ | 独立 STEP Common，mm³ |
|---|---|---:|---:|
| 23.142044210239405 / 3.482188470506243 | A_BACK_PANEL / L_KEY | 0.24558784938224815 | 0.24558784938215988 |
| 同上 | A_BACK_PANEL / R_KEY | 0.24558784938224820 | 0.24558784938215994 |
| 60.880681403413135 / 9.160729490168748 | A_BACK_PANEL / L_KEY | 0.23013738353925134 | 0.23013738353916050 |
| 同上 | A_BACK_PANEL / R_KEY | 0.23013738353925126 | 0.23013738353916044 |

两姿态只有上述 panel/KEY 对被拒绝，其余完整体对没有正交集或求值失败。direct Common 与 STEP 的最大体积差为 `9.084399898995343e-14 mm³`。对 L1 的 16 份 whole-endpoint frame 材料，panel、KEY、Common 的双向差集均为零；原 whole-endpoint 材料与当前完整 factory 的身份对应已实际完成。

因此，第 1 项的**复现验收通过**与**原结构存在干涉**同时成立。它仍是 CAD 材料结果，并非实物碰撞测量。首轮 F1 `40273132915` 的 native/assertion 步骤成功后，Python 3.10 exporter 因 `hashlib.file_digest` 不可用失败，未取得可恢复的完整体对原件；该首轮失败单列，F1a 是修正导出器后的完整新执行。

[F1a 验收](geometry/F1a/F1A_WITNESS_ACCEPTANCE.json) · [首轮失败](geometry/F1_FIRST_RUN_FAILURE_RECEIPT.json)

## 2. 具名结构候选、实际材料账与允许域

实际交叠发生在 panel 的原支撑柱与 KEY 原横梁。支撑柱属于原 OLD_COVER 支承与旧载荷传递路径；本候选保留 panel，通过在 KEY 横梁切出中间缺口并增加向前的 U 形连接绕开支撑柱。

`key_forward_loop_v1` 的源码 SHA256 为 `3e6ebf17f1e50fd71eeaf294d059566d9361d3d830edc4365ea8763d00259578`。K1 run `40276423445` 在两个原见证姿态完整执行 factory 与独立 STEP reader，共 **47,124 次 fresh 体对评估**，正交集、求值失败和两进程结果不一致均为 **0**。每姿态的 154 个原件先与 F1a 核对完整材料；原 panel/KEY 正 Common 先重现，应用候选后两侧直接 Common 与全对记录均为零。独立 reader 按冻结盒合同重建切除与添加材料，不调用候选构造器。

| 每侧 KEY 的实际材料项 | 体积 / 尺寸 |
|---|---:|
| 原件切除量 | 约 0.594 mm³ |
| 实际新增材料量 | 约 2.623824 mm³ |
| 净体积增加量 | 约 2.029824 mm³ |
| 新增连接腿的声明局部截面 | 0.38 × 0.36 mm |
| 局部截面积 | 0.1368 mm²，为原横梁 0.54 mm² 的 25.3333% |

切除、添加、剩余件与功能保留区都有独立材料记录，受保护原区域的有向差集为零。上述局部截面**尚非完整 KEY 的最小壁厚测量，也没有材料、疲劳或强度资格**。同一 CAD 内核的独立进程与独立重建不被称为另一 CAD 内核。

[K1 实际验收](geometry/K1/K1_WITNESS_ACCEPTANCE.json) · [结构与域审查](geometry/STRUCTURE_AND_DOMAIN_REVIEW.md) · [具名源码](../engineering-next-20261026/key-forward-loop-k1/key_forward_loop_v1.py)

### K2 四个端点与 K3 具名实体止挡的新增实际结果

K2 run 40277813145 已完成 stow_tabs_0、stow_tabs_3、predock 与 open_installed 四个完整姿态；前三个各 154 体，OPEN 含全部七个已声明安装附件，共 161 体。factory 与独立 STEP 共 **96,446 次体对评估、192,892 条 journal 记录**，正交集、求值错误及体对结果不一致均为零。OPEN 的轴界分类使 native Common 调用数为 producer 813、reader 817，但全对的体积和拒绝结果一致；此差别原样保留。K1+K2 六个有限姿态合计 **143,570** 次体对评估，并不代表全部运动域已通过。

panel_key_travel_stops_v1 在 panel 上增加下限柱及上限趾，保留 K1 KEY 的原件。K3 run 40281153812 的 STOW-tabs3 与 PREDOCK 双 pilot 已完成：每姿态 producer 与 reader 各 153 个 changed-panel 体对均 clear，每姿态 reader 的 18 项原生材料/接触/越程门均真实求值并通过。双 pilot 合计 612 次 fresh 体对评估、1,224 条 journal 记录。实际 panel 只增加约 **4.62456 mm³**，切除为零；两侧 nominal contact face 各 **0.324 mm²**。whole KEY 越程 0.001 / 0.01 mm 分别产生约 0.000324 / 0.00324 mm³ Common，向内控制为零。原接触功能面、材料守恒及两端完整 panel 身份均经过双向材料核验；不是从 AABB 推断 clear。

这为 q=0/12 的具名 CAD 止挡提供了先行实体证据。它尚不证明全部独立控制状态、实体变形/限位受力、制造公差或真实样件行程。源 binary64 上限接触平面与精确 12 mm 的约 -8.881784197001252e-16 mm 差异也继续记录。

K3FULL 的首轮 run 40283562050 在输入检查脚本编译处失败：10 个 job 均出现同一内嵌 Python 换行 SyntaxError，10 个 native 全对步骤全部 skipped。它是执行入口失败，没有产生几何或容量拒绝结论。修正后的 run 40285103942 仅改两处换行表达式，原首轮 commit 与失败包保留；16 个 runtime 科学源码、材料、十姿态及全部守卫逐字不变，另加入 22 段生成 Python / 7 段实际执行 Python 的语法检查。

跟进仍是六个完整参考姿态加四个左右独立边界接触姿态，计划 **237,818 次 fresh factory / STEP 体对评估**，不复用 pilot 体对结果。每个 worker 原 1,200 s / 1,536 MiB 守卫不变，最多并行两个；基于 K2 完整实测和 K3 pilot 计时，预计 60–105 分钟，另加排队。跟进已实际进入 native。首个 stow_tabs_3 状态已经独立验收：154 体、两进程各 11,781 个完整体对、18 个独立早期门全部通过；factory 252.200734 s、reader 193.500290 s，正交集/错误/不一致均为零。当前只记 1/10 个有限状态通过，其余仍按原 max-parallel=2 队列执行。

[K2 四端点验收](geometry/K2/K2_FOUR_ENDPOINT_ACCEPTANCE.json) · [K3 双 pilot 验收](geometry/K3/K3_TWO_PILOT_ACCEPTANCE.json) · [K3 实际原件绑定](geometry/K3/K3_ACTUAL_DUAL_PILOT_BINDING.json)

### 正 q 的 STOP / SPRING 分段

从四条原 ContactProfile 得到五个联合分段，原二进制浮点边界对应的精确有理数完整保留：

| q 范围，mm（此处显示近似值） | 联合接触分支 |
|---|---|
| 0 … 0.0011145618000001356 | plateau / plateau |
| 0.0011145618000001356 … 0.09055728089999172 | rounded / rounded |
| 0.09055728089999172 … 0.6429179606749895 | ramp / ramp |
| 0.6429179606749895 … 0.6429179606749900 | lower / ramp |
| 0.6429179606749900 … 12 | lower / lower |

第四段宽度为 `1/2251799813685248 mm`，约 `4.440892098500626e-16 mm`，没有折叠掉。最终 STOP 位移幅值约 1.16 mm，左右方向相反；SPRING OD 包络半径 0.43 mm，声明长度从 1.46 增至 2.62 mm。这些是源码几何/接触分支，不证明预压、力平衡、摩擦、回程或动态复锁。

### 左右独立域与真实行程限制

名义槽域为共同 slide `s∈[0,79.75]`、左右各自独立的 `dx,dq`，每侧满足 `|dx|≤0.0252814320072192` 与 `|dx−dq|≤0.035355339059327334`，并由 `q=(12/79.75)s+dq` 联系。加上软件 q 范围后的多面体有 14 个半空间、60 个顶点；左右 5×5 分支中 17 个可行、8 个空，两个精确方法一致。

**去掉人为 q 截断后，原槽域的 32 个顶点中有 24 个超出 q∈[0,12]，极值约为 −0.0606367711 与 12.0606367711 mm。** 两条有限槽的端帽分析也不能给出 q=0/12 处的实际止挡：已核对的 pin 投影距直段/端帽转换平面的最小距离仍分别约 0.754681、0.999907 mm，大于 0.4 mm 的 pin 半径。这不证明所有外域都物理可达；它说明这两条槽不能作为 q 截断的机构依据。

左右伸缩分配也保持独立：每侧三个关节各在 `[0.1,2.9] mm`，和为 `8.5−descent`；共同 descent 为 `[0,8.2] mm`，该多面体有 28 个顶点及 0 / 2.6 / 5.4 / 8.2 mm 分段。默认均分只是一条路径。 这里的 28 个顶点是理想等式与无容差不等式的精确投影。原 stage_allocation 还接受每关节 ±1e-9 mm、总和 1e-8 mm 的薄层；这些薄层必须另行覆盖，不能把 28 顶点称为完整 binary64 允许集。

新增三个连接棱柱相对两支撑柱另有 18 个精确分离证书；这只覆盖这组新增材料和障碍物。真实全机构允许域、实体行程限制、工艺公差与当前强度仍未闭合。

[分段与独立域](domain/POSITIVE_Q_BRANCH_DOMAIN.json) · [未截断槽域](domain/UNCLIPPED_SLOT_SOURCE_DOMAIN.json) · [端帽投影](domain/FINITE_GROOVE_ENDCAP_PROJECTION.json)

## 3. 连续包络：真实失败修复与剩余未决

| 具名执行 | 实际调用数 | 实际结果 |
|---|---:|---|
| L2 首轮 `40273642963` | 0 | 准备阶段的 S4 tree 断言失败，未进入 native |
| L2a `40274339675` | 89 | 4 clear、85 conservative overlap、0 evaluation error；原 postguard 全过 |
| L3 `40274745040` | 70 | 36 KEY/STOP、34 SPRING/STOP 新相关方法均 clear |

L2a 保留完整起终件与每个边界面扫掠：常规平面使用 native prism，近切向平面使用保守区间 carrier，曲面使用完整面原生界，极小非零位移外延后仍包含原端点。原有向体积、有效拓扑、严格 Common、整对总上界与 `1e-7 mm³` 门槛保持不变；没有取绝对值、夹零、跳过失败或删掉极小区间。

原 EXTRUSION 整对已重跑，当前构造先用保守盒覆盖曲面，避开了旧中间表示。实际 audit 没有直接执行 EXTRUSION 面分支，因此直接分支验证仍未完成。原生 bounds 加 padding/nextafter 也尚非严格区间几何证明。

L3 使用真实位移的共同参考系与完整相关 carrier，保留完整 STOP pin 与三个 remainder 的材料守恒、原 KEY 和 SPRING 原件身份。70 次每个完整 frame 的所有 carrier 总 Common 均为零；70 个穿透负向对照均被拒绝，体积为 `0.00013176096605022747` 至 `0.005808804816488513 mm³`。独立记录读者逐项核对了 1,018 个实际 BREP 哈希；这次记录审查没有重新调用 CAD 内核。

**L2 的 4/85 原报告保持原样。** 综合比较新方法后，剩余 **15 个调用、9 个实体对**：两个 panel/KEY 对的 8 个调用，以及 B_SHELL 对 7 个 telescope/flange 的调用。K1 的有限点修复不能直接覆盖这些连续区间。case-014 的 `1.2793811944413415e-7 mm³` 继续判作保守交叠，阈值不变。

完整 SLIDE 原方法耗时 1,236.487 s、13,770 次调用，其中 93.57% 经轴向间隙快速退出。L2 困难 89 调用产生 44,313 个 region，只有 1,901 次 Common，说明构造成本不能忽略。V4 因此先使用当前材料的保守轴界、真实 K1 factory-law probes 和逐 case/region 计时；全量 11,781 对的分片必须验证精确 union、无缺项和无重复，不能把分片完成误称单个原 worker 1800 秒内完成。

[原 89 次独立审查](envelope-review/L2a_ALL89_INDEPENDENT_READBACK.json) · [新 70 次相关审查](envelope-review/L3_ALL70_INDEPENDENT_RECORD_AUDIT.json) · [逐调用对照](envelope-review/L2_L3_COMPARISON.json) · [完整执行接口与容量](envelope-review/FULL_SLIDE_INTEGRATION_PLAN.md)

### V4 原运行导出失败与 V4a 新执行

V4 run 40279094567 的 native 与独立记录读取步骤实际完成；但科学 exporter 对 Common 大写文件名的白名单断言失败。原 partial ZIP 只有 **2,110 B、两个文件**：独立记录检查 JSON 和一个原 whole telescope 输入 BREP。这个原 reader 记录支持五次 factory-law probes、262 次调用、1,632 份 BREP 哈希、17 对中 10 clear / 7 conservative overlap；11,764 个完整体对槽位尚未测试。**完整 producer 报告、逐调用身份/计时及其余 BREP 未被该次上传保存，不能从这个 partial 包恢复，也不能据此声称七对的具体身份已读回。**

原两成员与原 ZIP 均保留。V4a run 40282814142 的 native 与独立记录 reader 已完成，原算法和资源限保持不变；科学 exporter 仍返回失败，但这次完整保住 **262 个逐调用 JSON、1,632 份 BREP**，并已实际核完 10,794,846 B ZIP 的哈希、CRC 及 1,912 个 manifest 成员。缺件是 932,252 B 的 producer 总报告（SHA 42797673…）；原 reader 对同 SHA 已成功解析，因而拒收原因可归入 runtime locator 过滤，具体 offending locator 未从科学包恢复。原 V4 / V4a 两次失败与各自保存范围分别记录。L5 正在提出针对完整同轴环形层的相关扫掠，用真实完整 B_SHELL 验证原七例，再验证当前 K1 的全 q 七对；容量依据是每组十二个 primary layer Common，尚不能直接推出实际耗时。这 262 个原调用进一步确认：两个 K1 panel/KEY 全 q 调用的 carrier 总 Common 均为零，八个同侧 KEY/STOP 与 SPRING/STOP 相关对也 clear。七个剩余体对均为 B_SHELL 与伸缩件/法兰，每对 36 调用；七对调用耗时合计 999.066948 s，全部调用合计 1,033.640670 s，控制器 wall 1,166.881252 s。仍有 11,764 个完整体对槽未测试；非零 KEY/crosshead 独立间隙状态也未因此取得资格。

尚未执行的直接 EXTRUSION 分支、严格区间 CAD 包含及独立五维允许域继续保持未决。

[V4a 实际逐对结果](envelope-review/capacity-V4a-actual/V4A_CAPACITY_AND_EXPORT_FINDINGS.json) · [V4 保留下来的原 reader](envelope/V4-first-run/INDEPENDENT_CAPACITY_RECORD_CHECK.json) · [原部分科学 ZIP](envelope/V4-first-run/S4_V4_partial_science_40279094567.zip) · [独立域覆盖计划](envelope-review/independent-domain/INDEPENDENT_DOMAIN_COVERAGE_PLAN.md)

## 4. 原数值资格：原 K/C 回收，原五探针仍拒绝一项

重装配 K 与 C 出现了真实字节差异，不能以相同源码或极小差值代替原件身份。N4/N4a 的重装配 K 为 `fc21f434…`，不同于原 K 的 `80f6f502…`；N5 首轮重装配 C 为 `da1876a5…`，不同于原 C 的 `9f75b00a…`。这些尝试在输入身份门槛停止，不能记录成新的五探针残差失败。拒绝 K 已单独长期归档，拒绝 C 随 N5a 科学原件保留。

N4b 恢复原 K、b、C、点序、自由/固定域和方向，执行预注册的有界 GMRES 修正。N5a 从 N4b 全场开始，以原 float64 残差驱动固定阻尼的 32 步局部 Jacobi 修正，并恢复原 C 与点序。两次都实际完成原五项：

| 原 probe | N4b 最终 float64 比值 | N5a 最终 float64 比值 | 原 `≤1e-7` |
|---:|---:|---:|---|
| 0 | 1.7609498572804048e-7 | 1.7540169838265448e-7 | 拒绝 |
| 1 | 1.9904777780475510e-9 | 1.9904777780475510e-9 | 通过 |
| 2 | 7.9778400558745000e-9 | 7.9778400558745000e-9 | 通过 |
| 3 | 7.7998978509609030e-9 | 7.7998978509609030e-9 | 通过 |
| 4 | 8.0436383517797490e-9 | 8.0436383517797490e-9 | 通过 |

原判据仍为 float64 `max(abs(Kff @ u − rhs)) / max(max(abs(rhs)),1)`。longdouble 仅为诊断，没有替代原判据。N4b 的 8 步全场/修正链、N5a 的 32 个外层场、32 个修正场、32 个实际更新场、残差和 ULP 链都保留。N5a 第 4 步后最差行的原比值停在 `1.7540169838265448e-7`；其他四项的场数组和文件哈希保持 N4b 原字节。

N4b worker 约 21.12 s、峰 RSS 2,826,440 KiB；N5a 约 21.31 s、峰 RSS 1,061,112 KiB。两次均未触发原资源守卫，不能把增加时间当作已证实的解决方案。后续只读行诊断先核对原 CSC 求和顺序与 float64 bitpattern，再用精确有理乘加分解误差，所得行级候选敏感性不被称为新完整解或原门槛通过。

N6 首轮下载失败只记录 HTTPError，状态码和具体根因未保存。N6a 成功取得原 565,978,451 B ZIP，但额外的“fixed DOF 必须排序”假设拒绝了原文件 [0,1,2,13,14,8]，尚未计算行级试验。N6b 仅修正这一读取假设，保留原 fixed 字节/顺序和原 sorted free complement；实际完成 **38 个行 bitpattern、32 个更新、162 个相邻 ULP 试验**，独立读回一致。

最差行 81 个非零列支持中，有 13 个单 ULP 变化改善这一行，其中 7 个使本行通过且本行精确残差不增。但这些列影响的 264 行只覆盖全场 20 个超门槛行中的 2 个；N6b 没有新全场，也没有新原始五探针资格。N7 run 40285015238 因此预注册最多 32 个完整候选：每个候选保存五个全场/残差和实际更新，重跑原五 float64 门槛，另由独立 reader 逐个重算全部受影响方程的精确残差。只接受受影响精确残差无穷范数不增、全场超门槛行数严格下降、原全场最大比值不增的顺序状态；保留全部被拒候选，原 180 秒等容量守卫不变。该 run 已实际完成并被原资格门拒绝：5 个完整候选、192 次虚拟标量检查，只接受 trial 2；探针 0 从 1.7540169838265448e-7 降为 **1.386574690771972e-7**，超门槛行由 20 减为 19。其余四个原比值和场文件保持原字节。随后当前最坏行 DOF179519 的有限单 ULP 候选耗尽，三个完整候选均不满足全部受影响行的精确范数非增条件；不是 180 秒或 32 候选额度耗尽。独立 reader 实算 35 次原 float64 门、543 个受影响方程的 before/after 精确和，并核 70 个全场/残差/更新数组。worker 9.714064 s、reader 8.930045 s。下一策略将先分析未受影响精确行能否为全局范数提供有效界，原 N7 规则和拒绝结论保持原样。

[N7 实际五探针与拒绝链](numerics/integration-evidence/n7/N7_HOSTED_OUTCOME.json) · [N7 原独立读取记录](numerics/integration-evidence/n7/N7-independent-readback.json)

原五项尚未全部通过，**完整 panel H / frame / trace / restore 仍被前置条件阻断**。panel H 本身为 120,745,800 B；3,885 列全场约 10.695 GB，全场加残差约 21.389 GB，分块减 RAM 不会消除原件保存量。原 restore 还保留独立 `2e-7` H-action 条件，不能由五项门槛推出。

## 5. 电气原生检查与真实资料

E3 run `40269456951` 的实际 KiCad 9.0.9 native readback / DRC 已取得并独立核对。五个执行源码文件、执行前后文件与 S4 Git 原件逐字节相同；14 个报告文件哈希、52 个端子身份与坐标另经检查。结果为 **52 terminals、130 tracks、26 个 C01–C26 研究网络、2 个封装；全 severity（含 exclusion）0 DRC 项、0 未连线**。

这关闭当前研究 ECAD 的原生检查范围。原理图 ERC、OEM 端子赋值、SI/载流/温升、供应商成品叠层与动态 FPC 仍没有资格。另一个 exact-S4 的 EC1 `40273665517` 只到 `kicad-cli version` 环境先决即失败，原 34 个包和五个源码身份通过，但 0 native readback / DRC；它与 E3 的真 pass 分开保留。EC1a 的严格 loader 诊断只输出库名、数字版本、状态与原日志哈希，不公开 raw runtime。

[S4 源字节绑定的实际 ECAD 审查](ecad/e3-native/INDEPENDENT_REVIEW.json)

本轮现有设备接入端点拒绝连接，未取得新的物理观测。没有同一样件的 10 项身份字段原件、7 个实际部件角色及 12 个 OEM 接口证据，也未取得可追溯的实际 OLED/COF/FPC、连接器、材料与工艺选择。通用型号或供应商网页不能填充这些 same-specimen 字段。

## 6. 当前结构、电气和试验合同的可冻结边界

当前输入审查发现 154 个材料条目仍无选定物理参数，13 个载荷工况无来源数值，9 个几何占位件待实际样件替换；摩擦、接头刚度、预载与散差、基准体系、工艺分布和最小壁厚规则仍未定义。不能用零方差、经验默认值或旧安装几何的 FE 结果替代当前切改后结构。

现场交接单保留同候选/同样件、原照片和标签、PN/revision、测量不确定度、朝向、端子来源、原机功能、采样与校准、版本绑定和有来源阈值的要求。当前 S4 空模板的历史生成与绑定检查仍有效，但空模板不是采集；K1 新候选也没有被偷偷绑定为这些旧模板的已测样机。

[当前真实输入状态](physical/PHYSICAL_INPUT_STATE.json) · [现场原件与试验交接单](physical/PHYSICAL_HANDOFF.md)

## 7. 实物 G3 → G4 → G5 与证据保存

真实 G3、G4、G5 本轮测量数均为零。状态分别为缺少真实输入/执行、被 G3 与 OEM 输入阻断、被 G3/G4 与寿命输入阻断；它们保持 unknown/blocked，没有被改成 pass，也不把缺测冒称实测 fail。维修、失效、换件和缺测必须分别记录。

科学保存使用未发布的同仓库证据 draft `423900341`：每个选定源 artifact 的 run、head、ZIP 大小/SHA、manifest 与每个成员/CRC 都先校验，上传后再次下载全部资产字节复核。原件与失败记录保留原字节，工程投影明确标识；排除的 raw runtime 仍是临时 runner 数据，没有被声称恢复或持久保存。最初 HTTP 415 的传输失败也单独保留，文档媒体类型修复后才取得成功回执。

截至本快照，已完成 22 个不同科学 ZIP、共 1,513,361,228 B 的逐成员与上传后整包回读，其中也包括真实失败原件。V4 的两成员部分 ZIP 另按原字节保存于 Git。各阶段确切资产数与完整读取回执见 [归档说明](archive/README.md) 和 [结果索引](SPRINT_RESULT_INDEX.json)。证据 draft 没有发布为产品 release，没有覆盖或删除旧资产。`complete_G2`、`candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 均为 false。
