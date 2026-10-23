# RAZR-SLIDE 全量开发审计、实际推进结果与下一步 work plan

审计日期：2026-10-23。工作分支：[work/blocker-recovery-20261023](https://github.com/TrillionniumFoundation/RAZR-SLIDE/tree/work/blocker-recovery-20261023)，交付：[PR38](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/38)。最新完整执行的功能源码为 `042b768903cccbd7a0995317c8598401e0318e2a`。

## 1. 当前结论

**当前项目已经具备可重复执行的软件与名义 CAD 研究系统；G0–G5 的总门槛仍未全部闭合。** 本轮已修复影响真实性的代码缺陷、恢复输入与锁环境，并在新功能提交上实际跑完全部单测、EP4/EP5 原生验证、独立读回和三个固定姿态的完整控制域。后续几何与数值计算的通过、拒绝、未完成和未启动分别列账。

`candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 均保持 **false**。新数值矩阵有独立身份；历史报告、当前产品候选和实物验收不能互相代替。

当前台账共 **12 条 blocker**：G0-01 与 G2-01 在各自声明的执行/名义库存范围内闭合；另 **10 条尚未完全闭合**，其中 G0-02 的本地完整执行部分已经完成，hosted 部分仍被阻断。G0–G5 六个总门槛均保持 blocked，没有用局部完成率代表整机开发完成率。

机器可读入口：[SUMMARY.json](SUMMARY.json)、[BLOCKERS.json](BLOCKERS.json)。旧发布状态原文保留于 [history](history/)。本次证据发布不把 `042b7689` 的实际运行改标为后续文档提交的运行。

## 2. 全量审计的范围与分支状态

开工时逐项读取的远端库存为 **40 个 branches、37 个 PR（32 merged、3 open、2 closed without merge）、127 个 workflow runs**，没有独立 issue。40 个分支逐一比较后，35 个已包含在 PR37 基线历史中，5 个保留独立提交。本轮随后创建 PR38，因此这些计数是开工快照，并非声称当前仓库仍只有 37 个 PR。

完整基线 Git 树核对了 **954 个树对象、28,250 个路径条目**。历史约 3.55 GB 大型归档核对了树中 blob 身份，未声称重新读完其全部原始字节。当前执行所需文件按原 Git blob 或冻结 SHA256 取回，最终选定输入清单为 **3,265 个已物化文件、0 个选定缺失、282 项冻结 SHA256**。完整历史 checkout 的验证标志仍为 `false`。

证据：[开工库存](baseline-inventory.json)、[最终选定输入清单](final-unit-input-inventory-20261023.json)、[源码物化范围](source-materialization.json)。

| 工作线 | 审计身份与处理 |
|---|---|
| 已合入 main | `a1b3cc1e0773446f2e36d0a607edf61211dd9919`；保持既有研究主线 |
| PR36 产品集成 | `e25cf001c1b714514d501de4c16d1592fde06b61`；未合并的产品线 |
| PR37 gate closure | `2a8893743c7e90935b1594e619eab9f2ae46b872`；本轮开发基线 |
| PR35 bearing 数值研究 | `176df31ceb35bb3737d68030e60ba377665de210`；独立模型与收敛任务，不能直接资格化 EP5 改动结构 |
| PR38 本轮恢复与修复 | 包含 `e76ff339` 第一功能提交及 `042b7689` 控制域/完整材料预算提交；通过与未通过证据均保留 |
| 其余独立旧候选 | 旧 body-guide/PR17、spatial-contact/PR25、cover-admission、stow-continuous-insertion 等保留原失败或已替代身份，不机械合并进产品候选 |

旧 EP4、旧 PAWL/contact 的拒绝是保留的研究结论；“闭合 blocker”不要求把已废弃候选的真实负例改成通过。

## 3. 本轮实质修复

1. **Donor 身份完整性。** 将 11 个必填字段固定为代码拥有的合同；配置、导入和已绑定读取统一检查。删除未知字段不再能使身份被误判完整。真实未知值保持未知。
2. **原始 CAD 结果与汇总一致性。** EP5 producer、wrapper 和独立 reader 从全部逐对 Common、containment 和 endpoint-cage 原始数值导出结论；矛盾顶层成功标志不能覆盖真实拒绝。
3. **一整个材料体使用一个容差预算。** 对同一完整零件与同一障碍，pin、余体和包络分区的非负交集体积相加，只使用一个 `1e-7 mm³` 预算。真实 CAD 回归确认，两块分别约 `9e-8 mm³` 的交叠不会再漏掉合计约 `1.8e-7 mm³` 的穿透。不同物理对、不同姿态和依次发生的路径段不混合求和。
4. **缓存绑定实际材料体。** 包络缓存同时绑定 native 对象、拓扑和位置；相同 caller label 不能让环体的清除证据复用于实心体。
5. **控制变量作用于真实零件。** 左右 flank、KEY/crosshead offset 和 telescope allocation 都有独立入口；槽约束、捕获范围、关节固定和与有限 contact profile 明确检查。错误端点分支不通过截断坐标掩盖。
6. **完整 pair 与实际源码核验。** 三个固定姿态的扩展控制域覆盖全部参与件及唯一无序对；独立 stdlib 后置检查器会拒绝“行数正确、材料对重复”的伪完整报告。producer/readers 在结束后重新核对实际执行 helper 与源码闭包。
7. **锁环境与 CI。** 真实安装并核验全部 43 个锁定包；完整 36-suite manifest、分片唯一覆盖、实际 test IDs、SHA/run/attempt、源码前后身份都进入严格聚合。required native jobs 保留，work 分支和 stacked PR 触发已接通。

新增控制/判据、legacy、独立后置检查的 focused 回归分别为 **27、12、13 项**。这些不是独立相加的“额外通过数”；它们已经包含在后面的 1,558 项完整执行中。scratch 后续诊断的小测试保留独立计数。

## 4. 实际完成的验证

### 4.1 新功能源码 `042b7689`

| 执行范围 | 实际结果 | 证据 |
|---|---|---|
| 全部当前单测 | **1,558 / 1,558 tests，36 / 36 suites**；0 failure/error/skip/expected-failure/unexpected-success；874.434 秒 | [完整汇总](full-unit-042b7689/summary.json)、[82 成员原始回执包](full-unit-042b7689/results.tar.gz) |
| EP4 原生与独立读回 | 7 regression groups 完成；15,886 pair rows，**55 个真实拒绝保留**；99.850 秒 | [汇总](native-042b7689/ep4/summary.json)、[142 成员原件包](native-042b7689/ep4/results.tar.xz) |
| EP5 local/full 与独立读回 | local 3,105 pairs；full **154/154/161 实体、36,442 pairs、123 containments**，raw Common 最大值为 0，独立 readers 无失败；134.417 秒 | [汇总](native-042b7689/ep5/summary.json)、[30 成员原件包](native-042b7689/ep5/results.tar.xz) |
| 三个固定姿态的完整连续控制域 | **36,442 个 pair domains 全 clear**，0 evaluation errors、0 collision witnesses；871.798 秒 | [汇总](canonical-controls-042b7689/SUMMARY.json)、[36 成员回执包](canonical-controls-042b7689/results.tar.gz) |

全部执行绑定原功能提交、实际所需输入与锁环境，前后源码身份一致。EP4 的 55 个拒绝分布为 A-local 1、PREDOCK 12、OPEN 25、STOW 17。EP5 的 containment 使用乐观 outer union，不能当成实测内腔通道或公差验收。

### 4.2 三个固定姿态的域到底覆盖什么

| 姿态 | 全材料 pairs | TAB 域 | flank 域 | telescope 域 |
|---|---:|---|---|---|
| STOW | 11,781 | 左右独立 `[0,3] mm` | 左右各 `[-1,1]` | 每侧 `0.1≤ji≤2.9`，三关节和 8.5 mm，完整三顶点凸域，左右独立 |
| PREDOCK | 11,781 | 两侧释放于 3 mm | 左右各 `[-1,1]` | 同上 |
| OPEN | 12,880 | 两侧释放于 3 mm | 左右各 `[-1,1]` | 每侧唯一 `(0.1,0.1,0.1) mm`；七个附件全包含 |

以上均固定 KEY/crosshead offset 为零。每姿态 900 个执行源身份与 43 个锁包核验通过，三个独立后置检查都实际执行。各姿态是在原资源守卫允许时分开完成，早先 cache/资源拒绝保留，并非将失败尝试拼成一次没有中断的单次运行。

几何方法仍使用同一浮点 CAD kernel，没有形式化定向舍入证书；某些正 axis gap 仅约 `1.11e-16 mm`，只能作为该计算方法的分离结果，不能宣称稳健制造余量。

### 4.3 原 native workflow 的完整执行

原 **10 / 10 jobs、37 / 37 commands** 已在 `e76ff339` 上完成，669 个原始输出逐 SHA256 验证，最长 lateral-guide 1,642.107 秒，小于原 1,800 秒 cap。任务包括 thin、mounted、coupling、pawl、serviceable、endpoint-joint、catalogue-joint、root-clearance、phone-layout、lateral-guide。

这些回执继续属于 e76。新材料预算判据对保留原始字节重聚合了 **17,726 个 region/material groups**，原 clear 组的和全部为零；另五份 legacy 报告的 20 个完整材料组也全为零。该重聚合不声称在 042 上重跑了原十个 CAD 作业。

证据：[原十任务完整索引](native-matrix-e76ff339/EVIDENCE_INDEX.json)、[严格审计](native-matrix-e76ff339/native-matrix-final-audit.json)。

## 5. 继续推进全程几何的实际结果

### 5.1 附件的完整声明路径已经实际通过

独立附件诊断在 56.769 秒内完成七个安装阶段、**1,099 个连续材料/障碍 pair domains**：1,082 个由正 axis gap 清除，17 个由完整平移包络求交清除，所有 Common 上界为零，0 evaluation errors、0 positive witnesses。正向安装和反向拆除共 14 个方向，几何集合只有七个，没有将同一路径重复计数。

范围为 OPEN 的全部 161 实体，逐步增加七个附件；TAB=3 mm、左右 flank 独立 `[-1,1]`、telescope=`(0.1,0.1,0.1)`，KEY/crosshead offsets 为零。完整 raw/source/lock 后置检查和独立原始数据复核已完成。此结果没有证明手/工具访问、螺纹驱动、预载和实物可装配性。[附件汇总与独立复核](geometry-followon-042b7689/accessory/SUMMARY.json)。

### 5.2 KEY 端点已保存的正交集得到真实读回，完整域仍未闭合

最初 KEY native v1 在 312.181 秒被原共享内存守卫停止。stdout 报告前两个有限试验完成，共 6,792 个 changed pair rows，其中 `STOW_OUTSIDE_HALF_BAND` 有四个 positive；完整逐对原始 JSON 没有写出，不能把这些 stdout 行转成完整 trial 资格。六个预定有限试验总共要求 20,880 个 changed pair rows，尚未完成。[原中断回执](geometry-followon-042b7689/key-stopped-v1/FAILED_PARTIAL_SUMMARY.json)。

第一次仅四个 STEP 的小读取因资源预检拒绝，没有 worker。后来 SEATING 预检独立记录到内存窗口改善，使用完全相同的冻结源码与原 90 秒/768 MiB/共享 6.8 GiB/磁盘 100 MiB 限制，第二次读取在 **2.352 秒**实际完成。四个原文件 SHA 不变、形状有效，无非 solid 顶层叶节点；完整 solid 数为 1、2、1、2，完整体积如下：

| 原保存交集 | 完整体积 mm³ |
|---|---:|
| positive-01 | 0.0012382062639602538 |
| positive-02 | 0.0016509416852802346 |
| positive-03 | 0.0012382062639599693 |
| positive-04 | 0.0016509416852800477 |

四个值都高于原 `1e-7 mm³`。读回仅核验保存交集，没有重算原 Common、恢复缺失 pair ID 或补回完整 trial，也没有换用独立 CAD 内核。短运行的外部 RSS 字段为零只代表未取得非零采样，不能当成零内存峰值。[实际读回](geometry-followon-042b7689/key-v4-readback-algebra/readback-attempt2.json)、[独立复核](geometry-followon-042b7689/key-v4-readback-algebra/readback-attempt2-independent-review.json)。

新的 v4 诊断器已完成 **50/50 纯回归**及独立审查。它在 STEP 输出前先保存正值的实际 pair 身份和数值，按阶段/错误/每 128 对保存检查点；只有来源、基线、全部 raw pairs 与 STEP 都完整的 trial 才可恢复。旧 stdout-only trial 不可复用。v4 native 尚未运行；原每 trial 1,200 秒、有效内存余量 2 GiB/256 MiB 磁盘启动和共享 6.8 GiB/100 MiB 运行限制均保留。

另有 **11/11 纯代数回归**和独立研究，直接读取原 STEP 的有限面与完整 LINE 边界：左右 KEY 前缘与 CAP_0/ROOT_INNER 合计六个相对面片的名义间距为 **0.02 mm**。面片面积与旧交集位置/体积支持具体候选解释，但不恢复原 pair ID。原耦合约束 `|dx|≤0.0252814320`、`|dx−dq|≤0.0353553391` 全部保留，负向范围 `[-0.0606367711,0]` 分成 `[-0.0606367711,-0.02]` 与 `[-0.02,0]`，两段都未删除。有限 floor 的切点可支持研究性的负向平台延拓；完整 pin 的半径和轴向材料仍需整件布尔验证。原生产 profile 保持不变，没有用坐标 clamp 消除反例，也没有将 0.02 mm 面距升级为已证明的全局第一硬止挡。[端点研究](geometry-followon-042b7689/key-v4-readback-algebra/ENDPOINT_RESEARCH.md)、[42 成员完整交付](geometry-followon-042b7689/key-v4-readback-algebra/results.tar.gz)。

### 5.3 SLIDE 已实际启动，但被原内存守卫中断

冻结 v2 准备的 **27/27 纯测试**和独立源码检查通过，覆盖完整 154 材料与 11,781 唯一无序对；域为 q∈[0,12]、slide∈[0,79.75] mm 且 `s=(79.75/12)q`、descent=0、TAB=3 mm、独立 flank 与 telescope allocation，KEY/crosshead offsets 为零。完整 STOP、四个增长弹簧、有限 FPC/OLED 均保留。q 与 slide 联动，不是独立二维域；所选 lower-restoring-force 接触分支的反程采用相同准静态材料集合，尚未证明动态回锁。首次启动因内存预算拒绝，原回执保留。[原准备与首轮未启动](geometry-followon-042b7689/slide-prepared-v2/SUMMARY.json)。

资源窗口改善后，第二次使用原源码与预算真正启动。**五个实际工厂场景的运动规律探针完成**；原监督器于 **388.385801 秒**记录共享不可回收内存 7,330,016,656 bytes，超过原 7,301,444,403-byte（6.8 GiB）上限，随后终止并回收 worker（exit -15）。最后保存的 11,781 行均为 `not_evaluated`，**可恢复的已完成配对数量为 0**；128 对刷盘点之前是否已有部分计算在内存完成无法恢复。不能把库存行数或五个工厂探针算成完整路径配对通过。

该次外部 controller 的 worker RSS 采样均为空；构造阶段 worker 自报峰值约 589 MB，不能外推后续峰值。可以确认实际触发的是共享内存守卫，不能声称 worker 的 1,536 MiB 峰值已得到外部实时验证。只读成本检查确定，最前 128 对是 A_BACK_PANEL 与非柔性材料，保守重叠可触发有限的 profile 分段/两级细分和重复扫掠构造；没有证据确定具体耗时 pair、认为运算挂死，或把该阶段归因于 FPC/OLED cage。

原第二次运行的完整回执、冻结 v2 源码和独立读回位于 [实际中断汇总](geometry-followon-042b7689/slide-v2-attempt2-stopped/SUMMARY.json)及 [20 成员原始包](geometry-followon-042b7689/slide-v2-attempt2-stopped/results.tar.gz)；[只读成本复核](geometry-followon-042b7689/slide-v2-attempt2-stopped/readonly-cost-review.json)另列其推断边界。

针对这次暴露的具体缺口，已冻结独立 **r3** 后续版本。它修复了 Popen 后首个回执写入异常可能绕过清理的问题，并加入逐对 `start` / `completion` 持久日志。日志绑定原 run、源码、控制域、pair 顺序与 hash 链；残缺前缀可显示最后完成和当时正在计算的 pair，但不是 native resume 或完整资格。最终验收仍要求完整 raw report、完整日志、原子索引和原独立几何 reader；读回后的报告/index 变化不能通过重新建立 hash 基线被吸收。每对记录保存原始求值，总体耗时与资源由监督器记录，没有宣称实现逐对计时。

PID 命名空间诊断确认当前 Popen PID 与 procfs 可见 PID 不同。新共享监控器在 CAD 前使用专用 nonce 管道握手，核对父子身份、NSpid、starttime、namespace 与来源，再取得正 RSS/HWM 并放行；存活 child 的身份或 RSS 不可读会停止并回收。**同一最终 helper 字节**另用恰好一个真实 stdlib child 完成 **0.230 秒**验证，外部读到约 **13.83 MB** RSS，退出码 0、进程已回收、专用 FD 全部关闭。该测试没有执行 CAD，也不追认旧 v2 的空 RSS 采样。[原映射探针](geometry-followon-042b7689/owned-child-procfs-probes/successful-probe.json)、[最终 helper 实际 smoke](geometry-followon-042b7689/owned-process-helper-smoke/result.json)。

r3 最终 **65/65 纯准备回归**通过，6.770 秒，17 份源码、900 项仓库执行源身份与 43 个锁包前后匹配。第一次联合小测试在额外 512 MiB AS 限制下有一个 `MemoryError`；原失败、日志和执行副本保留。只对外部测试 harness 显式设置 BLAS 单线程后，在相同 AS 限制下完成上述 65 项，原 native 几何和资源预算没有变化。[r3 汇总](geometry-followon-042b7689/slide-prepared-r3/SUMMARY.json)、[复现入口](geometry-followon-042b7689/slide-prepared-r3/README.md)、[74 成员冻结交付](geometry-followon-042b7689/slide-prepared-r3/results.tar.gz)。

**r3 尚未执行 supervisor preflight 或 native。** 它修复执行监督与证据持久化，不改变 v2 的实际中断结果，也不关闭连续 SLIDE 几何域。

### 5.4 SEATING 保留两次启动拒绝，后续入口同步修复监控

原 r2 **25/25 纯测试**通过。共享 descent∈[0,8.2] mm 的精确有理多面体保留 28 个生成点；左右 telescope 均满足各关节 [0.1,2.9]、三关节和 `8.5−d`，两个侧面使用同一个 d。完整 154 材料/11,781 对、有限 FPC 完整多边形与 taper、OLED 完整区域都在域内；小测试不是 native 几何运行。

逐对 JSONL 记录绑定实际来源、域、run、序号和前一条 hash。完整验收还必须具备完整 raw JSON、最终 journal commit、原子索引和独立 source/input/lock/geometric postguard；残缺前缀不等于可恢复的 native trial。独立复核实际发现的错误 base controls、Boolean 假零、物理标志与不完整 payload 等 reader 反例已被 r2 拒绝；旧 v1/v2 执行副本保持历史身份。[当前准备与复现布局](geometry-followon-042b7689/seating-prepared-r2/README.md)、[74 成员原始包](geometry-followon-042b7689/seating-prepared-r2/results.tar.gz)。

第一轮 `--preflight-only` 普通磁盘 267,284,480 bytes，低于原 400 MiB，内存条件当时满足。随后只回收已持久保存并完整验证的 frame 本地缓存，新的 native 请求使磁盘达到 481,591,296 bytes；但这时共享不可回收内存 6,417,796,352 bytes 加原 1,536 MiB 增量，已超过原 6.8 GiB 上限，第二次仍在启动前拒绝。**两次均没有 worker、没有 native pair 结果。** 没有降低任何预算，也没有循环等待重试。[第二轮实际启动拒绝](geometry-followon-042b7689/seating-attempt2/SUMMARY.json)。

随后发现 r2 使用了相同的 namespace PID 直接读取 procfs 的方式，故它的 worker RSS 监控也有空采样风险。已保留 r2 及两次拒绝的原身份，并单独准备 **SEATING r3**：使用与 SLIDE r3 完全相同的共享监控器，先核验实际子进程和原资源限制再释放 CAD；启动、首次写回、运行时遥测或中断异常都清理自己的 child 和管道。原几何、Budget、run_native、材料包络与 raw 资格合同保持原样，七个核心文件与 r2 逐字一致。

SEATING r3 的 **50/50 纯回归**通过，6.094 秒、峰值 RSS 48,812 KiB，13 份源码与 43 个锁包前后一致，并完成独立接线复核。50 项由原 25 项、共享监控器 17 项与 SEATING 生命周期 8 项组成；SLIDE 的 65 项也包含同一套共享 17 项，不能把两次执行相加为 115 个独立新增测试。**r3 同样尚无 supervisor preflight 或 native 执行**，后续需要监控 worker RSS 的尝试应使用其独立冻结入口。[r3 汇总](geometry-followon-042b7689/seating-prepared-r3/SUMMARY.json)、[源布局与精确命令](geometry-followon-042b7689/seating-prepared-r3/README.md)、[50 成员完整交付](geometry-followon-042b7689/seating-prepared-r3/results.tar.gz)。

这些 scratch 诊断测试的各自计数单独保留，均不增加仓库 **1,558 项**完整单测的 canonical 计数。


剩余 G2 的关键区别是：固定姿态控制域、零偏移的连续滑移/座合、附件路径、非零 clearance 联动、物理可实现的控制路径、零件本身全域有效性及实测公差，分别需要对应证据。完整材料的保守包络相交保留为 unresolved；有限 clear 样点不能覆盖它。实际正 Common 必须从对应真实输入与材料再现。

## 6. 原数值恢复：完整 K 已重建，响应资格仍须逐门通过

PR35 的 11 个仓库输入全部按原身份恢复；11 个原先缺失的外部输入中，8 个恢复原 SHA256 字节。原 K_panel、K_frame、response.npz 字节没有找到，故重建使用独立新身份，原报告不与新矩阵哈希拼接。

| 项目 | panel | frame |
|---|---:|---:|
| 原 tetrahedra | 57,620 | 79,628 |
| 完整 L2 DOF | 344,103 | 474,726 |
| K 非零项 | 23,646,483 | 32,719,176 |
| 装配能量相对核对 | 约 2.27e-14 | 约 1.86e-14 |
| 六刚体模态作用核对 | 约 4.41e-13 | 约 1.56e-13 |

保留原坐标/DOF 映射、E=1/ν=0.3、固定自由度和 P2 trace。能量/刚体检查不等于原五次 inverse-operator probes。两个 K 的新字节身份、装配源、实际命令和原输入均已记录。

原 46+40 个表面 trace 接口已核对唯一父 tet/局部次序；局部凝聚块差异不超过约 `1.03e-14`。显式低内存 Schur adapter 的小规模数学核对通过，但不把小例算作大模型执行。真实稀疏图的 ND 符号填充比已测 panel MMD 更差；frame 独立 L/U 条目约 4.15 亿、基本数组约 4.99 GB，所以没有在资源不足时强行数值分解该方案。

原 archive continuation 确实运行了 **185.210 秒**，完成旧 2,560 列之后剩余 1,325 列，达到 **3,885 / 3,885 列**。MMD 分解耗时约 14.515 秒，L/U 非零项 176,412,608，观测 peak RSS 2,694,688 KiB；逐列真实 free-DOF residual 最大值约 `2.7066562324762344e-9`。

但其后原始五探针 `response()` 在未改动的判据上抛出了 **`ValueError: five-probe full free-DOF residual exceeded`**。判据是残差比非有限，或大于原 `1e-7`。原代码在记录探针编号/残差数值之前退出，因此不能说是哪一个探针、具体超标多少，也不能把逐列较小残差当作五探针已经通过。原 `ExactResponseCache.restore` 尚未到达；它另有 `2e-7` 的 H-action 相对门槛。

已完成的 H 为 120,745,928 bytes，SHA256 `696f3f7efcf5eee381461824e90e5d89ea506e218d197fe30e190b67a4b6f8ae`，现在作为 **未资格化候选隔离保存**。旧 2,560 列前缀、C、ordered points 及原源文件保持原身份。没有将它标成合格 restart，也没有进入原全域 QP。

为继续定位，已另行冻结五探针诊断器：使用同一 K/D/C、float64、MMD_AT_PLUS_A 和原 LU 参数，记录原始五向量的残差分子/分母/比值、有限性、场 SHA 和 H-action；最多四次同 LU 的迭代修正 `u ← u + LU.solve(b − Kff·u)`，不改变两个原门槛。若全部通过，再核验四个原外载场、释放 LU，并实际调用原 restore。十项小规模测试和独立源码复核已经完成，但只证明该诊断实现的小例行为。

唯一实际启动尝试 **未启动 worker**：普通可用磁盘 574,775,296 bytes，低于该独立诊断预先声明的 600 MiB，短 54,370,304 bytes；共享内存加 2.9 GiB 预留也不能满足原 6.8 GiB 守卫。没有 PID、没有分解结果、没有探针数值。原 archive continuation 的 700 MiB 启动预算保持不变；新诊断的 600 MiB 是不复制完整 H 的不同任务范围，并非为通过检查临时削低原预算。

证据：[实际失败独立复核](numerical-recovery/followon-042b7689/panel-actual-failure-independent-review.json)、[隔离清单](numerical-recovery/followon-042b7689/quarantine-manifest.json)、[探针准备](numerical-recovery/followon-042b7689/probe-preparation-report.json)、[实际未启动回执](numerical-recovery/followon-042b7689/probe-attempt-1-summary.json)、[完整 75 成员源码/日志/回执包](numerical-recovery/followon-042b7689/results.tar.gz)。包内不含 K/H/C 大型数值载荷。

原有限点 QP 的通过不能代替全域接触证据。保留的研究报告还有 75 个 body regions 与 1,112 个 bearing regions 未满足全域 gap 审计；原 `2e-10` QP、`1e-7` gap、每轮至多 128 个新点以及 5,255 body + 1,196 bearing 域均未放宽。当前 EP5 对壳体、KEY 和 A web 的改动仍需自己的结构模型与真实载荷/支承/预载输入。

## 7. Hosted CI 的当前结论

新功能提交的 [run 39917795794](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39917795794) 已结束：**19 个 job records，18 failure、1 skipped；0 steps、0 assigned runners、0 artifacts**。ubuntu-slim、ubuntu-24.04 及三个新增控制域作业都未真正开始执行。四个 pinned action commits 均可解析。

目前可读接口只提供 failed checks 的 annotation 数量，title/summary/text 为空；直接 annotation 正文接口不可用。因此本次启动失败原因是**未知**，没有把历史 billing 注释套用为当前原因，也没有更改账户设置或反复请求 rerun。

管理员最小交接包含本次 run/attempt/commit 与两类 runner 的 check IDs：slim plan `120296206407`、EP5 ubuntu-24.04 `120296206120`。真实闭合出口是取得本次原始 annotation、解决实际启动原因，并获得 runner steps、完整严格单位聚合和 required native artifacts。[当前观察](ci-042b7689/SUMMARY.json)、[管理员交接](ci-042b7689/hosted-admin-handoff.md)。

## 8. 无法从软件计算补造的实物输入

现有 donor 只观察到型号 `XT2551-3`。以下 **10 个身份字段**仍需同一实物与原始标签/记录绑定：region、mainboard_revision、runtime_panel_id、display_module_part、display_module_revision、touch_revision、pack_A_label、pack_B_label、USB_roles、USB_version_rate。

七类原件为 COF、USB_port_board、display、mainboard、pack_A、pack_B、touch。十二个端子接口为 MAIN_DISPLAY、MAIN_TOUCH、A_PROTECTED_PACK、B_PROTECTED_PACK、A_CHARGE、B_CHARGE、USB_DATA_CROSS、USB_POWER、CAMERAS、RF_ANTENNA、AUDIO_SENSORS、MOTION_STATE。它们的绑定、供电/保护链和版本未用推测值补齐。

OLED/COF/FPC 实际叠层、动态弯扭限制、导体/阻抗/疲劳资料、电池成包膨胀与极耳、紧固/连接、材料、摩擦、保持/释放/回锁力、公差与工具空间仍须原始实测或受控供应资料。EP5 的 188 mm 总长、164 mm 自由段、10.8 mm 中段宽度与双 U 路线属于候选设计参数。

产品约束保留等尺寸 A/B 成品舱、约 7 英寸单主屏、无背屏、屏幕平铺存入 B、滑移 79.75 mm、座合 8.2 mm，以及 A 舱大电芯优先。4700 mAh 是未验证目标；旧电芯标签的 3430+1140=4570 mAh、手册典型 4700/rated 4540 mAh 属于不同证据口径，不能替代已选成包容量/能量验收。

来源：[产品接口合同](../../design/product_interfaces.json)、[产品几何](../../design/product_geometry.json)、[EP5 路线](../../design/product_routing_ep5.json)、[物理资格合同](../product-integration-20261018/physical-test-followon-20261019/QUALIFICATION.md)。

目前没有已编号实物整机的完整无电装配试验、运动供电/充电/USB/显示/触控日志或寿命/制造过程验收记录。现有物理证据合同、计划及 as-built 模板可直接用于收集这些记录。

## 9. 下一步 work plan 与闭合出口

以下顺序使用明确依赖和验收出口；没有把尚缺输入的实物工作承诺成日历完成日期。

| 优先级 / blocker | 具体下一步 | 闭合出口 | 所需职责 / 依赖 |
|---|---|---|---|
| P0 / G0-02 hosted | 读取本次 check annotation，修复实际启动条件后执行当前 required workflow | 真实 runner/steps、严格 36-suite 聚合及全部 required native artifacts | 仓库/组织管理员 |
| P0 / G0-NUM | 在满足已声明预算的资源窗口运行冻结五探针诊断，记录全部初值/修正及原 restore；随后完成 frame H、trace 与完整 restart | 原数值门槛、原模型与载荷不变；完整 C/H/ordered points 的真实保存/恢复；失败保留 | 数值负责人、足够独占内存与普通可用磁盘 |
| P0 / G1-01 | 收集同一 donor 标签、标定尺寸、出口/高度边界与端子 | 10 身份、7 原件角色、12 接口完整绑定原证据 | 硬件/集成；真实 donor |
| P0 / G1-02 | 冻结屏/COF/FPC、电池成包、材料、连接、公差和工艺 | 真实版本、动态限制、膨胀/极耳及制造边界可追溯 | 材料/电气/工艺 |
| P1 / G2-02 | 完成下面的连续运动及 KEY 端点待办；正交集分析后以实际几何定义可实现域或约束 | 所有允许状态、完整材料/障碍、正反程连续覆盖；全部 unresolved 有合法证明或修复 | 机械/几何；稳定资源窗口及真实控制约束 |
| P1 / G2-03 | 将实测尺寸/工艺分布带入装配、保持、紧固、工具访问与最小间隙 | 最坏边界满足预声明标准；名义 clear 不代替公差资格 | 机械/工艺；G1 输入 |
| P1 / G5-NUM | 原模型全域接触继续收敛；当前 EP5 另建真实支承/载荷/接头模型 | 原 gap/force/compliance 阈值，独立全场审计与规定的网格/载荷收敛 | 数值/机械；完整响应与真实输入 |
| P2 / G3 | 编号无电实物完整装配与循环 | 标定记录覆盖 skew/release/jam/hold/return/relock | 样机/测试；可实现机械路径和部件 |
| P2 / G4 | 静止和运动中的供电、充电、USB、显示、触控 | 原保护链与连续时间戳原始日志；失败不可删除 | 电气/测试；G3 与端子绑定 |
| P2 / G5 | 结构、寿命、工艺稳定性、检验及追溯 | 受控样本、预声明 load/cycle/process 标准和测量不确定度验收 | 制造/质量；前置门槛与真实试验 |

### 9.1 可以直接接续的计算工作

先把下一次运行安排到满足既有启动预算的资源窗口，按下表串行执行；各包包含冻结源码、实际参数、布局与独立 reader。资源预检失败应保留原回执，不进入 worker，也不缩小材料、控制域或调整验收阈值。

| 次序 | 已准备入口与原预算 | 本次运行必须产出的证据 | 失败后的正确处理 |
|---|---|---|---|
| 1. Panel 五探针定位 | [数值诊断准备](numerical-recovery/followon-042b7689/probe-preparation-report.json)及[75 成员复现包](numerical-recovery/followon-042b7689/results.tar.gz)；600 秒、4.25 GiB AS、共享 6.8 GiB；启动普通磁盘 600 MiB、增量内存约 2.9 GiB | 同一 K/D/C、同一 float64 和分解选项；逐个记录原五个向量的有限性、真实 free-DOF residual、每次同 LU 迭代修正、H action；满足原门槛后才执行原 restore | 保留失败的 probe index/ratio 与场数据；最多四次修正及原停滞规则。无合格响应时不得运行下游 QP 或将完整列数当成合格 |
| 2. KEY 完整配对复现 | [v4 准备及命令](geometry-followon-042b7689/key-v4-readback-algebra/README.md)；每 trial 1,200 秒、有效可用内存余量至少 2 GiB、磁盘 256 MiB；共享 6.8 GiB、运行磁盘 100 MiB | 从 `STOW_OUTSIDE_HALF_BAND` 单个完整 trial 开始，恢复实际 pair ID、Common 数值、双方材料和对应 STEP；之后完成声明的六个试验 | 任何正值先记录实际身份，再输出 STEP。完整 raw/source/STEP 缺一即未完成；明确碰撞位置和物理 stop/clearance 关系，再设计实际几何修复 |
| 3. SLIDE 连续零偏移域 | [本轮独立 r3 准备及命令](geometry-followon-042b7689/slide-prepared-r3/README.md)；原 1,800 秒、worker 1,536 MiB、共享 6.8 GiB、启动磁盘 200 MiB / 运行 100 MiB及 1,536 MiB 增量保留 | 从全新 run 开始；实际 own-child RSS 与稳定进程身份；每对 start/completion 与原始求值记录持久保存，并记录总体耗时/资源观察；完整 154 材料、11,781 唯一对的原域、完整报告及独立后置核验 | 先用实际 pair 日志定位成本与保守 unresolved，再作有对应反例的优化。旧 v2 的五个工厂探针和残缺 pair 库存不能恢复为 native 通过 |
| 4. SEATING 连续零偏移域 | [r3 完整布局及命令](geometry-followon-042b7689/seating-prepared-r3/README.md)；worker 1,740 秒 / 外部 1,800 秒，worker/增量 1,536 MiB，共享 6.8 GiB；启动磁盘 400 MiB / 运行 300 MiB | 共享 descent 的全 28 顶点参数域、完整 154 材料/11,781 对、完整 flex 有限体；逐对持久记录、完整 raw JSON 和原子最终索引，再独立核验 | 保守包络相交保持 unresolved。以同一几何细分或真实碰撞修复解决，不能删除 flex、taper、接头余体或允许状态 |

KEY 的有效余量使用其原 `min(MemAvailable, cgroup_unused + clean_inactive_file_cache)` 计算；SLIDE/SEATING 保留各自不可回收内存估算加增量的预检。各监督器的原估算口径和资源上限分别记录，没有用一种快照替代其他守卫。

这些步骤具有依赖：panel 五探针合格不自动完成 frame H；frame 需要重新取回已验证的归档并校验原 SHA，再完成全部响应、原保存/恢复及全域收敛。KEY 的完整有限端点配对也不代替非零 offset 的连续全路径。零偏移 SLIDE/SEATING 完整运行之后，仍需对物理可实现的 telescope 分配、slot/KEY 联动与回程建立完整控制域，覆盖正反向、回差、保持、释放和回锁。

在全部小型准备回归结束后的 **10:50:44 UTC**，按各冻结监督器实际资源函数做了一次只读观察：普通可用磁盘仅 **181,960,704 bytes**，低于 SLIDE 200 MiB、SEATING 400 MiB、KEY 256 MiB 和数值探针 600 MiB 的各自启动线。SLIDE/SEATING 的内存条件当时已可满足；KEY 有效可用余量为 1,388,417,024 bytes，仍不足 2 GiB；数值探针的内存增量条件也失败。这是资源观察，不是新的 supervisor/native 执行，也不计入旧尝试次数。该观察下没有任何一项同时满足原磁盘与内存条件。[逐函数原始观察](publication-receipts/final042-resource-observation.json)。新增小测试只验证日志、资源监督和读取的可靠性，不产生几何或数值资格。

### 9.2 硬件与管理员可以并行推进

管理员应直接从 [hosted handoff](ci-042b7689/hosted-admin-handoff.md) 中的 run/attempt/check IDs 获取本次原始错误。硬件负责人则按现有 donor、接口与物理资格合同，提交同一编号实物的标签、测量与原始日志；身份、尺寸、材料或端子有缺项，就在对应门槛保留缺项。获取这些输入后，才有依据将名义 CAD 候选更新为受控装配模型、设定实测公差和开展 G3–G5 验收。

## 10. 证据保存与当前权限边界

代码、较小原始回执及完整 CAD/单测证据包随 PR38 交付。所有归档都有 SHA256 与成员读回记录；只有在完整归档、对应成员与副本身份一致后才回收本任务的冗余本地文件。没有删除其他任务数据或放宽资源保护来制造完成。

Frame 的完整 K 归档已保存成功，并重新下载验证了整个归档 SHA256、22 个原成员和附加 manifest。只有完成这些核验后，才回收 394,530,277 bytes 的本地 raw K 冗余副本。后来为解除 SEATING 磁盘门槛，又核对当前保存身份、本地归档完整 SHA 与文件身份，回收这一个下载副本，释放 243,171,328 bytes。**frame raw K 与下载归档目前均未在本地物化**；持久保存原件和明确恢复路线保留，后续 frame 计算必须先重新取回、验证归档。模型与原 K 字节没有改变，panel 归档和两份 H 没有被删除。[原完整成员核验](numerical-recovery/resource-compaction/frame-downloaded-archive-readback.json)、[后续缓存回收及恢复路线](numerical-recovery/resource-compaction/frame-local-downloaded-archive-reclaimed.json)。

Panel 的 `panel-full-L2-rebuild-20261023.tar.xz` 为 **174,121,632 bytes**，SHA256 `96c095334540eaf2aa5ccf918bb2dfb451a7fac343881f4748e794e46aa04364`。**自动审批已拒绝该归档的外部保存操作**：它包含私有仓库的网格、载荷、K 和审计证据，本次具体载荷与外部文件保存目的地尚缺用户明确授权。因此该归档只保留受保护的本地原件，没有改走 GitHub 或其他上传渠道。后续需要用户明确授权这一具体保存动作。

完整但未通过原五探针资格的 120,745,928-byte panel H 同样保留本地隔离状态，未随新的 Git 证据包上传。新的 Git 包只含代码、较小回执、摘要和 CAD 验证原件。[保存状态与边界](numerical-recovery/PERSISTENCE_STATUS.json)。

此审计保留每项已闭合的具体范围以及未闭合条件。工程研究的局部通过不会自动授予整机、制具或制造放行。
