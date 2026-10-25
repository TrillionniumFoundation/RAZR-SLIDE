# RAZR-SLIDE 十工作包执行状态与下一轮验收路线

**状态整理：2026-10-25。严格沿用用户原十行及 P0 / P1 / P2 顺序。** 本文与执行报告、原始证据索引共同记录本轮实际执行和剩余依赖。下列“负责人”是下一轮应明确落实的**职责角色**，不是已指派的个人，也不代表已发出联系或取得承诺。

## 一、总体结论与身份

**唯一候选 S4 的软件集成资格已经完成：36 套 / 1,654 项同版锁环境测试全部通过。** D6 同版三组有限 KEY 原生对照全部完成，两组 v2 点 clear、none 对照四个真阳性保留。C2 的 36/1,641 和 188 mm 研究板真实 KiCad DRC 0 项保持各自历史来源；S4 没有重跑原生 ECAD。完整 G2、当前结构和真实 G3–G5 未通过。[D6-unit] [D6-geometry] [E1-ecad]

| 身份 | 已发生事实与使用边界 |
| --- | --- |
| **S4 唯一当前候选** `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560` | tree `cdd9e2c41216201b6cd04dd610d45fde80499045`。实际 D6 全 36 套 / 1,654 项通过；同版三组有限 native 已完成并独立复核。候选 ref 已推进；E3 台账提交不改被测源身份。[D6-unit] [D6-geometry] [S4-advance] |
| **C2 历史被测源码** `bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb` | tree `0eb5fb6c13645b6ce6ff9aec765d5465007efc13`。36/1,641 历史软件与 ECAD、D4/L1 等原生回执继续绑定此源；不改标为 S4。 |
| **E1 已发布证据** `bf1064b1be153fcd7ca6b96a8465653275518548` | 软件、原生 ECAD、资格模板及继承 wheel 字节核对的证据归档。 |
| **E2 已发布证据** `006222404a1dbecb7df6b35514325f6f075e5d3a` | parent E1，tree `55b7a9c29d3412397dd2c2344fc4e6fad4b34b97`；已追加 canonical STOW/OPEN、SLIDE r3、SEATING r3、finite FULL_BAND 与现场交接。**不再是待发布项。** [E2-index] |
| **原 v4 本地历史与 D4 完整执行** | 先前本地仅完成 1/6 的资源失败原件保留；D4 后续已实际补齐六组、两份新基线、一个独立有限 ORTH 及严格 resume。六组中四组 clear、两组 STOW 各四个真阳性，不能把十个 jobs success 写成六组几何 clear。[LOCAL-v4] [D4-complete] |
| **独立 hosted D1 / D2** | D1 `94f0bdadec7bdad843693846bb44a305ea3c7d0c` 检出 C2，但安装阶段失败、零 native；D2 `db8ce6b1a9ea3ca0608903c8126e5a24789e4d74` 只运行资源接口探针，没有检出/执行 C2。两者均独立于被测功能源码身份。 |
| **S3 功能源与后继证据台账** | S3 `20dfddfe8497a73b1814623e6320b3a9ac4273d0` 是 E2 后的十文件功能修复，tree `346eb145bd243ef829b9a540b36dfc830d7298f3`。D5 已对 exact S3 实跑 36 套 / 1,654 项，保留一条生成入口同步失败；两组 v2 有限点 clear，none 对照四阳性。S4 仅同步三份生成入口，D6 同版 36/1,654 实际全过，三组原生对照完成，唯一候选已推进 S4；后继证据/台账提交与实际被测源分开，旧回执不换 SHA。[S3-source] |

C2 冻结时保留的 `pending` 文本属于历史源码状态；后来完成的运行由绑定 C2 的 E1/E2 及新增原件说明。`candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 仍为 false。没有把研究执行进度换算为整机完成百分比。[C2-overview] [E2-index]

## 二、原十工作包：实际状态、责任角色、下一步与验收

| 用户原工作包 | 本轮实际完成 / 未完成 | 负责人角色 | 下一条可执行动作 | 验收证据与前置条件 |
| --- | --- | --- | --- | --- |
| **P0-1 统一候选** | **完成软件集成验收。** 唯一候选 S4 `dd7def6e…`；D6 exact-S4 全 36 套 / 1,654 项实际通过，全部异常计数为 0，43 锁包与 6,895 源/输入路径前后核对。三组有限 native 完成后独立审查，候选 ref 实际快进与 API 回读通过。S3 的一条真实入口同步失败和 C2 原回执均保留；PR36→37→38、a9aaf481、主线 README、PR35 独立身份已核。[D6-unit] [D6-geometry] [S4-advance] | 软件集成 / CI；独立验证；配置管理。 | 后续功能修复从 S4 开始；每个新源码取得自己的完整验证。当前 E3 只承载结果和入口台账，继续保持 PR draft、产品放行 false。 | 已取得同一 S4 的原 report、36 套日志、1,654 个逐项身份、manifest/hash、环境与生命周期回执；完整原件私有保存，公开工程聚合与原件哈希。后继证据提交不冒充被测源；实物资格独立验收。 |
| **P0-2 真实器件** | **外部实物阻塞。** 历史 donor 型号 `XT2551-3`、specimen `XT2551-3-41ad305f` 已见于原记录；但 **10 个身份缺项 / 7 个零件角色 / 12 个真实接口仍未补齐**。本轮没有实物拆机、标签尺寸和带电原机基线。[C2-interfaces] [现场交接单] | 现场拆机 / 计量；器件工程；电气系统。 | 按已交现场清单先确认同一 specimen 和完整原机基线，再采集各角色标签、版本、三维包络、退出/装拆方向、端子及原始照片/日志；先登记“已取得 / 缺失 / 不可读”，不靠型号补值。 | 同 specimen、受控 PN/revision、原照片与量具校准、尺寸原始值及不确定度、逐针来源、时间/原始 path/hash。每个角色与接口能对应实件及原机功能；只有型号一致不能关闭此 WP。 |
| **P0-3 OLED/FPC** | **研究约束和差口已查明，真实选型未冻结。** 当前 EP5 路径族最小长度约 187.768803 mm；公开参考 OLED 71.940×165.680 mm 相对其有 **22.088803 mm 长度不足**，相对 67 mm trial 宽度多 **4.940 mm**。网页与 preliminary PDF 型号不一致，资料 reliability 为 TBD；不是 selected 件。OLED 0.2 mm / FPC 0.1 mm 仍是研究几何假设。[C2-route] [C2-oled] | 显示 / 柔性互连；机构；器件来源管理。 | 在 P0-2 实件身份基础上，取得完整成品叠层、COF/触控/连接器包络、固定与不可弯区、总长宽厚公差、出线方向、动态弯曲/拉力/寿命条件的受控来源，然后作保留路径或改版决定。 | 同一真实 PN/revision 的完整资料与实测一致；不能把 substrate 0.408 mm 当模组总厚，也不能拼接不同模组资料。动态阈值须有适用材料、方向、循环、环境与装配条件；缺来源继续 unknown。若改路径，建立新候选并重验相关机械/电气域。 |
| **P0-4 KEY** | **原 v4 六组与严格恢复已完整，真实碰撞未隐去。** D4 STOW 0.001 和 OPEN 三档 clear；STOW 半带/全带各四个 native Common 阳性，0 error / pending；每组原四条 profile 拒绝仍在。独立负 dq ORTH 的全部 11,781 对 clear。第一层有限退让全带保留两处约 0.00649356 mm³ 真交集，据此冻结 S3 两层 v2 四体/14盒研究；D5 与当前 S4/D6 各自完成三组全新验证；D6 两个 v2 有限点全对 clear，none 对照四真阳性仍在。[D4-complete] [E2-KEY] [S3-source] | 机构 / CAD；运动学与真实接触；独立证据复核。 | 同版 D6 三组已完成；下一步按真实 factory 重建正 q 时 STOP/SPRING 运动体清单，分段验证逐侧二维及左右独立域。实体止挡、接触约束或结构修复需要真实机构证据。 | 原六组材料/逐对/阳性/严格 resume 已取得；已取得的新 v2 有限 clear 仅适用于实际点。144 跨侧 X 证书只覆盖所列 24 体刚体 STOW 研究，不涵盖完整正 q factory、OPEN、SLIDE 或手动动作；加工公差、剩余强度与完整连续域仍须独立验证。 |
| **P0-5 SLIDE / SEATING** | SLIDE 原 r3 全 11,781 条已留存：**11,762 clear / 10 conservative unresolved / 9 evaluation failure**，pending=0；59 个递归 error 分布在17个pair中。S3 已修两个 standalone reader 入口顺序，四个新进程回归含 foreign-module 拒绝反例；此源码修复没有消除几何失败。L1 两组89次原调用均已实际逐值复现，保存真实Common/失效棱柱及异常，原19对判定仍未闭合。SEATING 声明的 11,781 外部体对全 clear，KEY/crosshead=0，左右独立伸缩分配已覆盖。[E2-SLIDE] [E2-SEATING] [S3-source] | 机构 / 运动学；CAD 内核与包络算法；独立验证。 | 先对 slide≈23.142和60.881mm处 A_BACK_PANEL/左右KEY的四个名义刚体整件见证做完整factory与独立原生读回，再进行结构修复。依据 L1 已取得材料分别修复：5 个左侧临时prism负体积、3个右侧无效Common、1个EXTRUSION以及8个极小精确区间；原72条保守分类保留，其中8节点已有整件端点见证推导，另64个height/spring包络仍需相关性解释。保持原区间与物质守恒，另冻修复源及反例，再补非零偏移、连续柔性、独立分配及正反程。 | 原错误、未决与未执行分开保存；不把全部19条称为实体碰撞，不捕获后改 clear。新的观测/方法修复有单独源码和输入身份，须保留原 pair/精确区间/资源过程。SEATING 外部域通过不外推柔性自有效性、真实载荷或整个 G2。 |
| **P0-6 panel 五探针** | **原数值资格仍失败，失败类型已区分。** 旧三策略均原五探针4/5，probe0原float64比值高于1e-7；更低 extended 值只作诊断。新 N1(COLAMD+threshold1)与 N2(MMD+threshold1)对 exact-C2 输入真实运行，均在 LUSUP 扩容阶段失败，五 RHS 已存但 **0 solve / 0 residual**。N2采样VmSize距6GiB AS仅约1.96MiB；N3只改AS8GiB后在原180s墙时守卫终止，依然0solve/0residual。原frame5/6GiB失败及所有原件保留。[C2-num] [C2-frame] [N1-evidence] [N2-evidence] | 数值 / FE；稀疏求解器与计算资源；独立数值验证。 | 根据 N1/N2/N3 完整记录建立下一次分解时间/峰值容量或替代算法的可复核依据；原K/b/C、五RHS、float64 1e-7与原restore条件保持。未证明分解完成前，不启动全响应，也不把后段内存回落解释为接近完成。 | 完整五探针通过后再推进同策略全响应及另一侧验证；两侧资格和原H/trace/restore条件必须实际取得。AS接近上限支持一次对照，不证明分配失败只有这一原因。每次保留原RHS、原场/残差、分配失败或未执行状态；旧模型不替代当前EP5结构资格。 |
| **P1-1 当前 EP5 结构与公差** | **结构输入合同已交，当前结构资格未完成。** 实际 STOW 154 完整实体清单、材料/13 类载荷/支承接触/预紧/工艺公差缺项已有合同；尚缺真实材料批次、摩擦/连接刚度、载荷来源、最小壁厚工艺与公差分布，未完成完整当前 FE 网格。[C2-structure] | 结构 / FE；材料工艺；尺寸公差 / 计量。 | 依真实器件与稳定几何，把每个占位件替换、材料、接触/支承和载荷缺项绑定到实件、来源与责任；先冻结建模输入，再生成当前装配 FE / 公差模型。 | 依赖 P0-2/3 和 P0-4/5。需全局力矩平衡、外功/应变能、独立全场、网格及载荷/增量收敛，覆盖最坏装拆/保持/复锁。bbox 不能充当壁厚、`E=1` 不能充当真实材料、未知公差不能置零。 |
| **P1-2 同版电气互连** | **188 mm 研究 ECAD 原生资格完成，产品电气尚未闭合。** EP5 总长 188 mm、自由段 164 mm，26 路研究网、52 terminals / 130 tracks，真实 KiCad 9 wrapper/native readback/全 severity DRC **0 项**，板字节与源闭合。[E1-ecad] C01–C26 是自有导通测试网；实际 OEM pinmap、电池 A/B / 充电 / USB / 显示链路和固件控制基线未因此确定。 | 电气系统 / PCB；柔性互连；原机软件与固件集成。 | 在 P0-2 实件 pinmap 与 P0-3 成品 FPC 资料冻结后，建立实际原理图、端接、保护和供电/高速链路合同；先与原机功能基线逐项比对，再做受控互连设计。 | 真实逐针来源、实际叠层、载流/温升/阻抗与动态条件闭合，取得对应 ERC/DRC、SI/PI 和功能/电气实测原件。DRC 0 不证明 OEM 分配、充电兼容或高速通信；未经识别的研究网不能直接用于真实电源/USB/OLED。 |
| **P1-3 实物验收合同** | **软件合同可执行，批准输入仍缺。** G3 EP5 同候选绑定、G4 功能×动作×供电覆盖、G5 原始逐样本/动作窗口重算、来源/校准/预登记和 unknown/fail 保留门控已实现并在 S4 的完整 36/1,654 中通过。另已从 exact S4 新生成四份原字节空模板，121 源/13 native 输入绑定核对，G3 结构通过而未实物评估，G4/G5 原 CLI 为 unknown、0 新实测。C2 历史模板不改标。[S4-empty] [C2-G3] [C2-G45] | 试验 / 计量；机构与电气负责人；质量 / 独立资格审核。 | 逐项批准受控阈值来源、测点、仪器误差、采样与时基、样件/批次和计划；明确 force、travel/skew、FPC 拉力/半径/阻值、电气/热/功能、寿命/环境/工艺类别各由谁提供。 | 不补任意数值。阈值及适用条件先于试验冻结；missing/unknown 保留 unknown、观测失败保留 fail。输入 hash 改变时重新冻结候选和计划，不能把旧 C2 模板改写成当前实测或当前通过。 |
| **P2 G3→G4→G5** | **执行链和导入门控已就绪，真实物理执行为 0。** 本轮没有制造、带电产品验收或寿命结果；已实现代码合同不算实物通过。[C2-G3] [C2-G45] [现场交接单] | 现场装配 / 实验；电气与机构；质量 / 独立见证。 | 物理输入、制造/试验前置和批准计划齐全后，按同候选同样件执行 G3，再凭真实 pass 执行 G4，再凭同候选 G3/G4 pass 执行 G5；每一步先登记原件与样件身份。 | G3 无电装配/完整动作/导通；G4 原系统两供电模式、17 阶段、9 功能覆盖；G5 原始逐样本暴露和动作窗口可独立重算，寿命/工艺阈值均有来源。缺原始数据或只有摘要继续 unknown；提前失效、维修换件、缺测与停机都保留，不推定物理合格。 |

## 三、hosted 实际结果与资源诊断

| 执行 | 已核实事实 | 下一步 |
| --- | --- | --- |
| C2 Research `40193410938` / attempt 1 | 36 unit jobs、plan 和 aggregate 成功；aggregate 为 1,641。独立 CodeQL Actions/Python 执行成功。保留的观察时点为 16 个 native jobs 无 runner/步骤；没有推断其账户原因。[HOSTED-C2-review] | 以新的实际 API/原件更新后续状态；不能把该 snapshot 或 CodeQL execution success 外推为整个 pipeline 通过或零安全发现。 |
| D1 `94f0bdadec7bdad843693846bb44a305ea3c7d0c` / run `40200106104` / attempt 1 | 四个实际 jobs 在 uv 查找 Python 3.12.14 时 exit 2；六 label matrix 为一个未展开的 skipped 条目。**43 包检查、CAD preflight、两份 canonical、六 label、ORTHOGONAL 和 strict resume 均未执行。** 四 ZIP、完整日志/API与独立复核已封存。[D1-evidence] | 修复安装编排并确认原资源接口后，启动独立新 run；保留 D1 原件。D1 artifact 中默认写出的环境 exit=0 因报告缺失不能作为通过。 |
| D1 资源接口观察 | 四份 install receipt 的 root cgroup `memory.stat/current/max` 不可用；据原 C2 supervisor 源码分析，直接在同样接口下运行会失败。这是静态后续兼容性判断，**不是 D1 已执行的 native 资源失败**。[D1-evidence] | 先读取真实 runner 的 proc/cgroup/磁盘条件，再决定 native 执行环境。 |
| D2 `db8ce6b1a9ea3ca0608903c8126e5a24789e4d74` / run `40201283904` | 两种 runner 均已实际执行只读采集和上传，最后控制接口门控均失败。slim 为 cgroup v1 布局；22.04 为 cgroup2，根目录有 memory.stat 而无 memory.current/max。两个 ZIP 的 18 个内容成员已独立核 hash；C2/原监督器/依赖/CAD/owned nonce 均未执行。22.04 的 finite 公式快照为 472,091,584 B，不是 native 通过。[D2-evidence] | 后继 D3b 已实际证明当前服务子组的只读私有挂载兼容性；该计量范围小于 VM root，须如实保留环境变化。D2 对 v4 的更严格观测门控 false，不代表原 v4 resources() 实际执行并拒绝：原函数对缺 current 可退化为 0。 |
| D3 `05589769…` / run `40202776045` | workflow 在任何 job 前失败，jobs=0、check-runs=0，未运行 probe。静态发现 job-level env 使用不支持的 runner context；未获得 provider annotation 原文。[D3-D3b-evidence] | 原件与原静态检查都保留，后继只修路径初始化。 |
| D3b `7fae0a27…` / run `40202923069` | 原 C2 supervisor 实际运行 5.0096 s，6 个资源样本、5 个正 RSS 样本；原 v4 resources() 实际执行。真实 service counter inode、UID、namespace 和 host mount/limits 均已独立复核。[D3-D3b-evidence] | D4 在每个 job 重做门控，并先验证长时进程的中断清理。这个短探针没有执行 43 包、CAD、finite nonce、六 label 或 resume；实际计量范围为服务子树，不能称为未改变全 VM root 计量。 |
| 官方 Python pin 修复 | 原 uv 0.10.10 成功离线解析官方 SHA 固定的 Python 3.12.14 单条下载记录，未升级 uv 或改 Python patch。[PYTHON-pin] | 后续原生 job 仍须实际下载/安装 Python、同步原锁并验证 43 包；解析成功本身不等于安装成功。 |

D1 原 full harness 设计为两份新鲜基线、六个原 v4 label、一次原六 bundle resume，另有一个独立 ORTHOGONAL，共计划十个 jobs。D1 实际只形成四个失败 job 和一个未展开 matrix 条目，不能写成十个任务都运行过。源 C2、原五个 v4 文件及原研究门槛保持不变。原 per-label 1,200 秒预算与 hosted 额外外层时限分别记录。后续使用全 workflow 新 run/attempt，避免缺失基线时混用不同 attempt 的原件。[HOSTED-plan]

### 后续实际补齐与当前新执行

| 执行 | 实际状态与范围 |
| --- | --- |
| D4 / `40204613951` | 10 jobs完整；同C2两基线、原v4六组、严格六bundle恢复以及一个finite ORTH均有原件。四组clear、两组STOW各四真阳性；全部profile拒绝和原flag保留。[D4-complete] |
| N1 / `40206010654` | 原K/C/RHS重建闭合，LUSUP在jcol234701扩容失败；0solve/0residual。完整201,582,664B ZIP与锁源码诊断已保存。[N1-evidence] |
| N2 / `40207901134` | MMD列排序对照在jcol312868扩容失败；0solve/0residual。完整201,585,678B ZIP已保存；AS容量对照依据与未证因果边界分别保留。[N2-evidence] |
| D5 / `40208304041` | exact S3 完整36/1654实际执行：1653通过、1生成入口同步失败、0error/skip。两个v2有限点各11781 fresh clear，none对照四阳性；整体failure。[D5-run] |
| N3 / `40209098454` | AS8GiB对照由原180s守卫在181.076s终止；5RHS已存，0分解完成回执/0solve/0residual；完整201,592,456B ZIP保留。[N3-run] |
| L1 / `40210275856` | E17和O72两组共89次原调用逐值完全复现；真实材料与trace完整，原17方法未决和72保守未决未改判为clear。[L1-run] |
| D6 / `40210734348` | **已完成。** exact S4 36 套 / 1,654 项全过；三组 native 35,343 fresh pair、70,686 journal，两 v2 clear / none 四阳性；双读者核原件后候选已推进。[D6-unit] [D6-geometry] [S4-advance] |

## 四、下一轮 1–3 个工作日：依赖式工作安排

下表是资料和计算资源到位后的 1–3 个工作日工程安排。真实器件采购、供应商资料、制造和寿命试验的工期，按对应受控合同另行排期；当前尚无可据以给出完成日期的输入。

| 窗口 | 工作与责任角色 | 依赖 / 停止条件 | 可验收交付 |
| --- | --- | --- | --- |
| **第 1 工作日：依据本轮实际结果冻结下一域** | 从已验证 S4 与已封存 D6 原件启动下一修复；机构把正 q 的真实 STOP/SPRING 分段及逐侧独立槽域写成受控域清单；CAD 先核中途panel/KEY整件见证并拟结构修复，再按定向材料修方法错误；现场采同 specimen。 | D4 环境适配和全部原件已有；新域必须由真实 factory/机构支持。不得用软件截域替代实体止挡，也不把 v2 有限点当完整运动。 | 当前候选资格与适用域表、SLIDE每项因果和修复diff、10/7/12原件取得状态及职责落实。 |
| **第 1–2 工作日：完成有依据的修复与输入绑定** | 机构检验 v2 剩余材料、真实接触及公差；CAD针对已取得的原异常/正负体积证据做最小修复与反例；数值按容量对照实际结果决定响应/frame资源合同；结构/电气将材料、载荷、pinmap、叠层逐项对源。 | 保留原门槛；需要新算法/几何时另冻源码和假设。资料不足继续unknown；容量对照失败后不按固定增量盲试。 | 原件支撑的修复diff、完整材料/独立读回、真实源数据及受控资源合同；逐项已解决/未决/真实失败清单。 |
| **第 2–3 工作日：有条件进入验证** | 对已冻结的新功能候选运行必要的源码和对应原生域验证；实物和受控资料如果已经到位，现场完成同 specimen 的身份/尺寸/端子/原机基线导入，工程据此冻结实际结构/互连及试验计划。 | 原五探针未全过不进入完整 H/restore；KEY/SLIDE/SEATING 及柔性完整域不足则 G2 不通过。实体、材料、阈值或校准来源不足，G3/G4/G5 不设名义通过日期。 | 每条线的原始 pass/fail/unknown 回执及适用范围；新旧候选证据兼容性表；物理准入所需输入与下一触发条件。寿命试验持续时间由受控目标决定，不按此三天窗口假定。 |

### 必须保留的先后关系

1. **软件身份先于运行资格。** C2通过原件留存于E1/E2及D4；S3是十文件新功能源，D5保留唯一生成入口失败；S4仅生成三行同步，D6实际检出S4完成36/1,654全过与三组有限几何，候选已推进。N1/N2/N3是各有身份的数值策略/资源对照；后继证据台账不冒充任何一次被测源，旧回执不换SHA。
2. **当前运动域与旧数值恢复并行，但不能互相替代。** 原 panel/frame 的 operator probe/H/restore 与当前 EP5 真实结构是不同资格对象。
3. **真实器件与 OLED/FPC 同时约束机械和电气。** 未冻结身份、完整层叠、端子和动态条件时，结构/互连不能以研究占位件当最终产品。
4. **G3 → G4 → G5 必须逐级引用同候选同样件的真实 pass。** 工艺/硬件改动、维修换件、阈值来源或采样合同变化必须按来源和计划重新判断证据适用性，不能“沿用通过”。[C2-G3] [C2-G45]

## 五、已发布证据与新增原件索引

E2 中以下 repository paths 都位于 `engineering/engineering-integration-20261025/` 下；包 SHA 来自已留存的原始打包回执。E2 发布成功及索引已核对，本稿没有重算几何，也不声称重新下载全部远端包验证了一遍。

| 证据 | 固定来源 | 包大小 / SHA256 与范围 |
| --- | --- | --- |
| 软件完整测试 | E1 [unit 原件][E1-unit]；E2 [完成索引][E2-index] | 36 / 1,641 全通过；原 Test ID、source、lock 和日志见包内回执。 |
| 原生 EP5 研究 ECAD / qualification-r2 | E1 [product/execution-bec1c8d7/execution.tar.gz][E1-ecad] | 152,981 B；`83e097de4286a7788c11067ff9b25a76f07de3fd23282cc929a8edad99cb0032`。区分 C1 历史 preflight 与 C2 实际 wrapper。 |
| 21 个继承 wheel 原始字节 | E1 [locked-wheel-payloads 包][E1-wheel] | 317,562 B；`04fb0b1dffec893dcfc4bcd76740feee36e756ec010e85de18efdbeaaa854aa9`。不证明历史安装事件链。 |
| canonical STOW / OPEN | E2 [geometry/evidence/candidate-bec1c8d7/canonical-controls/C2-canonical-STOW-OPEN-bec1c8d7-original-evidence.tar.gz][E2-CONTROLS] | 822,228 B；`d5964689de0d3a6d5be43a17f50009dc1e750358e76745a228958258345c350d`。固定姿态域通过。 |
| SLIDE r3 | E2 [geometry/evidence/candidate-bec1c8d7/slide-r3/execution.tar.gz][E2-SLIDE]；[reader 复现说明][E2-SLIDE-reproduction] | 2,963,473 B；`58bb969095d7f63eea813fee725358f31be9e3aae2031955c8334b285bdeeff1`。11,781 条已留存，10 未决 + 9 求值失败未消除。 |
| SEATING r3 | E2 [geometry/evidence/candidate-bec1c8d7/seating-r3/execution.tar.gz][E2-SEATING] | 1,466,066 B；`5dd9b0eae267ee037045af5c01ce34ec0f8f11cae58f41741048ea40b62d4e9d`。仅声明的 external-pair 域 clear。 |
| finite FULL_BAND 局部退让 | E2 [geometry/evidence/candidate-bec1c8d7/key-relief-full-band/execution.tar.gz][E2-KEY] | 1,020,392 B；`2998bafcbf98adcd78a31f5cc2a40af2897a16f9b3d419fe31af7fe2e5c28477`。两处阳性及独立进程 STEP 体积读回保留，不是原 v4 六项执行。 |
| 原 v4 本地 1/6 与三次资源尝试 | [本地 summary][LOCAL-v4]、[archive receipt][LOCAL-v4-receipt]；同目录 `execution.tar.gz`，**本次后继证据提交纳入，不回写 E2** | 1,479,658 B；`5b51fd75db150bf765284c710186a467a7460714a0823c10b1b21cd63c3f17ab`。唯一完成 native report SHA `0af8bde52576839435e7628234a3f40b42c0c71c16a6c45f42f7a9453a9e3f7f`。其原 postguard 是数据/身份/hash 检查，不是第二次 CAD 重算。 |
| 当前数值与结构输入 | C2 [numerics/SUMMARY.json][C2-num]、[FRAME_SUMMARY.json][C2-frame]、[CURRENT_EP5_INPUT_CONTRACT.json][C2-structure] | 保留 panel 原门槛拒绝、frame 分解资源失败和当前实体未资格；不能从合同存在推定结构通过。 |
| 现场交付 | E2 [product/PHYSICAL_HANDOFF.md][现场交接单] | 同 specimen 身份、10/7/12 原始采集、真实叠层与 G3–G5 来源阈值清单；明确没有本轮真实物理结果。 |

此前本地未完成的五个原 v4 标签，已在 D4 的同一次实际 hosted run 中补齐，并由原严格 resume 验证全部六份完整 bundle；本地失败历史仍保留。STOW 半带/全带的八次真阳性出现没有因执行完成而消失。D4 的 finite ORTH 只有一个点，不能外推全部正交/左右独立/连续域。

旧三种数值策略在 C2 源码冻结前执行，各次源 SHA256 保留；N1/N2/N3 则是后来检出 exact C2、配合各自新冻结 driver 的真实执行。两类身份不混用，失败类型也不拼成五探针残差结果。

## 固定来源链接

[C2-overview]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/README.md
[E1-index]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bf1064b1be153fcd7ca6b96a8465653275518548/engineering/engineering-integration-20261025/COMPLETED_EVIDENCE_INDEX.json
[E1-unit]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bf1064b1be153fcd7ca6b96a8465653275518548/engineering/engineering-integration-20261025/unit-evidence/candidate-bec1c8d7/C2-full-unit-bec1c8d7-original-evidence.tar.gz
[E1-ecad]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bf1064b1be153fcd7ca6b96a8465653275518548/engineering/engineering-integration-20261025/product/execution-bec1c8d7/execution.tar.gz
[E1-wheel]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bf1064b1be153fcd7ca6b96a8465653275518548/engineering/engineering-integration-20261025/environment/locked-wheel-payloads-bec1c8d7/lock-byte-identity.tar.gz
[C2-num]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/numerics/SUMMARY.json
[C2-frame]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/numerics/evidence/frame-rebuild-and-factorization/FRAME_SUMMARY.json
[C2-structure]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/structural/CURRENT_EP5_INPUT_CONTRACT.json
[C2-interfaces]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/design/product_interfaces.json
[C2-route]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/design/product_routing_ep5.json
[C2-oled]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/product/OLED_SOURCE_RECHECK.json
[C2-key]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/geometry/README.md
[C2-G3]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py
[C2-G45]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/integration/product_qualification.py
[现场交接单]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/006222404a1dbecb7df6b35514325f6f075e5d3a/engineering/engineering-integration-20261025/product/PHYSICAL_HANDOFF.md


[E2-index]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/006222404a1dbecb7df6b35514325f6f075e5d3a/engineering/engineering-integration-20261025/COMPLETED_EVIDENCE_INDEX.json
[E2-CONTROLS]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/006222404a1dbecb7df6b35514325f6f075e5d3a/engineering/engineering-integration-20261025/geometry/evidence/candidate-bec1c8d7/canonical-controls/C2-canonical-STOW-OPEN-bec1c8d7-original-evidence.tar.gz
[E2-SLIDE]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/006222404a1dbecb7df6b35514325f6f075e5d3a/engineering/engineering-integration-20261025/geometry/evidence/candidate-bec1c8d7/slide-r3/execution.tar.gz
[E2-SLIDE-reproduction]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/006222404a1dbecb7df6b35514325f6f075e5d3a/engineering/engineering-integration-20261025/geometry/evidence/candidate-bec1c8d7/slide-r3/REPRODUCTION.md
[E2-SEATING]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/006222404a1dbecb7df6b35514325f6f075e5d3a/engineering/engineering-integration-20261025/geometry/evidence/candidate-bec1c8d7/seating-r3/execution.tar.gz
[E2-KEY]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/006222404a1dbecb7df6b35514325f6f075e5d3a/engineering/engineering-integration-20261025/geometry/evidence/candidate-bec1c8d7/key-relief-full-band/execution.tar.gz
[LOCAL-v4]: geometry/evidence/candidate-bec1c8d7/key-v4-local-attempts/SUMMARY.json
[LOCAL-v4-receipt]: geometry/evidence/candidate-bec1c8d7/key-v4-local-attempts/ARCHIVE_RECEIPT.json
[HOSTED-C2-review]: unit-evidence/candidate-bec1c8d7/hosted/INDEPENDENT_REVIEW.json
[HOSTED-plan]: geometry/evidence/candidate-bec1c8d7/key-hosted/harness/C2_KEY_HOSTED.md

[D1-run]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40200106104

[D1-evidence]: geometry/evidence/candidate-bec1c8d7/key-hosted/D1-install-failure/README.md
[D2-run]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40201283904

[D2-evidence]: geometry/evidence/candidate-bec1c8d7/key-hosted/D2-capability/README.md

[D3-D3b-evidence]: geometry/evidence/candidate-bec1c8d7/key-hosted/D3-D3b-compatibility/README.md
[PYTHON-pin]: environment/python-pin-official-catalog/SUMMARY.md

[D4-complete]: geometry/evidence/D4-original-v4-six-bec1c8d7/README.md
[S3-source]: source-S3/S3_SOURCE_PUBLICATION.json
[N1-evidence]: numerics/evidence/panel-N1-hosted/SUMMARY.md
[N2-evidence]: numerics/evidence/panel-N2-hosted/SUMMARY.md
[D5-run]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40208304041

[N3-run]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40209098454
[L1-run]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40210275856
[D6-run]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40210734348

[D6-unit]: unit-evidence/source-dd7def6e/D6-full-unit/OUTCOME.json
[D6-geometry]: geometry/evidence/source-dd7def6e/D6-finite/OUTCOME.json
[S4-advance]: source-followon/S4_CANDIDATE_ADVANCEMENT.json

现场版本边界：既有 `qualification-r2` 和 `PHYSICAL_HANDOFF.md` 保留 C2 历史绑定；本轮已从 exact S4 生成 [四份同版空模板](product/qualification-s4/README.md)，现场使用时仍须核对 `bound_commit == HEAD`；候选变化则重新生成。空模板、结构校验与软件通过均不能补填真实阈值、标签、测量或实物资格。

[S4-empty]: product/qualification-s4/README.md
