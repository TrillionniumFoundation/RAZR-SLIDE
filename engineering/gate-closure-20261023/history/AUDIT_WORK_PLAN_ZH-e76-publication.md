# RAZR-SLIDE 全量开发审计与 blocker 执行计划（2026-10-23）

## 最新执行状态：本地完整验证已经恢复

交付分支为 `work/blocker-recovery-20261023`，[PR38](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/38)。整体 **G0–G5 尚未全部闭合**；下面区分已完成执行、新代码待验证与必须取得的外部证据。机器可读入口为 [SUMMARY.json](SUMMARY.json) 和 [BLOCKERS.json](BLOCKERS.json)。

### 精确 e76 的已完成执行

以下结果全部属于 `e76ff339cbd38610b42f550d1d990131233c8f7d`。后续代码变动不会把这些回执改标为新 HEAD。

| 验证范围 | 实际结果 | 可核查证据 |
|---|---|---|
| 全部当前单位 suites | **1,506 tests / 36 suites 全通过，0 failure/error/skip**；1,080 Python 文件语法通过，43 锁定包版本一致，源码前后不变 | [summary](full-unit-e76ff339/summary.json)、[完整原始回执](full-unit-e76ff339/results.tar.xz) |
| 原 native workflow | **10/10 jobs、37/37 commands exit 0**；669 个原始输出逐字节 SHA256 校验 | [索引及全部原件包](native-matrix-e76ff339/EVIDENCE_INDEX.json)、[严格审计](native-matrix-e76ff339/native-matrix-final-audit.json) |
| EP4 native 与独立读回 | 7 regression groups 完成；15,886 pair rows，**55 条几何拒绝保留** | [summary](native-e76ff339/ep4/summary.json) |
| EP5 local/full 与两套独立 readers | local 3,105 pairs；full **154/154/161 bodies、36,442 pairs、123 containment rows**，0 positive Common / escape；endpoint cage 亦实际读回 | [summary](native-e76ff339/ep5/summary.json) |

Native10 的任务为 thin、mounted、coupling、pawl、serviceable、endpoint-joint、catalogue-joint、root-clearance、phone-layout、lateral-guide。最长 lateral-guide 为 **1,642.107 s**，小于原 1,800 s cap，没有删命令或放宽 timeout。先前容量 guard 中断的尝试仍为 failed；后续从完整 job 继续，严格核对唯一覆盖与原件身份后才形成 10/10 结果。

EP4 拒绝分布为 A-local 1、PREDOCK 12、OPEN 25、STOW 17。作业执行通过不表示所有历史研究几何通过；原 pawl 分支正 Common、旧 contact REJECTED 等真实负例保持原身份。EP5 的 containment 仍是乐观 outer union，不能当作实测内部通道公差。

### 输入与环境 blocker 的更新

旧完整单测尝试的缺输入/缺包问题已解决。最终选定输入核对为 **3,265 个已物化文件、0 个选定缺失、282 项冻结 SHA256、10 个原归档 / 682 个原始成员**；所有恢复文件保留原 Git blob 或冻结 manifest 身份。锁环境真实安装并验证全部 43 个包。

证据：[最终输入就绪清单](final-unit-input-inventory-20261023.json)、[锁环境](locked-environment.json)。这不宣称全部历史约 3.55 GB 归档内容都重新读过；完整树审计与当前所需字节重验各自保留范围。

### 第二轮实质修复与新配置

在第一轮 donor 必填字段、EP5 原始结果一致性、锁环境/HEAD 核验、严格 CI 分片聚合之外，本轮继续修复：

1. **材料分区容差漏判。** 同一完整零件相对同一障碍的 pin/余体/扫掠区域共用一个 `1e-7 mm³` 预算，用非负 Common 的和作保守上界。真实 CAD 反例中两块约 `9e-8` 各自低于阈值，实际中间姿态交叠约 `1.8e-7`；新判据正确拒绝。不同物理对、不同姿态及依次发生的路径段不混合求和。
2. **包络缓存错用材料体。** 缓存绑定实际 native 对象、拓扑及位置；相同 caller label 不能把环体的清除证据复用于实心体。
3. **独立控制真实作用于材料。** 左右连续 flank、KEY/crosshead offset、telescope allocation 均有显式入口；槽约束、捕获范围、固定和及有限 contact profile 严格核对。未知端点分支拒绝执行，不截断坐标假装验证。
4. **旧 producer/reader 的源码闭包。** 所有改动入口绑定实际执行的 sum helper，并在全部计算结束后做 source postflight。五个 legacy 入口保留原 130 标量记录，完整 STOP–KEY 的 pin+三余体由 reader 的实际重算值归并。
5. **连续固定姿态全参与件验证与 required CI。** 新增三态完整控制/telescope 域作业，scope guard 要求对应顶点域、实际 pair 完整性、expected HEAD 和锁环境，旧名义报告不能代替新域报告。

新增 **27 个控制/判据 focused tests + 12 个 legacy tests 全通过**，包括真实材料反例、源码篡改拒绝及 4.1 mm 座合时 108 个实际 split 材料的逐体双向差分。独立复核还发现 CI 后置检查会接受行数正确但材料对重复的 synthetic 报告；新增不导入 CAD 的 reader，从原始参与件派生全部唯一无序对，同时重建实际 HEAD/执行文件/锁环境、核对完整域与原始数值，**13 个 synthetic 正反回归通过**。配置最低数已更新为 **1,558 tests / 36 suites**（repository 199、product 190）。**新配置数不是新源码完整执行结果；canonical 验证应在后续新 functional commit 上单独运行。**

对旧 native 原始字节独立重聚合 **17,726 组 region/material partitions（含 30 组显式材料分组）**，全部原 clear 组的和均为 0；另 5 份冻结 legacy reports 的 20 组也全部为 0。因此此项判据收紧未改变这些具体旧结果；没有声称在新 HEAD 上重复执行了旧 CAD。

证据：[新增回归与每文件身份](regression-reviews/PATCH_MANIFEST_V5_EXTENDED.json)、[legacy 回归](regression-reviews/legacy-focused-tests.json)、[独立后置检查回归](regression-reviews/postguard-PATCH_MANIFEST.json)、[旧字节重聚合](native-matrix-e76ff339/legacy-partition-reaggregation.json)。

### G2 已推进的范围与剩余范围

新固定姿态验证包含所有 154/161 个完整材料体和每一无序材料对。每侧三关节满足 `0.1≤ji≤2.9`、`j1+j2+j3=8.5−descent`；完整凸多边形顶点给出每对材料相对 Z 位移的线性投影，左右分配独立。一级、二级 telescope 及各 bottom cap 的 8 个移动体全部列入，第三段由固定和约束定位。

| 姿态 | TAB 域 | flank 域 | telescope 域 |
|---|---|---|---|
| STOW | 左右独立 `[0,3] mm` | 左右各 `[-1,1]` | 每侧固定和 8.5 mm，完整三顶点凸域 |
| PREDOCK | 两侧均释放于 3 mm | 左右各 `[-1,1]` | 同上，左右分配独立 |
| OPEN | 两侧均释放于 3 mm | 左右各 `[-1,1]` | 每侧唯一 `[0.1,0.1,0.1] mm`，七件附件全部包含 |

已完成的 v3 scratch 诊断仅覆盖名义等分 telescope：三态 **36,442 对全部清除，0 evaluation errors**。另 6 个非名义完整场景合计 **71,785 对、4,594 次实际 Common、0 positive/error**，实际使用非零独立 KEY/crosshead 与不等 telescope 分配。这些报告明确 `canonical=false`，不能代替新增扩展域或全行程证明。

新扩展域的完整运行仍需后续 canonical 回执。保守包络有交叠时保留 unresolved；有限无碰撞样点不能取消 unresolved。实际碰撞反例必须从可行输入重新构造完整场景复现。方法使用同一 CAD kernel，没有形式化定向舍入证书。连续 slide/seating、非零 KEY/crosshead 域、附件装拆、全材料耦合与反程仍需完整证据。

证据：[域合同](nominal-control-domain-contract.md)、[v3 三态与六有限场景原始归档](regression-reviews/g2-v3-control-and-finite-diagnostics.tar.gz)。

### 数值恢复已进行实际大计算

PR35 全部 11 个仓库输入已恢复；另 11 个外部缺失文件恢复了 **8 个原 SHA256 字节身份**。原 K_panel、K_frame 和 response.npz 字节尚未找到，故新矩阵单独标为忠实重建；原历史报告不能与新 K 哈希拼接。

| 实际重建 | panel | frame |
|---|---:|---:|
| 原 tetrahedra | 57,620 | 79,628 |
| 完整 L2 DOF | 344,103 | 474,726 |
| K 非零项 | 23,646,483 | 32,719,176 |
| 装配能量相对核对 | 约 2.27e-14 | 约 1.86e-14 |
| 六刚体模态作用核对 | 约 4.41e-13 | 约 1.56e-13 |

原坐标/DOF 映射、E=1/ν=0.3 归一化、固定 DOF 和边界 P2 trace 均保留。能量/刚体核对不是原五次 inverse-operator probes。

Panel 大分解已真实成功，峰值约 2.56 GiB RSS；原 3,885 列响应完成并 flush **2,560 列**，最大已观测自由度残差约 `2.71e-9`。共享内存 guard 触发后，完成列、C、ordered points、输入/源码和 H 前缀全部冻结哈希。这是可续算的部分线性响应，**不是已收敛 QP checkpoint**。

原 46+40 个表面 trace 接口也已真实核对，面/父 tet/局部次序唯一对应，原局部凝聚块差异不超过约 `1.03e-14`。显式新身份的低内存 Schur adapter 已准备。对真实稀疏图执行 ND 排列并精算符号填充后，发现该排列比 panel 已测 MMD 更差；frame 的独立 L/U 条目约 4.15 亿，基本数组就约 4.99 GB，因此没有冒险做该排列的大分解。小规模数学验证不等于大模型 factor、全 H 或接触收敛。

当前共享资源阻止续算：已准备的等价只读 Kff 映射版本保持原 MMD/模型/约束/阈值，启动要求可用磁盘至少 1 GiB、执行中保留 500 MiB，并继续保留 4.25 GiB address-space 与 6.8 GiB 全局内存 guard。记录时普通可用磁盘约 0.64 GB、共享不可回收内存约 5.15 GB；不得把 root 保留磁盘块计入新任务预算。仅清理已完整归档并核对的重复副本；没有活动数值 worker 或无限等待的观察器。

新增 [数值复现源码与全部小型回执](numerical-recovery/reproducibility/README.md) 保留 100 个代码/JSON/日志文件、实际命令、依赖身份、失败/未启动/中断记录和后续严格资源守卫。它不包含大型矩阵，且明确区分已执行源与尚未执行的新 adapter。

数值后续为安全资源窗口内完成剩余 panel 1,325 列、完整 frame H、原五次 inverse probes、完整初始 restart，然后执行原 QP/全域审计；不通过放松约束、目标、载荷或阈值获得通过。当前 EP5 新结构仍须独立资格化。

证据：[外部原文件恢复](numerical-recovery/exact-PR35-input-recovery.json)、[部分响应回执](numerical-recovery/panel-partial-response-receipt.json)、[panel 工件](numerical-recovery/panel-L2-artifact-receipt.json)、[frame 工件](numerical-recovery/frame-L2-artifact-receipt.json)。

### Hosted CI 与下一步 work plan

e76 run [39907440200](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39907440200) 有 16 个 job records：15 failure、1 skipped，**0 runner、0 steps、0 artifacts**。两种 runner 均未启动。四个 pinned action commit 均可解析；annotation 正文仍不可读，当前原因未知，不将历史 billing 原因套用。[管理员最小交接](ci-e76ff339/hosted-admin-handoff.md) 已列出两类 runner 的 check IDs、只读 API 和所需原始注释。

| 优先级 / 条目 | 下一项动作 | 真实完成出口 | 职责 |
|---|---|---|---|
| P0 / 新源码验证 | 在新 functional commit 跑全部单位、EP4/5、扩展三态连续控制域 | 同一源码/锁/实际输入、完整材料与 pair、失败保留、前后身份一致 | 软件 / 几何 |
| P0 / G0-02 | 读取本次 annotation、修复 hosted 启动条件 | 实际 runner steps、严格单位聚合及全部 required native artifacts | 仓库 / 组织管理员 |
| P0 / G0-NUM | 完成全 H、原五次 inverse probes 与完整 restart | 未改数学合同、完整 C/H/ordered-points、真实保存/恢复闭环 | 数值 / 计算资源 |
| P0 / G1-01 | 同一 donor 实物标签/测量/端子交接 | 10 个未知身份、7 原件角色、12 端子接口全部原证据绑定 | 硬件 / 集成 |
| P0 / G1-02 | 冻结 OLED/COF/FPC、电池成包与工艺边界 | 真实版本、动态限制、膨胀/极耳、材料/连接/公差可追溯 | 材料 / 电气 / 工艺 |
| P1 / G2-02/03 | 完整滑移/座合/非零 clearance/装拆/反程及实测公差 | 全允许状态与材料连续证据；保持、工具访问、最坏边界达到预声明标准 | 机械 / 几何 |
| P1 / G5-NUM | 原全域接触收敛；另建 EP5 修改结构模型 | 原 gap/force/compliance 阈值、独立场审计；真实载荷/预载/支承/接头 | 数值 / 机械 |
| P2 / G3 | 编号无电实物完整装配和循环 | 原始标定记录覆盖 skew/release/jam/hold/return/relock | 样机 / 测试 |
| P2 / G4 | 静止及运动供电/充电/USB/显示/触控 | 原保护链、完整连续原始日志及失败记录 | 电气 / 测试 |
| P2 / G5 | 结构、寿命、工艺稳定性、检验和追溯 | 受控样本、预声明 load/cycle/process 标准与不确定度验收 | 制造 / 质量 |

`candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 均保持 false。软件、名义 CAD 或原归一化 FE 不能代签当前实物试验。

---

## 以下为首次发布时的历史基线与初始计划（保留原文）

以下“尚待”“缺失”等表述属于第一功能提交前的历史状态；最新进度以上面的执行记录和 SUMMARY.json 为准。

## 科学与工程基线

本轮以真实远端对象和执行证据审计，不按分支名或测试配置数量推断完成度。

| 身份 | 固定提交 | 状态 |
|---|---|---|
| main | `a1b3cc1e0773446f2e36d0a607edf61211dd9919` | 已合入研究主线 |
| PR36 / 产品集成 | `e25cf001c1b714514d501de4c16d1592fde06b61` | 基于 main，16 个提交，未合并 |
| PR37 / gate closure | `2a8893743c7e90935b1594e619eab9f2ae46b872` | 基于 PR36，3 个提交，draft；本轮工作基线 |
| PR37 真实旧执行源码 | `0d97d8021dc508a40eb2565f6683c6dfba2659f4` | 旧原生与单测回执固定于此 |
| PR35 / rigid bearing | `176df31ceb35bb3737d68030e60ba377665de210` | 与产品集成分叉，draft，保持独立 |

开始审计时的远端库存为 **40 branches、37 PR（32 merged、3 open、2 closed without merge）、127 workflow runs**，没有独立 issue。40 个分支逐一与 PR37 基线核对：35 个已经包含在基线历史中；5 个仍有独立提交。独立项包括 PR35、已替代的 body-guide delivery/PR17、已替代的 spatial-contact/PR25，以及旧 cover-admission、stow-continuous-insertion 候选。后四项保留其原失败或替代身份，不能因未合并而直接拼入当前设计。

完整基线 Git 树由 **954 个树对象、28,250 个路径条目**核对。大型原始 archive blobs 只核对树中身份，未宣称全量原始归档 3.55 GB 内容重新验证。所需 Python 源、当前工程输入、测试依赖和选定历史资料按原 Git blob 逐一恢复。主线、当前产品候选和独立数值研究各自的结果不互相代签。

## 开始时的真实进度

既有代码已实现等尺寸 A/B 舱、单柔性 OLED 平铺储存、名义滑移/座合、完整 FPC 端接、手动控制、研究 PCB/端子清单、接触数值模型及物理证据合同。这是可执行的工程研究系统；尚没有完整、合格的物理手机样机。

- 旧 EP5 名义三态研究已验证 154/154/161 实体、36,442 对、123 项乐观外域包容检查及独立 STEP 回读。
- 旧完整单测尝试实际运行 1,251 tests：25/36 suites pass、11 fail、16 missing-input/dependency errors、0 assertion failures。1,461 是旧配置最低数，不是该次通过数。
- 旧 EP4 七组回归通过；当时三态实体验证因原 mounted tar 缺失而未执行。
- 最近 publication-head run 39757637822 的 14 jobs 都没有 runner steps，不能当作已执行测试失败或通过；本轮未核实该次平台失败的具体原因。
- 全部 G0–G5 总门槛仍 blocked；G2-01 的有限名义子项不能替代全程运动和产品验收。
- 4700 mAh 是未验证的整机目标；实际 A/B 电芯与成包边界未冻结。原 PR34/35 结构模型不资格化 EP5 新开槽壳体、KEY 和 A web relief。

## 本轮实质修复与恢复

### 输入与环境

六个旧执行缺失的工程归档已取回原始完整字节，合计 **19,108,049 bytes**；容器 Git blob/SHA256 与全部 608 个成员（598 STEP）的原 manifest 一致。归档原本在仓库中，本轮解决的是本地运输/可用性问题，没有生成替代容器。

PR35 列出的 **11 个仓库内输入、6,930,605 bytes**也已精确恢复。8 个原 owner volume 文件及 3 个 legacy response seed 仍未移交，不能用位移场代替完整 C/H/ordered-points/exchange checkpoint。

在隔离环境实际执行 `uv sync --locked --no-cache`，全部 **43 个锁定包**安装并核对，包括 CadQuery 2.7.0、OCP 7.8.1.1.post1、NumPy 2.5.4、SciPy 1.18.1、Shapely 2.2.0。旧共享环境存在 22 个缺包/版本漂移。本轮不修改共享环境。

### 防止资格与进度误报

1. **donor 字段删除漏洞**：旧配置可删除未知字段，仅提供 model 就被判为完整身份。现在由代码固定全部 11 字段，配置、导入、已绑定读取共用校验；未知字段保留 null，缺失/多余/错误类型都不能缩小门槛。真实 10 个未知身份、7 部件角色、12 端子缺项仍保留。
2. **EP5 结果汇总漏洞**：旧 wrapper 可接受与逐姿态拒绝相矛盾的顶层成功标志。现在由全部 pair/containment 原始数值及局部 endpoint cage 检查派生结果；独立 reader 同样核对并实际回读 cage 与正交集工件，保留所有真实负例。
3. **未锁环境误报风险**：canonical 单测入口新增 Python、项目依赖、完整 uv lock 和 Git HEAD 字节核验。未锁执行只能作为明确诊断，不能给出 canonical pass。
4. **CI 分片证据完整性**：全部 suites 从受控 manifest 生成；聚合要求同一 SHA、run/attempt、锁、manifest、源码快照、唯一 suite 覆盖、实际 test IDs 与最低数，拒绝缺项、重复、跳过、失败或跨运行混合。PR/push 触发支持工作分支与 stacked PR。原 native gates 继续独立要求执行成功。

以上条目是实现/输入恢复记录。**本文件首次提交时，新功能源码的完整测试、原生执行及新 hosted run 尚待结果；后续结果写入本目录 SUMMARY.json 与执行回执。** 旧报告保持旧源码身份，不作为新 HEAD 重跑证据。

## 下一步 work plan 与逐项出口

| 优先级 / 编号 | 可执行工作 | 真实完成条件 | 职责角色 |
|---|---|---|---|
| P0 / G0-01 | 在固定新源码跑 EP4、EP5、独立 readers | 所有实际输入与源码前后身份一致；完整声明参与件及原负例得到读回；执行成功与几何拒绝分开记账 | 工程 / 几何 |
| P0 / G0-02 | 恢复所有测试显式输入，在锁环境跑全 36 suites；取得新 hosted steps | 达到更新 manifest 的真实最低数，零 error/failure/skip，前后源码一致；保留真实 run/attempt/artifacts 与聚合回执 | CI / 工程 |
| P0 / G0-NUM | 移交剩余 volume/response seed，或执行有独立新身份的忠实重建 | 输入可核；完整 C/H/ordered-points 状态可保存恢复；原五次算子 probes 通过；未执行求解不记收敛 | 数值 / 原工件保管 |
| P0 / G1-01 | 取得同一 donor 原件标签、校准尺寸、出口和端子 | 补齐 10 身份、7 部件角色、12 接口，原件、标定、版本逐一绑定 | 硬件 / 系统集成 |
| P0 / G1-02 | 冻结 OLED/COF、FPC 成品叠层动态限制、电池成包、连接和工艺 | 所选版本的供应方资料与实测边界可追溯；未知值不填为推测合格 | 材料 / 工艺 / 电气 |
| P1 / G2-01 | 保持并在受影响变化后重验名义三态 | 同一配置完整参与件、全对矩阵和包容域、独立回读；不扩大到完整 G2 | 几何 |
| P1 / G2-02 | 定义机械可实现的释放、滑移、座合、附件装拆与返回轨迹 | 覆盖左右独立 tabs、slot flank、telescope 分配/回差、释放/复锁；完整允许状态域连续正反程证据 | 机械 |
| P1 / G2-03 | 实测公差、装拆与保持连接、工具/工装访问、最小壁厚 | 全部材料与障碍件保留；实际工艺/部件最坏边界下满足预声明标准 | 机械 / 工艺 |
| P1 / G5-NUM | 原数值复现与当前 EP5 结构资格分开执行 | 真实材料、载荷、预载、支承、接头及新截面；全域接触与收敛、独立场审计 | 数值 / 机械 |
| P2 / G3-01 | 同一实物无电装配、保持、释放、卡滞、返回复锁试验 | 预声明计划、校准、原始视频/日志、量测不确定度；fail 不被缺测抹掉 | 样机 / 测试 |
| P2 / G4-01 | 原保护接口下带电供电、充电、USB、显示与触控 | 静态及全程运动真实原始功能记录；26 通道低速样片不能代替高速/功率功能 | 电气 / 测试 |
| P2 / G5-01 | 结构、耐久、工艺稳定性、检验及追溯 | 所选配置受控实物满足预先定义的寿命/载荷/过程标准，再决定制造放行 | 制造 / 质量 |

环境和原件恢复可与同一 donor 取证并行。G2 的真实尺寸、公差、材料判定依赖 G1；G3–G5 依赖相应配置、物料和实物试验。软件能自动判定记录的完整性与逻辑，无法产生尚不存在的实物、供应商资格或测量原件。

## 交付规则

每个闭合项记录被执行提交、源码/输入哈希、适用范围、原始日志、判据与 pass/fail/unknown。测试最低数随新增有意义负例更新；不删历史失败、不跳过缺输入测试、不降低公差或接触阈值、不把研究通过转为产品放行。功能执行提交与证据发布提交分别列明。

本轮保持 `candidate_go=false`、`fixture_fabrication_go=false`、`manufacturing_go=false`。后续总门槛状态以实际结果与仍缺的输入为准。
