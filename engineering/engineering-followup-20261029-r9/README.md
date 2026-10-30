# R9：实算结果、完整原件与验收边界

> 本轮已完成原十态有限几何总账、原 16 帧条件体积门及原 K/b/C 数值读回。物理允许域、原生连续 G2、当前结构与电气资格、实物 G3–G5 仍未关闭。

本轮以原 S4 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560` 为功能源，
以远端证据基线 `e51de63915a1abeed29e2f95be3044a5d5965045` 为恢复起点。
命名候选仍为 `key_forward_loop_v1` 与 `panel_key_travel_stops_v1`。
R9 新执行和历史原件读取保留各自身份。目录中的日期是轮次标签，实际执行时间按原 UTC 回执保存。

本轮的明确新增结果是八个原登记姿态的完整 factory/reader，并与原 near/far 汇成十态有限总账；
原 16 帧包络的条件体积门全部通过，并完成完整独立读回；
原 K/b/C 的五个 panel、五个 frame 原 float64 残差也已实际重算并通过。
当前结构的真实材料、机械允许域、完整原生包络和实物 G3–G5 仍有独立未决项。

## 1. 中途见证：原失效、K1、K3 分层对应

| 原登记姿态 | slide / mm | qL=qR / mm | 原 S4 panel/L_KEY Common / mm³ | 原 S4 panel/R_KEY Common / mm³ | 最终具名 K3 候选两侧 Common / mm³ |
| --- | ---: | ---: | ---: | ---: | ---: |
| near | 23.142044210239405 | 3.482188470506243 | 0.24558784938224815 | 0.2455878493822482 | 0 / 0 |
| far | 60.880681403413135 | 9.160729490168748 | 0.23013738353925134 | 0.23013738353925126 | 0 / 0 |

原失败工厂的 154 个参与体与原 F1a whole-material 记录双向材料差均为零，原正碰撞保留。
K1 近/远完整工厂、K3 早期 STOW/PREDOCK 的 153 个 panel 对试点，以及最终 K3 近/远
完整工厂是不同层级。每个最终 K3 工厂和 reader 各有 11,781 对；near 为 777 次 native
Common 加 11,004 次正轴隙判定，far 为 747 加 11,034。

本轮从两份完整封存 ZIP 重新读取顶层原始记录：四套矩阵逐对核对，616 份 STEP/BREP
重核哈希，原材料映射、原门及 source/contract 绑定一致。最终 K3 两侧和全对 Common
记录均为零，producer 与 reader 的 Common 差为零。原 F1a STEP 读回中约 1e-13 的
真实数值差仍保留；它们没有被改成逐位相同。此次原包复核没有重新运行历史 near/far CAD。

证据：[原两姿态完整矩阵读回](independent-review/R9_ORIGINAL_NEAR_FAR_FULL_MATRIX_READBACK_V2.json)。

## 2. 原登记十个有限姿态

原 `full_stop_states.py` 的十个状态现均有实际完成的 producer、独立 native reader 和当前记录独审。
其中 near/far 为 R7 已完成运行的原包复核，其余八态为 R9 新执行；没有把十态写成一次全新单轮运行。

| 原状态 | slide / mm | qL / qR / mm | 体数 | 每角色完整对数 | 执行来源 |
| --- | ---: | --- | ---: | ---: | --- |
| stow_tabs_0 | 0.0 | 0.0 / 0.0 | 154 | 11,781 | R9 新 producer + reader |
| stow_tabs_3 | 0.0 | 0.0 / 0.0 | 154 | 11,781 | R9 新 producer + reader |
| near | 23.142044210239405 | 3.482188470506243 / 3.482188470506243 | 154 | 11,781 | R7 原执行；R9 原包复核 |
| far | 60.880681403413135 | 9.160729490168748 / 9.160729490168748 | 154 | 11,781 | R7 原执行；R9 原包复核 |
| predock | 79.75 | 12.0 / 12.0 | 154 | 11,781 | R9 新 producer + reader |
| open_installed | 79.75 | 12.0 / 12.0 | 161 | 12,880 | R9 新 producer + reader |
| lower_L_contact_R_free | 0.1 | 0.0 / 0.03009404388714734 | 154 | 11,781 | R9 新 producer + reader |
| lower_R_contact_L_free | 0.1 | 0.03009404388714734 / 0.0 | 154 | 11,781 | R9 新 producer + reader |
| upper_L_contact_R_free | 79.65 | 12.0 / 11.969905956112857 | 154 | 11,781 | R9 新 producer + reader |
| upper_R_contact_L_free | 79.65 | 11.969905956112857 / 12.0 | 154 | 11,781 | R9 新 producer + reader |

合计每角色 **118,909 对**，producer 与 reader 合计 **237,818 条对结果**；共重核 **3,094 份 STEP/BREP**，**156 个适用 native 早期门**全部通过。OPEN 包含原 154 体及实际安装的 7 个附加参与体，descent=8.2 mm。原登记输入、同名候选源码/合同、全材料清单和各状态 q 均已绑定。

producer 的方法账为 7,735 次 native Common + 111,174 次正轴隙；reader 为 7,739 + 111,170。OPEN 的左右 `TELESCOPE_2_BOTTOM_CAP` 对 `TELESCOPE_3` 及对 `TELESCOPE_3_CORE_BOTTOM_SHOULDER` 共四对，producer 正轴隙为 `1.1102230246251565e-16 mm`，STEP reader 为 0，因而转为直接 native Common；四条读回 Common 均为 0，原分类一致。全对 Common 差仍为 0；方法路径并非全部相同。原 `1e-7` 判据未改变。

四条原 cam profile 和全部十态源输入已重算；八个新 native 状态中的 64 个 STOP/SPRING 边界映射全部读回，最大边界差 `3.552713678800501e-15 mm`。这仍不是弹簧力、预紧、摩擦或物理可达域的验证。

首版四态 campaign 在完成首叶后受控停止，整体仍记为未完成；其第二态 352 份部分文件、首次停止时的 ESRCH、完整 v1/v2 首叶对照和资源记录均保存。共享 cgroup 的 OOM 计数从 0 增至 3，实际受害进程和原因未知；没有把这些共享事件归因于已成功结束的本轮 CAD worker。

证据：[十态独立总账](independent-review/R9_GEOMETRY_TEN_STATE_INDEPENDENT_FINAL_LEDGER.json)、[几何范围与原件说明](geometry/README.md)、[OPEN 四对真实方法差](geometry/OPEN_STEP_METHOD_BRANCH_DIFFERENCES.json)。

各姿态的全矩阵包含严格正轴隙和原生 Common 两种原判据，矩阵行数不等于 Boolean
调用次数。独立几何 reader 是另一个执行进程，使用同一 OCP 内核；不声称第二种 CAD 内核。
CAD 参与体中仍有设计占位体，完整工厂计数不代表实际器件已经取得或装配完成。

## 3. 结构修复、功能面和独立输入域

K1 的裁刀外包尺寸为 1.10×1.52×0.38 mm，被切掉的原 web 名义材料是
1.10×1.50×0.36=0.594 mm³。保存的每侧实际切除为约 0.5940000000000016 mm³，
新增约 2.623824 mm³。原保留区、裁刀外区域及三个保护 mask 的材料检查继续有效于
它们原登记的范围。

新 U 腿局部截面为 0.38×0.36=0.1368 mm²。原 S4 还有 0.25×0.30=0.075 mm²
的 yoke tab 源特征；与周边的实际重叠和载荷路径仍需完整检查。这些局部尺寸均不构成
全 KEY 的最小壁厚、最小有效截面或强度证明。K1 保护 masks 也不是所有功能面的完整目录。

K3 panel 切除为 0，新增 4.624559999999989 mm³。每侧 lower_post 和 upper_toe
与原 panel 有正体积连接；新增行程接触 patch 为 0.90×0.36=0.324 mm²。
q=0 时为 Y=5.0 的 lower 接触，q=12 时为 Y=17.38 的 upper 接触。
原 cover 的左右 front/rear 四个定向功能 patch 双向面积差为零；它们仍是指定 patch，
不等于全部功能面已抽取并资格化。

### 正 q 时的 cam STOP/SPRING 源分段

| q 区间 | 原分支 | STOP 的源行为 |
| --- | --- | --- |
| q=0 及 `(0,a]` | plateau | 原 home height |
| `(a,b)` | rounded_corner | 原圆角平方根曲线 |
| `[b,c)` | ramp | height 斜率为 −2 |
| `[c,12]` | lower_stop | 原 lower_stop_height 固定 |

`a=0.0011145618000001356`，`b=0.09055728089999172`。
接触 0 的 `c=0.6429179606749895`，接触 1 的 `c=0.64291796067499`；原末位差保留。
该 height 在原工厂中映射到 STOP_i 的 **X 平移**，L/R 符号相反；它不同于 K3 的
**Y 向 q=12 行程接触**。near/far 处于 cam 的 lower_stop 分支，但仍在 K3 两个行程端点之间。

SPRING 是半径 0.43 mm 的 OD tolerance cylinder 几何包络，X 端点随原 STOP 位移扩展。
该表示没有提供真实弹簧刚度、预载、回位力、摩擦或变形解。

### 原软件接受域

公共 slide `s∈[0,79.75]`，公共 descent `d∈[0,8.2]`；`d>0` 要求 `s=79.75`。
每侧各有 tab `[0,3]`、flank `[-1,1]`、KEY 偏移 dq 和 crosshead 偏移 dx。令
`K=12/79.75`，则每侧同时满足：

```text
q_side = K*s + dq_side
0 <= q_side <= 12
abs(dx_side) <= (.425-.4)*hypot(1,K) + 1e-7
abs(dx_side-dq_side) <= (.425-.4)*sqrt(2) + 1e-7
```

左右 dq/dx 可分别取值，但共享 slide/descent；既不要求 `qL=qR`，也不能把任意
`[0,12]×[0,12]` 当作同一工况可取的左右 q 域。

每侧三个 telescope 关节满足 `.1-1e-7<=j<=2.9+1e-7`，同时
`abs(sum(j)-8.5+d)<=1e-7`；两侧共享 d。默认等分没有实际机构保证。
OPEN 附件要求 `s=79.75,d=8.2`。这些是联立的软件输入约束，物理完整可达域仍需
真实保持、回位、摩擦、预载、制造公差及释放顺序证据。

证据：[材料与允许域交叉审查](independent-review/R9_K1_K3_MATERIAL_AND_DOMAIN_CROSSREVIEW.md)。

## 4. 连续包络：原 16 帧条件门通过

| 具名实际计算 | 原帧结果 | 全局分割 | 记录耗时 / s | 最坏原帧交集体积保守上界 / mm³ |
| --- | ---: | ---: | ---: | ---: |
| balanced | 8/16 | 4096 | 517.482501109 | 3.5546081383170135e-7 |
| gradient | 8/16 | 4096 | 348.126441491 | 3.0052596034059657e-7 |
| cylinder/slab，完整 12 通道 | **16/16** | **718** | **552.217835624** | **9.321533029448826e-8** |

三轮均保留完整源码、日志、forests 和独立读回。现行成功轮从全部 1,537 个原根重新
开始，使用完整原 D，最大深度 18，执行 4,722,120 个原边界片测试、13,224 个通道
检查。原限制 4096 次分割、深度 24、12,000,000 片、600 秒及 805,306,368 字节
address space 全部保持；峰值 RSS 449,392,640 字节另记。计时包含初始化、计算和
完整证书序列化，在最终 report 写入前采样；没有声明独立外部 wall-time 测量。

独立 reader 用 265.905903066 秒重新核验原根、完整 D、全部可达节点、全原片 census、
严格 quadric 排除、各格薄层上界和体积账，确认相同 16/16 结果。三个真实证书篡改
负控全部被拒绝。

新方法把同一格内的原 cylinder 投影上界与另一材料的 plane/line 投影下界联合起来，
用完整位移、原基、轴向支撑和向外取界的有理平方根形成保守薄层，再沿原坐标积分。
原格体积与分割守恒单独验证；筛选策略不能代替包含证明。

最终 2,255 个末叶包括 1,493 个原正 tiny boxes、678 个完整通道排除、72 个薄层上界，
以及 **12 个保留整盒的未决格**。所有正贡献全部计入各帧总量，没有删除极小量。
通过表示保守体积上界满足原 `Fraction(1e-7)` 门，并非零相交证明。

### 原 L1 四类反例仍逐项保留

临时 prism、Common 上界、EXTRUSION 三类继承 R3E 的完整有理载体证据及其独立
方向、拓扑和有向体积检查；原 native 失败保持失败。极小位移与相关性由本轮原 16 帧
重新计算及读回推进。27 份继承证据保留原字节，包括 17 个原 case result 和 25 个原错误事件。

仍未资格化的义务包括 native BREP 包含与 filling、编译后的几何误差界、一般
EXTRUSION 的原生扫掠体、完整机械允许域及连续 G2。已成功的 v1 运行未触发其
已知异常保存窄窗口；另命名 v2 的 IO 修复与小型故障控制独立登记，未宣称 v2 全量运行。
候选双通道优化源码保留为准备、未执行。

证据：[包络完整说明](envelope/README_R9_ENVELOPE.md)、
[精确范围](envelope/R9_ENVELOPE_SCOPE.json)、
[独立最终总账](independent-review/R9_ENVELOPE_INDEPENDENT_FINAL_LEDGER.json)。

## 5. 原 K/b/C 数值资格的本轮实际复核

原 K/b/C、原 full fields、原修正历史和原 `1e-7` 门均保持。本轮重新执行 K 产品与
float64 残差计算，没有重跑求解器，也没有把原模型资格转移到当前 K1/K3 结构。

| 原 probe | panel 原判据残差比 | frame 原判据残差比 |
| --- | ---: | ---: |
| 0 | 9.983337773558199e-8 | 5.659897926075834e-9 |
| 1 | 1.990477778047551e-9 | 1.268995135824172e-10 |
| 2 | 7.9778400558745e-9 | 1.9311867265678982e-10 |
| 3 | 7.799897850960903e-9 | 1.2438483918711836e-10 |
| 4 | 8.043638351779749e-9 | 1.7809635438880483e-10 |

原判据使用无量纲归一化残差比 `rho=||K_ff*u_f-b_f||_inf/max(||b_f||_inf,1)`。
10 个原残差比均通过，且与保存的残差字节一致。原 panel 修正 reader 实际核了 45 个
native 门、1,262 个前后精确方程、7 个原 anchor 和 36,180 个候选对。
四个原外载的 scalar 与原 2D block 残差比最大为 2.4101609596982598e-11。

Panel/frame 各 3,885 列 H 的 7,770 个原基 RHS 和保存投影哈希重核，raw H 和原
block 对称化 H 与历史数组一致。没有声称重新执行全部 7,770 次 K 产品，原历史也
没有保留全部这些成功全场。原 `ExactResponseCache.restore` 只执行原 5 个有序、
SHA 绑定的 full-field 动作，最大相对误差 1.1659935073707673e-8，满足原 restore
门 2e-7；任意 RHS 的逆算子和有限 QP checkpoint/resume 仍未资格。

本轮使用 Python 3.12.14、NumPy 2.3.5、SciPy 1.17.0；未重现原 NumPy 2.5.4 / SciPy 1.18.1 环境。
附加 whole-seed 逐位复核中 `loadG=R.T@F` 的 24 个值有 9 个不一致，最大差
2.220446049250313e-16；该失败及精确有理诊断保留，没有改变原门或原数组。
首版 reader 的实际字段/选档错误、修正版及日志也保留。

证据：[数值范围](numerics/R9_NUMERICAL_SCOPE.json)、[复核说明](numerics/README.md)。

## 6. 实物资料、当前结构/电气合同和 G3–G5

本轮找到了 Motorola 官方维修资料分发入口、L2/L3 和维修 BOM 的公开预览，完整 PDF
未取得。可见美国 BOM 明确用于 XT2551-1/-2，现有历史样件记录为 XT2551-3；新预览
未绑定其板卡 revision、OLED/COF、FPC 或连接器端子。新的同样件原件、测量和绑定均为 0。

原 10 项身份、7 个器件角色、12 个实际接口合计仍有 228 项待绑定事实：207 项要求
同一 specimen，21 项要求最终选定 PN/revision。事实数量不等于独立文件数量。
照片/标签、坐标方向、尺寸/不确定度、仪器/校准、端子来源和原机功能必须逐项可追溯。

当前结构仍有 154 项材料分配和 13 个载荷工况需要来源，完整公差、摩擦/接触/预载、
网格/载荷收敛和最坏情况资格未完成。既有 OLED 参考重检在其固定路径族下仍保留
22.088803 mm 长度缺口及 4.94 mm 试片宽度超出；该结论没有排除所有路径族，也没有
选定真实模组。原 E3 研究布线的原生 DRC 通过记录仍有效于其原范围，OEM 端子、ERC、
电源/SI、完成叠层和动态 FPC 尚未资格。

G3、G4、G5 本轮均无实际执行、无真实 pass。阈值来源、采样、校准、时间同步、计划
及同候选/同样件/同装配 revision 绑定未齐，当前合同不能作为已资格的冻结合同。
后续必须有真实 G3 pass 才能进入 G4，再由真实 G4 pass 支持 G5。缺测、真实失效、
维修与换件仍是不同事件；变化后的装配 revision 不继承原 pass。

来源与适用性：[实际资料说明](real-sources/README.md)、
[公开来源适用性账](real-sources/R9_OEM_SOURCE_APPLICABILITY.json)、
[原实物接收合同](../engineering-followup-20261028-r5/real-sources/intake/R3_SAME_SPECIMEN_INTAKE_CONTRACT.json)。

## 7. 交付与发布状态

本轮范围总账为 [R9_COMPLETED_WORK_LEDGER.json](R9_COMPLETED_WORK_LEDGER.json)，
逐项绑定几何、包络、数值、材料/域、OEM 适用性及各自独审的 SHA256。
[三范围独立交叉总账](independent-review/R9_INDEPENDENT_SCOPE_CROSS_LEDGER.json)
保留各层资格边界，不把数值、条件算法和有限 native 结果互相替代。

完整交付分为三个科学包及一份最终汇总/发布审查包：

- **本轮几何原件**：八个新态的全部 STEP/BREP、逐对 JSONL、材料账、控制试验、reader、源码和原失败/部分运行记录均在 `geometry/R9_GEOMETRY_ORIGINALS.tar.gz`，逐成员 SHA256 和全包回读分别见 [manifest](geometry/RAW_EVIDENCE_MANIFEST.json) 与 [回读回执](geometry/ARCHIVE_READBACK.json)。近/远历史原件仍使用各自独立封存包。新交付身份见 [几何保存回执](preservation/R9_GEOMETRY_PRESERVATION.json)。
- **包络证明与源码**：包含本轮完整 forests、原 R8 前置源码、全部真实失败、证书 reader 和实际故障控制。身份见 [包络保存回执](preservation/R9_ENVELOPE_PRESERVATION.json)。故障控制中故意截断的 gzip 仍按失败样本保留；通过的是外层封装和逐成员字节核对。
- **本轮数值读回记录**：包含新 reader、日志、结果、微小逐位差诊断；它不冒充全部原 K/H/全场数据。原完整输入仍在九个独立数值包中。身份与未保留的传输元数据边界见 [数值保存回执](preservation/R9_NUMERICAL_PRESERVATION.json)。
- **最终汇总/发布审查包**：提供本文、范围账、独审、保存身份、最终本地 commit 和精确待发布文件清单，便于审阅后发布。

[十四份原始伴随包索引](provenance/R9_EXTERNAL_ORIGINALS.json) 列出各原包的名称、字节数、SHA256 和保存身份。
新包未重复塞入全部历史大包；重放相关分支需按索引取得其原始依赖。
独审目录的 [49 文件集成记录](status/R9_INDEPENDENT_REVIEW_COPY_RECEIPT.json)
包含 48 份冻结文件与其 manifest；既有文件逐字节保持不变。

当前入口通过原 `tools/sync_current_design.py` 从 `design/current_product.json` 同步；
原 S4 的 36-suite/1654-test 是历史完整运行，本轮未新增完整 unit run。
本地证据分支为 `evidence/full-sprint-20261029-r9`，证据基线仍为
`e51de63915a1abeed29e2f95be3044a5d5965045`。
该分支本轮尚未推送，未合并 main；最终精确 commit 和文件总量以交付的发布审查清单为准。
缺失的原 `a11b00f71231ef3516d2a79c73fa441c375ac755` 及其旧请求分支未被伪造或改名冒充已发布。

所有历史失败、当前失败、未执行优化和未决资格保留各自原身份。
`candidate_go=false`、`manufacturing_go=false`、`all_blockers_closed=false`。
