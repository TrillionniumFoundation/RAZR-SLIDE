> **2026-10-26 后继实证已更新：** 本文保留 2026-10-25 时点的历史结果。当前完整 factory、具名 KEY 修复、连续方法、数值与归档结果见 [2026-10-26 执行报告](../engineering-integration-20261026/EXECUTION_REPORT.md)。

# 2026-10-25 全量执行：结果、原始证据与下一步

**唯一候选 S4 已实际完成 36 套、1,654 项锁环境测试，全部通过；同版三组有限 KEY 原生对照也已完成。整机运动、当前结构与实物资格仍未完成。** 当前功能源码为 S4 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`，tree `cdd9e2c41216201b6cd04dd610d45fde80499045`。完整原始回执已经封存，两位读者完成逐项独立核验后，候选 ref 已以 expected-old-SHA 保护实际快进并经 API 回读。真实器件、材料、阈值和物理试验仍按缺失记录。[同版软件结果](unit-evidence/source-dd7def6e/D6-full-unit/OUTCOME.json) · [候选推进回执](source-followon/S4_CANDIDATE_ADVANCEMENT.json)

工作入口：[PR #39](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/39)。当前 PR 保持 draft，`candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 均为 false。

## 1. 候选源码与证据提交

| 身份 | 作用 |
|---|---|
| C2 `bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb` | 历史已验证功能源码；tree `0eb5fb6c13645b6ce6ff9aec765d5465007efc13`；E1/E2、D4、L1、N1/N2/N3 保留该执行身份 |
| E1 `bf1064b1be153fcd7ca6b96a8465653275518548` | C2 后继证据提交，保存完整单元回执、原生 ECAD 与锁包原始载荷比对 |
| E2 `006222404a1dbecb7df6b35514325f6f075e5d3a` | E1 后继证据提交，保存 canonical STOW/OPEN、SLIDE/SEATING、失败的有限 FULL_BAND 退让候选及现场交接单 |
| S3 `20dfddfe8497a73b1814623e6320b3a9ac4273d0` | E2 后继十文件功能修复；原 36 套最低 1,654，资格必须来自本 SHA 的新执行 |
| D4 `3f82204b944b08ec471e33b4f2a492884462aa67` | 实际完成 exact-C2 原 v4 六组、两基线、一个有限 ORTH 与严格恢复的独立执行编排 |
| N1 / N2 / N3 独立 driver 与 workflow | exact-C2 输入上的新数值策略；前两次分解扩容失败，第三次由原 180 s 守卫终止，均 0 solve / 0 residual；不构成当前 EP5 强度资格 |
| **S4 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`** | **唯一当前候选**，固定在 `candidate/engineering-integration-20261025`；S3 后继仅同步三生成入口；D6 实际完成 36/1,654 全过及三组有限几何；tree `cdd9e2c41216201b6cd04dd610d45fde80499045` |
| D6 `16c500ba26f394023b6f3848f00c38faec3f3682` | 四个独立 jobs 均实际完成；执行检出 S4，workflow 身份独立，不能代替功能源码 SHA |
| L1 `8d8f766c3079e537e380017421710776aaf7c8ac` | 在 exact-C2 原方法上观察 19 个问题体对的 89 次原调用，保留真实错误、材料和旧判定 |
| D1 `94f0bdadec7bdad843693846bb44a305ea3c7d0c` | 独立 hosted KEY 诊断 workflow；每个研究 job 检出固定 C2，不把 D1 当作研究源码身份 |
| D2 `db8ce6b1…`、D3 `05589769…`、D3b `7fae0a27…` | 同一独立诊断分支的接口探针与服务子组兼容性尝试；不是新的功能候选，实际执行范围见下文 |
| 本文件所在后继提交 E3 | parent S4；保存实际执行的公开工程摘要、原件哈希、独立复核和更新后的入口。它不是 S4 或 C2 的被测源码身份，也未被改称另一次完整验证 |

统一祖先包含 PR36 → PR37 → PR38、资格修复 `a9aaf481b1e51caa948f824aa4768af1f5b3d57a` 与主线 `92d80fbef80bef4cde8dc7d759399f19fe8ba7ce`。主线删除根 README 的决定被保留；入口位于 `docs/RESEARCH_OVERVIEW.md`、`CURRENT_DESIGN.md`、`status.json`，从同一 `design/current_product.json` 生成。

`current_product` 的 `implementation_baseline.commit`、`product_geometry.base_commit` 与 `product_interfaces.basis_commit` 继续保留三配置共同的历史声明起点 `a1b3cc1e0773446f2e36d0a607edf61211dd9919`，因为原产品合同要求三者相等。它们没有被单独改写成 S4。当前实际被测功能源码明确记录在 `current_verified_functional_source` 与独立候选 ref；历史声明起点、被测源码和后继证据提交具有不同作用。

PR35 `176df31ceb35bb3737d68030e60ba377665de210` 不是 C2 祖先。它与本次重建诊断仍属于独立的归一化 bearing 研究，不构成当前切改后 EP5 壳体的强度资格。[候选谱系](CANDIDATE_IDENTITY.json)

首个候选 C1 `8fa8ae2bae5de8808ad8259e04434bdd18d47541` 的不完整验证原样保留。修复了本地检出遗漏的受控原生输入和 SLIDE worker 同名辅助模块导入顺序后，C2 从头执行全部 36 套；没有把 C1 的部分结果拼成完整通过。[首次失败回执](unit-evidence/first-candidate-aborted/RECEIPT.json)

## 2. 完整软件验证与实际 hosted 状态

**C2 一次完整本地执行：36 套、1,641 次测试全部通过，0 failure / error / skip / xfail / xpass。** 1,641 个 `(suite, test_id)` 全部唯一；裸 test ID 为 1,627 个，差额是已核对的跨历史 suite 同名。43 个锁定包版本与 Python 3.12.14 一致；1,205 个 Python 文件通过 AST 解析；4,788 个实际源码/输入路径、303,644,769 B 在执行前后不变并匹配 C2 Git blob。没有声称把所有历史归档完整检出。[完整回执](unit-evidence/candidate-bec1c8d7/C2-full-unit-bec1c8d7-original-evidence.tar.gz) · [独立逐测试审查](unit-evidence/candidate-bec1c8d7/INDEPENDENT_REVIEW.json)

本地锁环境的 21 个继承包另外做了锁定 wheel 对照：21 个下载文件的大小和 SHA256 匹配锁；1,650 个原始 payload 文件及 86 个原始 metadata 文件逐字节一致。952 个生成的 pyc、installer 元数据、重写 RECORD 和生成入口不在该原始载荷结论内；历史安装事件与进程内实际执行字节也未因此获证。补充 checker 的反例不并入 1,641 次 canonical 测试。[锁包证据](environment/locked-wheel-payloads-bec1c8d7/SUMMARY.md)

GitHub C2 research run `40193410938` 的 36 个 unit jobs、plan 与 aggregate 已实际成功。独立下载的 aggregate 原始 ZIP 与日志记录 `passed=true / tests_run=1641 / expected_suite_count=36 / errors=[]`，各 suite 计数和 manifest/lock 哈希匹配 C2。另一个 CodeQL run `40193407732` 的 Actions、Python 分析成功。观测时 16 个 required native jobs 仍排队、无 runner 和步骤，research 整体不能标为通过；没有推断排队的账户原因。该独立 hosted 审查没有逐一下载 36 个 hosted 原始 shard，本地完整逐测试原件已在上一证据包核验。[hosted 原件与审查](unit-evidence/candidate-bec1c8d7/hosted/INDEPENDENT_REVIEW.json)

### S3 / D5 的真实失败与 S4 修复

[D5 run 40208304041](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40208304041) 在 exact S3 上完整执行了 **36 套、1,654 项**：1,653 pass、1 failure、0 error / skip；35 套通过，product-integration 套保留一条失败。原逐项日志和 JSON 中 1,654 个 `(suite, test_id)` 唯一，裸 ID 1,640 个；新增 13 项均在实际通过的 repository suite 中。6,895 条实际源码/输入路径、1,208 个 AST、43 包和 S3 前后身份全部通过，没有资源截断。

唯一失败为 `test_product_state.ProductStateTests.test_generated_entrypoints_are_current`。其首个比较发现 `docs/RESEARCH_OVERVIEW.md` 仍写 1,641；随后原生成器独立检查发现三个需同步入口：该文档、`CURRENT_DESIGN.md` 与 `status.json`。S4 仅将这三行登记数更新为 1,654；生成器、manifest、事实台账和所有功能/几何源均未变化，原 `--check` 和幂等生成通过。S3 的失败回执不会被修复后的状态覆盖。

**S4 的 [D6 run 40210734348](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40210734348) 已实际完成：36 套、1,654 项全部通过，0 failure / error / skip / xfail / xpass。** 1,654 个 suite-qualified ID 唯一，裸 ID 为 1,640，14 个跨 suite 同名由原测试定义解释；6,895 个实际源码/输入路径在执行前后不变并匹配 S4，1,208 个 AST 通过，13 个新源身份和 43 锁包逐项核对。实际 Python 3.12.14、uv 0.10.10；真实 INT/TERM 及 8 份 namespace cleanup 回执通过。原 verifier exit 0，外层时限未触发。原 ZIP 的 745 成员 / 744 内容 manifest 均通过 SHA256/CRC；原报告 SHA256 为 `b8903d3f12dde048ea30435fb89430b364be63d7cbfe332ad1da5f27cff8bb13`。这是完整新执行，未复用 C2/S3 的软件通过。

独立 workflow 为 `16c500ba26f394023b6f3848f00c38faec3f3682`，四个 jobs 全完成；两位读者分别审核原件后，唯一候选 ref 实际推进至 S4。新公开目录仅包含工程聚合，完整 ZIP、日志和双方完整审阅保留在私有原件包；原软件报告的完整运动、原生 KiCad、硬件与放行 false 标志不变。[S4/D6 逐项工程结果](unit-evidence/source-dd7def6e/D6-full-unit/OUTCOME.json) · [完整原件哈希](unit-evidence/source-dd7def6e/D6-full-unit/ARCHIVE_REFERENCE.json) · [S3 失败独立摘录](unit-evidence/source-20dfddfe/D5-full-unit/INDEPENDENT_REVIEW.json) · [S4 最小修复](source-followon/S4_SOURCE_PUBLICATION.json)

## 3. 原生几何：执行完成与几何通过分别记录

| 执行 | 实际范围与结果 | 结论范围与限制 |
|---|---|---|
| Canonical STOW | 154 体，11,781 个唯一体对全 clear；原 postguard 通过 | 当前 C2 的固定姿态声明域 |
| Canonical OPEN | 161 体，12,880 个唯一体对全 clear；原 postguard 通过 | 当前 C2 的固定姿态声明域；本组没有另一次 PREDOCK canonical 运行 |
| SLIDE r3 | 154 体，11,781 对全部有终态记录；11,762 clear、10 保守包络未决、9 顶层求值失败；原 exit 2 | `complete_native_diagnostic_executed=false`，域 clear=false；未决不等于实际穿透 |
| SEATING r3 | 154 体，11,781 对全 clear；原 fresh-process reader exit 0 | 声明的连续外部体对域通过；整个 SEATING/G2、连续柔性自身有效性仍 false |
| 有限 FULL_BAND 端面退让研究 | 154 体、11,781 对全部重算；2 对 ROOT_INNER 真实阳性；独立 STEP 读回与材料守恒通过 | 局部候选失败；未改变生产默认几何，不是原 v4，不证明连续域或结构强度 |

完整原件分别在 [controls](geometry/evidence/candidate-bec1c8d7/canonical-controls/)、[SLIDE](geometry/evidence/candidate-bec1c8d7/slide-r3/)、[SEATING](geometry/evidence/candidate-bec1c8d7/seating-r3/)、[FULL_BAND](geometry/evidence/candidate-bec1c8d7/key-relief-full-band/)。相应原 supervisor 的墙钟、内存及任务文件系统容量条件均有原始记录；不同任务的容量字段与预算不混用。完整逐对 journal、源身份与资源采样随包保存。

### KEY 原版执行与独立槽顶点

**此前本地原 v4 完成 1/6；后续 D4 已补齐全部六组，以下本地失败历史原样保留。** 原冻结 v4 的五个源文件从受控归档逐字节提取，没有修改算法或原门槛。第一轮因原 2 GiB 启动内存条件不满足，在 0 条命令、0 对计算时停止。第二轮实际完成 `STOW_OUTSIDE_0p001mm`：3,396 个变化体对 fresh 计算，8,385 个固定体对复用同 C2 的有效 STOW 基线；0 positive / 0 error、finite clear，原 postguard 与 reader 通过。`STOW_OUTSIDE_HALF_BAND` 随后启动条件拒绝，其余四项未到达。后续任务在普通用户可用磁盘归零和内存不足时，没有启动新的原生 worker。[本地完整尝试](geometry/evidence/candidate-bec1c8d7/key-v4-local-attempts/SUMMARY.json) · [独立复核](reviews/KEY_V4_LOCAL_REVIEW.json)

原 v4 的强身份绑定是 repo、study、baseline 的绝对路径、源/环境与字节。结果目录可搬移，只要 STEP 的相对 basename 与 SHA 等原合同保持；不能把新增的 hosted 固定结果路径要求误称为原 validator 的限制。[路径补充说明](geometry/evidence/candidate-bec1c8d7/key-v4-local-attempts/PATH_BINDING_ADDENDUM.md)

为补齐执行，保留了以下独立 hosted 尝试：

| 尝试 | 实际观察 | 范围 |
| --- | --- | --- |
| D1 / `40200106104` | 四个实际 jobs 均在旧 uv 查找 Python 3.12.14 时失败；六 label matrix 未展开 | 0 次 43 包检查、0 canonical、0 v4、0 ORTHOGONAL、0 resume。日志中未执行分支默认写出的环境 exit=0 不计通过 |
| D2 / `40201283904` | 两种 runner 均实际运行只读接口探针；slim 为 cgroup v1，22.04 的 cgroup v2 root 缺 current/max，最终控制接口门控失败 | 22.04 可用且服务子组真实存在；finite 公式快照不是 CAD 资格。探针的严格 v4 观测门控不等于原 v4 函数实际拒绝 |
| D3 / `40202776045` | workflow 在任何 job 前失败，jobs/check-runs 均为 0 | 静态发现 job-level env 使用 runner context；未获得 provider annotation 原文。未执行任何 runtime probe |
| D3b / `40202923069` | 修路径初始化后，原 C2 supervisor 真正运行 5.0096 s、6 个资源样本、5 个正 RSS；原 v4 resources() 也实际执行 | 真实 counter inode、原 UID、PID/user/cgroup namespaces、host mount 与 limits 独立核验通过。无 CAD、43 包或 finite nonce 资格 |

D3b 把**真实当前服务子树**只读绑定到私有 mount namespace 中原程序期待的路径，随后降回原 UID；没有伪造计数器或修改限额。其计量范围为 `/system.slice/hosted-compute-agent.service` 及后代，小于 VM root。该外部执行环境适配及其范围变化明确保留，不能写成“环境完全未变”。后续完整 job 必须各自重新通过原门控，短探针不能担保未来容量。[D1 原件](geometry/evidence/candidate-bec1c8d7/key-hosted/D1-install-failure/) · [D2 原件](geometry/evidence/candidate-bec1c8d7/key-hosted/D2-capability/) · [D3/D3b 原件](geometry/evidence/candidate-bec1c8d7/key-hosted/D3-D3b-compatibility/)

Python 下载修复保持 uv 0.10.10 与 Python 3.12.14，通过 SHA 固定的官方单条下载目录补齐旧 uv 的内置记录。旧 uv 的离线解析实际成功；该独立解析探针没有安装 Python，也不等于 43 包或 CAD 通过。各实际 job 的下载、安装、版本和运行结果须读其自身回执。[官方原件与解析证据](environment/python-pin-official-catalog/SUMMARY.md)

### D4：原 v4 六组、基线与严格恢复已实际完成

[D4 run 40204613951](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40204613951) 的 10 个 jobs 全部完成。实际功能源仍为 C2，独立 workflow 为 `3f82204b944b08ec471e33b4f2a492884462aa67`；原五个 v4 源文件与原门槛没有修改。两份新的 canonical 基线分别完成 STOW 的 11,781 对与 OPEN 的 12,880 对，均 clear。原六组结果为：

| 原 v4 标签 | 本次变化体对计算 | 同 C2 固定体对复用 | 真实阳性数 | 有限点结果 |
| --- | ---: | ---: | ---: | --- |
| STOW 0.001 mm | 3,396 | 8,385 | 0 | clear |
| STOW HALF_BAND | 3,396 | 8,385 | 4 | 拒绝 |
| STOW FULL_BAND | 3,396 | 8,385 | 4 | 拒绝 |
| OPEN 0.001 mm | 3,564 | 9,316 | 0 | clear |
| OPEN HALF_BAND | 3,564 | 9,316 | 0 | clear |
| OPEN FULL_BAND | 3,564 | 9,316 | 0 | clear |

六组均为 0 evaluation failure / 0 pending。STOW FULL_BAND 的左右 CAP 交集分别为 `0.004876412527985787 / 0.004876412527985475 mm³`，左右 ROOT_INNER 为 `0.012995443639309764 / 0.012995443639308627 mm³`；八份阳性 STEP 与逐对材料完整保留。全带实算与先前已冻结的几何预测最大差约 `7.08e-16 mm³`。这确认了两层台阶问题，未把真实交集改记为包络未决。

严格原版 resume 已独立恢复六份完成 bundle，`all_six_trials_validated=true`；六项均记录 reused=true、`native_executed_this_invocation=false`，没有重新执行 trial CAD。aggregate job 本身另做过 CAD box preflight，故不称整个 job 未运行 CAD。resume 原报告 SHA 为 `910752107cdaae714cd1ea0ee81d01cd63f0cc1b958234fc29010288302ccd76`。

每个 job 实际通过 Python 3.12.14 / uv 0.10.10、43 包前后检查和 INT/TERM 生命周期门控。各 producer 的原始 ZIP、全部日志、API、源身份、资源采样与独立核验均已保存；18,310 个 artifact 内容成员出现次数包括重复基线副本，不能称为独立源文件数。完整归档为 41,133,399 B、SHA256 `aa61452f0e343458e082790d96a6011d6a2acb7a2055c0a719b50e698629a2ff`。[执行摘要与范围](geometry/evidence/D4-original-v4-six-bec1c8d7/README.md) · [原始包持久索引](LARGE_EVIDENCE_PERSISTENCE.json)

**各组原 profile 的四条端点外拒绝仍然存在。** 原 runner 固定的 `hosted_Actions_execution_claimed=false` 未改写，hosted 事实由独立 GitHub 原件证明。六组执行完整，并不满足全部几何 clear、真实机构允许域、连续运动或实物放行。


D4 另实际完成一个独立 STOW ORTHOGONAL 点：`dx=+0.0252814320072192 mm`、`dq=-0.010073907052108134 mm`、candidate=none。154 体、11,781 对全部本次重算，其中 782 次 native Common、10,999 次正轴间隙；0 阳性 / 0 error，23,562 条 journal 事件完整，独立新进程 STEP reader 通过。原 `exact_commit_execution_claimed=false` 保留，51 个实际源码/输入与 C2 Git blob 的绑定由补充审查证明。它只覆盖这一个有限正交点；完整左右独立槽域及真实 factory 的正 q 段仍待验证。[完整独立审查](geometry/evidence/D4-original-v4-six-bec1c8d7/independent-review/D4_COMPLETE_INDEPENDENT_REVIEW.json)


### 已定位的第二处 KEY 台阶

第一轮端面退让消除了 CAP_0 的旧干涉，但 FULL_BAND 下左右 `KEY × ROOT_INNER` 各保留约 `0.00649356026866 mm³` 的实际交集，每侧由四个正体积实体组成。独立 STEP 读回的残余位于 `Z=3.6..4.0 mm`，在本次切削带 `Z=2.699..3.101 mm` 之外。[原生及读回原件](geometry/evidence/candidate-bec1c8d7/key-relief-full-band/execution.tar.gz)

由阳性实体 Y 边界及已知原刚体位移回推，另一组台阶的名义余隙约为 `0.055 mm`，小于 full offset `0.06063677106654654 mm`。每侧 XZ 截面积为 `1.152 mm²`，故预测交集体积为：

`1.152 × (0.06063677106654654 − 0.055) = 0.00649356026866161408 mm³`。

该值与实际 native Common 相差约 `4.3e-17 mm³`。有限 worker 的原 `exact_commit_execution_claimed=false` 字段保持不变；补充文件逐项核对了 54 个实际执行源码/输入与 C2 Git blob 的一致性，此补充绑定没有改写原报告。这是回移几何推导，既不是新的 nominal-plane 测量，也不是实物余隙测量。半带位移尚未跨过第二余隙，不能用半带的结果证明 full-band 闭合。后续应对两层台阶及完整独立槽域定义新的结构候选；不得把软件 q 范围截断当作已经存在的实体止挡。[独立复核](reviews/KEY_FULL_BAND_REVIEW.json)

### S3：第二层让位与 reader 修复已冻结，实际资格单独取得

新功能源 S3 为 `20dfddfe8497a73b1814623e6320b3a9ac4273d0`、tree `346eb145bd243ef829b9a540b36dfc830d7298f3`，parent E2。它只改变已审查的十个文件：新增独立命名 `stow_two_layer_face_relief`、在现有 worker/监督器/reader 中绑定其身份及材料复核，修复两个 SLIDE reader 的模块导入顺序，并登记 9 个 KEY 合同反例与 4 个 reader 入口回归。原 36 套的登记最低数因此从 1,641 变为 **1,654**；登记数本身不构成实际通过。

v2 对左右 CAP/ROOT 共四个固定体使用 14 个切除盒，保留原槽域与默认 candidate=none。第二层 Z 为 `3.6..4.0 mm`，固定台阶 Y 为实算 `13.645 mm`；KEY 名义 Y `13.7 mm` 来自既有 Common 与已知 dq 的回移推导。新切面 Y 为 `13.61936322893345 mm`；`0.020 mm` 构造余隙与 `0.001 mm` padding 是研究定义，没有被赋予真实工艺能力。新的 reader 独立重建每个 cutter，要求与保存的 STEP 双向差体积均不大于原 `1e-7 mm³`，再执行完整材料守恒检查。

准备阶段九个新 KEY 反例和四个入口回归、原 16 个 complete-reader 回归均分别通过；新增 13 项随后也在 D5 全量执行中实际通过，不能重复加计。D5 的三组 native 现已完整执行并独立核验，全部使用 exact S3、154 体、11,781 个 fresh 体对，每组 782 次 native Common + 10,999 条正轴间隙证书及 23,562 条 journal 事件：

| D5 有限点 | 实际阳性 / 求值失败 | 原有限点结论 | 独立 STEP / 材料回读 |
| --- | ---: | --- | --- |
| 默认 none、STOW FULL_BAND | 4 / 0 | 拒绝，四对和原 D4 完全一致 | 通过证据校验，保留真实交集 |
| v2、STOW FULL_BAND | 0 / 0 | clear | 通过；14 个切除体定义与真实 STEP 的双向差均为 0 |
| v2、STOW ORTHOGONAL | 0 / 0 | clear | 通过；同样保留原材料守恒及双向重建检查 |

四个实际修改体在切除前后各保持一个正体积 Solid；材料余额最大误差约 `3.33e-12 mm³`，没有增加材料。原始 `exact_commit_execution_claimed` 字段未被改写，额外受控源码绑定证明本次实际 S3 身份。三份原始 ZIP 的 2,284 个内容成员、35,343 次 fresh 对计算及 70,686 条 journal 均独立核验。**D5 整体仍因上文单元失败而失败，不能据三组几何 job 成功推进候选。** [三组实际摘要](geometry/evidence/source-20dfddfe/D5-finite/GEOMETRY_SUMMARY.json) · [源码冻结回执](source-S3/S3_SOURCE_PUBLICATION.json)

新 144 个跨侧移动体对 X 间隙证书只适用于所列 24 体刚体 STOW 研究域。真实 factory 的正 q 段还驱动 STOP 和 SPRING：原先的小正 dq 交叉检查不能涵盖进入 rounded-corner 的较大正 dq。正 q 验证必须使用真实 factory、扩展运动体清单并按接触轮廓分段，不能把有限负 dq 或 24 体证书扩大为完整允许域。[范围补充](geometry/evidence/source-20dfddfe/key-v2-preparation/S3_KEY_KINEMATIC_SCOPE_ADDENDUM.json)

### S4 / D6：同版三组有限原生验证完成

| S4 实际 case | 完整体 | 本次 fresh pair | 正 Common | 求值错误 | 有限点结果 |
|---|---:|---:|---:|---:|---|
| v2 STOW FULL_BAND | 154 | 11,781 | 0 | 0 | clear |
| v2 STOW ORTHOGONAL | 154 | 11,781 | 0 | 0 | clear |
| 原默认 none STOW FULL_BAND | 154 | 11,781 | 4 | 0 | 不 clear，原真阳性保留 |

三次均从 S4 新执行，合计 **35,343 个 fresh pair、70,686 条 journal 事件**；每组 782 次 native Common、10,999 次正轴间隙。新进程同 CAD 内核 STEP reader、四个改体的 14 切除盒重建与材料守恒均通过；最大绝对体积平衡差 `3.325340003357269e-12 mm³`。默认 none 的四个阳性与 D4/D5 逐值一致，保留原 `1e-7 mm³` 判据；没有更改默认生产几何。原 raw `exact_commit_execution_claimed=false` 保留，实际 S4 的源身份由另行前后 blob 核验支持。

这两个 v2 点不覆盖正 q 时真实 STOP/SPRING factory、完整连续槽域、SLIDE 中途 panel/KEY、工艺公差或结构强度。两点 clear 不能关闭下述 L1 阻断。[同版三组结果与材料](geometry/evidence/source-dd7def6e/D6-finite/OUTCOME.json) · [原件哈希](geometry/evidence/source-dd7def6e/D6-finite/ARCHIVE_REFERENCE.json)

### SLIDE 的 19 条未决与 reader 缺陷

10 条保守包络未决涉及背板—KEY、KEY—STOP 和弹簧外径公差包络—STOP；9 条顶层求值失败涉及 B_SHELL 与部分左右伸缩件。原记录包含 59 条递归 error，不能改称 59 个失败体对。其中 8/10 个保守包络对内另有 epsilon 区间异常，59 条 error 分布在 17 个体对内。以 `A_BACK_PANEL × L_KEY` 的一个末端区间为例，区间宽度为 `5e-16 mm`，按原源码算术得到的二进制浮点位移约 `4.44e-16 mm`，触发原 `1e-12` 非零位移保护；该位移数字并不泛指所有 epsilon 异常。其他记录涉及有向体积和受限曲面方法。需要按原 pair、区间和方法分别修复，不能统一忽略成 clear。[逐对问题表](reviews/SLIDE_ISSUE_MAP.md)

C2 本身保留一个 **standalone reader 导入顺序缺陷；S3 已做源修复，资格属于新源码身份**。直接运行 `check_slide_checkpoint.py` 会在身份检查时拒绝，因为同名 `owned_process` 被解析到 SEATING。完整独立读回采用原 supervisor 的导入顺序，在新进程调用未改 reader；没有关闭任何 source/path/HEAD/env/postguard 检查，最终 exit 2 正确保留负结果。原 CLI 失败、错误 launcher 尝试、实际成功读取 launcher 和 SHA 都随包保存。该变通读取不等于直接 CLI 已修复。[精确复现说明](geometry/evidence/candidate-bec1c8d7/slide-r3/REPRODUCTION.md)

S3 的改动仅调整两个入口的导入顺序，保持身份、原检查函数与门槛；准备阶段四个新进程回归包含两个 foreign-module 拒绝反例。该修复没有消除 SLIDE 几何中的 10 个未决、9 个顶层求值失败或 59 个递归 error。

原报告 `completed_pair_count=11776` 是旧 heartbeat；完整数组与独立校验的 journal 均为 11,781。没有改写原始标量以掩盖这一差异。

### L1 已完成：方法失败定位与中途整件交集见证

[L1 run 40210275856](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40210275856) 在未改 C2 方法和原资源门槛下，实际完成 E17 的 17 次求值失败调用与 O72 的 72 次保守重叠调用，覆盖原 19 个问题体对。**89 个 raw 返回均与原 r3 逐值相同**；原 aggregate 仍为 17 `unresolved_evaluation`、72 `unresolved_enclosure_overlap`。963 条源码/输入闭包、17 个 helper、43 锁包与原资源门控均已核对。505 条逐 case 材料记录产生 1,010 个成功的 STEP/BREP 导出，不能把它们当作 505 个全局唯一零件；没有声称另做独立原生 STEP 重导入。[公开工程摘录](geometry/evidence/candidate-bec1c8d7/slide-L1/OUTCOME.json)

25 个实际 ValueError 对象已具体定位：16 个来自 8 条精确宽度 `5e-16 mm` 的 interval 在双参考系下的位移检查；5 个来自左 B_SHELL 临时平面 prism 的约 `−2.2566e-10 mm³` 有向负体积；3 个来自真实 Common 体积大于该极薄临时 region 的无效结果；1 个来自原方法不支持的 EXTRUSION。完整 B_SHELL 本身仍是正体积实体。额外 272 个 GeneratorExit trace 事件来自原 generator 正常关闭，单独保留，不统计为 CAD 失败。原小区间、负体积与无效 Common 都没有通过删除、取绝对值或降门槛变成 clear。

**另有一个需要优先处理的几何发现。** 对 8 个 A_BACK_PANEL×KEY 节点的 16 个 frame 逐项对照原源码、descriptor、单一 q 参数与实际 Common 材料，确认这些 positive Common 来自 `whole_start/whole_end` 两个完整实体端点，不是放大的 spring/height 包络。独立核验支持以下新增推导：

| 声明名义刚体域中的位置 | 涉及完整实体 | 实测 Common 体积 |
| --- | --- | ---: |
| q≈3.4821884705062427 mm；slide≈23.142044210239405 mm | A_BACK_PANEL 分别与 L_KEY、R_KEY | 每侧约 `0.245587849382247 mm³` |
| q≈9.160729490168748 mm；slide≈60.880681403413135 mm | A_BACK_PANEL 分别与 L_KEY、R_KEY | 每侧约 `0.230137383539251 mm³` |

这构成**声明的名义刚体 SLIDE pair 域内、四个侧×坐标状态的有限整件正 Common 见证**。它是原实际材料结合源码的新增推导，保留了有理参数、binary64 实际平移 recipe 和各自差别；原 r3 的 overlap 分类与 `collision_proved=false` 均不改写。尚未在这些坐标新构建完整 factory 场景、重验全部体对或独立原生重导入，因此不称实物碰撞或整机资格。其余 32 个 KEY/STOP 调用含独立 q/height 包络，另 32 个 SPRING/STOP 调用含最大 spring 包络及相关性问题，64 个结果仍未提升为实体碰撞。[独立见证审查](geometry/evidence/candidate-bec1c8d7/slide-L1/FINITE_WITNESS_REVIEW.json)

下一步首先复现上述两个中途位置的完整 factory/整件材料并处理 panel/KEY 结构，再分别修复临时包络构造、极小精确区间与 EXTRUSION 支持；随后补齐独立偏移、真实相关接触、连续柔性有效性和正反程。端点 v2 有限 clear 无法消除这些中途阻断。

### SEATING 通过范围

该结果覆盖固定 slide `79.75 mm`、共同 descent `0..8.2 mm`、两侧独立可行伸缩分配以及 slot flanks 的连续外部体对域，使用 28 个精确多面体顶点。KEY/crosshead offsets 固定为 0，tabs 为 3 mm，途中没有七个 OPEN 附件。它没有证明非零 KEY/crosshead 的完整允许域、柔性体连续自身有效性、反向动态复锁、力平衡、公差或实物动作。

## 4. 原 panel / frame 数值诊断

本节先列的三种 probe 修正与 frame 尝试在 C2 源码冻结前执行，逐次源码 SHA256 与原文件另行保存，不重新标注为 exact-C2。随后 N1/N2/N3 则实际检出 C2 并重新装配相同原矩阵，二者身份和结果分别记录。

重建的 panel K/C 与 frame K 匹配已记录的 **2026-10-23 重建矩阵**字节身份，不把它们混同于更早 volume-v3 的 K。panel 的 344,103 DOF、frame 的 474,726 DOF 和各自原约束没有被删减。[数值回执](numerics/SUMMARY.json)

原 panel 判据保持为 float64 运算的 `max(abs(Kff @ u − rhs)) / max(max(abs(rhs)), 1) <= 1e-7`。原五个方向中 probe 0 的全 1 方向失败，其余四个通过。三种有界处理均没有让原五探针全部合格：

| 处理 | probe 0 原检查结果 |
|---|---:|
| 原求解基线 | `2.384908468e-7` |
| 高精度残差驱动修正 | 最终 `1.760949857e-7`；最好一步 `1.539097907e-7` |
| float64 修正 | 最终 `2.065996289e-7` |
| 对称均衡对照 | 最终 `3.161390295e-7` |

同一最终向量的 extended residual 较小，仅支持病态/消减敏感的诊断，不能替换原 float64 资格。原 probe 0 的最差自由 DOF、RHS、分母、残差、修正范数和迭代 SHA 已保留；各轮初始与最终全场也已保存。中间迭代没有逐步保存完整全场数组，这一边界明确保留。

frame 的 5 GiB 和一次 6 GiB 有界分解尝试均因 SuperLU 分配资源失败退出，**0 个 RHS 求解完成**。这是资源失败，不是 0/5 残差拒绝，也不是不可行性证明。没有继续盲目扩大预算。panel 五探针未过，完整响应/H、frame/trace、原 `2e-7` restore-H 条件及接触 checkpoint 都未被提升为合格。[frame 完整原件](numerics/evidence/frame-rebuild-and-factorization/) · [完整探针持久化索引](numerics/RAW_EVIDENCE_PERSISTENCE.json)

### N1：exact-C2 输入的新选主元策略，实际在分解阶段失败

[N1 run 40206010654](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40206010654) 使用独立 driver SHA `5f59b7e916eae3a1881d71f9dc656b337ade6a87870e3da429e3666e10bdd1ad`，检出 C2 并重新装配 panel；所得 K 为原 `80f6f502…`，C、点序、五个 RHS 与方向字节均核对通过。策略为 COLAMD / `diag_pivot_thresh=1` / `SymmetricMode=False`，不缩放、不做迭代修正，保留原 `residual_record`、6 GiB address-space limit 与原外部守卫。

实际原日志为 `Can't expand MemType 0: jcol 234701`，随后 SciPy 包装为 `SystemError: gstrf was called with invalid arguments`。锁内 SciPy 1.18.1 的源码把 MemType 0 对应到 LUSUP 数值存储，确认该路径是内部 factor storage expansion failure；没有取得实际分配 errno 或申请大小，故未将 6 GiB AS 单独确定为唯一原因。

该次五个 RHS 与方向已在 factor 前保存，**0 次 RHS solve、0 个全场解、0 次残差评估**。原监督器约 27.113 s、exit 1、`resource_stop_reason=null`；1 s 采样 RSS 峰值 3,757,465,600 B，进程实际 `ru_maxrss=5,085,176 KiB`，两种测量不混用。它不是五探针残差失败，也未触发 180 s 或共享 6.8 GiB 守卫。完整原始 ZIP 为 201,582,664 B、SHA256 `a69e6dc15e81cc750552a062224c0e92e352ec7f29a691d92f148885d7cf8c2c`，767 成员全部按 CRC/大小/SHA 和 manifest 独立核验。[原始包索引](LARGE_EVIDENCE_PERSISTENCE.json) · [锁源码诊断](numerics/evidence/panel-N1-hosted/independent-source-diagnosis.tar.gz.reference.json)

### N2 / N3：排序与容量对照已实跑，仍未进入探针求解

[N2 run 40207901134](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40207901134) 只将 N1 的 COLAMD 改为 MMD_AT_PLUS_A，保留 threshold=1、SymmetricMode=False、原矩阵/RHS/约束/残差和全部预算。实际再次在 LUSUP 扩容失败，日志 `Can't expand MemType 0: jcol 312868`，监督器约 45.345 s。worker 的实际 `ru_maxrss=4,104,700 KiB`；采样 VmSize 达 `6,440,398,848 B`，距实际 6 GiB AS 只余 `2,052,096 B`。这个容量接近现象支持另做一次明确的 AS 对照，但没有证明 AS 是唯一原因，也不能按剩余列数线性估计分解耗时。完整 201,585,678 B ZIP 的 767 成员和五 RHS/方向全部独立核验。[N2 结果](numerics/evidence/panel-N2-hosted/SUMMARY.md)

[N3 run 40209098454](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40209098454) 保留 N2 的算法与数值条件，只把新研究 driver 的 AS 从 6 GiB 改为 8 GiB，并增加只读 worker 内存观测；原 180 s、共享 6.8 GiB、磁盘 500 MiB 和单线程守卫不变。实际在 **181.076 s 被原 wall_time_limit 终止**，worker exit −15、向外传播 143，外层 hosted cap 未触发。五个原 RHS 均已保存，但没有分解完成回执、solve-start、解向量或残差记录；终态 probe report 也不存在。本次没有 N1/N2 的扩容报错，不能据此认定分解已经完成。

N3 的采样 VmSize 峰为 `8,380,502,016 B`，观测到的内核 VmHWM 为 `6,530,998,272 B`，采样共享判据峰为 `5,935,220,968 B`；分别约 7.805、6.082、5.528 GiB。这些值不是完整 factor VmPeak 或 driver 终态 ru_maxrss。后段内存回落没有配套 jcol/CPU 进度证据，不能称“接近完成”。原始 ZIP 为 201,592,456 B、SHA `8e1bdb8cff00d73550f9a6b472cc261b1bdaf688588fc2ef3ec84fca9927c97e`，766 成员完整核验。[N3 独立原件审查](numerics/evidence/panel-N3-hosted/INDEPENDENT_REVIEW.json)

| 数值尝试类别 | 真正完成的探针解 / 残差 | 实际结论 |
| --- | ---: | --- |
| 冻结前原三种修正/均衡策略 | 每次 5 / 5 | 各 4/5 达原 `1e-7`，probe 0 拒绝 |
| C2 N1、N2 部分选主元策略 | 每次 0 / 0 | 分解阶段 LUSUP 扩容失败 |
| C2 N3 AS 对照 | 0 / 0 | 原 180 s 墙钟守卫终止，分解完成未获证 |

后续不自动增加预算或降低 `1e-7`。下一次研究需先给出可复核的分解容量/时间或替代算法依据，并继续保存全部原输入与资源回执；原五探针真正合格之后，才进入 3,885 列响应、H、frame、trace 和原 restore。三个新增失败不得写成新的“各 4/5 通过”。

## 5. 同版电气与产品合同

已建立独立 EP5 **188 mm 总长 / 164 mm 自由段**的 continuity26 研究图稿。真实 KiCad 9 原生读取与全 severity DRC 已执行：52 个端子、130 条走线、2 个封装，error/warning/exclusion 全部纳入检查，0 DRC 项、0 未连线。板和工程文件前后未变，五个执行源码文件匹配 C2。[完整原生回执](product/execution-bec1c8d7/execution.tar.gz)

当前 C01–C26 是研究导通网，没有 OEM 显示/触控/电池/充电/USB pinmap。该执行没有请求原理图 ERC 或板—原理图 parity，不能据空 parity 数组声称 ERC 已通过。高速阻抗、载流、回流、温升、动态弯折和成品叠层仍需真实输入。

G3 EP5 v2、G4 的 9 类功能 × 17 个动作阶段 × 两种原系统供电模式，以及 G5 的逐样本暴露/动作/连续 cycle 验证已经实现并纳入 C2 完整测试。合同区分 unknown 和实际 fail，不能用缺测掩盖失败，不能用循环汇总替代连续原始采样。绑定的原始模板和 readiness 回执在产品执行包中；它们没有被改称实物试验结果。

### S4 同版空采集包已生成

从独立 exact-S4 检出调用原生成器，生成七个原输出；公开交付其中四份原字节空模板。121 个源与 13 个 native 输入的绑定核对通过，156 个已物化文件由独立读者核 SHA/Git blob；native 输入只读做身份摘要，没有运行 CAD/FE。G3 当前 EP5 结构绑定检查通过，物理资格评估未执行；G4/G5 原 CLI 的无 acquisition 评估与 builder 相同，均为 `unknown`，分别保留 58 与 21 个阻断。新实测 0、实物身份未填、全部放行 false。旧 C2 包不变，当前现场可从 S4 包开始采集。[同版空模板与现场步骤](product/qualification-s4/README.md) · [实际生成与检查结果](product/qualification-s4/OUTCOME.json)

## 6. 真实器件、OLED/FPC 与当前结构仍需输入

本轮没有取得新的真实手机标签、尺寸、端子、原机功能或 G3/G4/G5 原始测量。旧 ADB 记录只支持部分 `XT2551-3` 身份；当前历史端口实际不可达，也没有 adb 程序。**10 个身份字段、7 类实物零件、12 类接口仍未闭合**，四个空间占位体尚未被真实包络替换。[现场逐项交接单](product/PHYSICAL_HANDOFF.md)

公开 OLED 筛选没有产生可冻结的 PN/revision。新增供应商 PDF 的实际料号为 `TA067FVMK01-08`，其 `165.680 mm` 外形长度相对当前最短路径 `187.768803 mm` 差 `22.088803 mm`，`71.940 mm` 宽度比当前 `67 mm` 假设多 `4.940 mm`。这只排除了该参考件直接适配当前固定路径的说法，不证明所有其他路径或料号都不可能。完整成品叠层、COF/触控/端部、动态半径、应变和全程支撑尚未冻结。[原始来源核对](product/OLED_SOURCE_RECHECK.json)

已为当前切改后的 EP5 建立 154-body 实际名义体积/bbox/来源清单和材料、13 类载荷、支承/接触、预载、公差与收敛合同。没有把 bbox 当壁厚，没有把未知材料填成通用弹性模量，没有把旧 PR34/PR35 模型继承成当前壳体强度。当前完整 FE 网格与全域结构、公差资格仍未完成。[结构输入合同](structural/CURRENT_EP5_INPUT_CONTRACT.json)

## 7. 下一步执行顺序

1. **几何与数值并行处理明确失败。** 依据原 v4、独立槽顶点和两层 KEY 台阶证据定义新命名结构候选；先复现并修复 SLIDE 中途 A_BACK_PANEL/KEY 的有限整件正 Common 见证，分别修复方法失败与相关包络未决，再补齐非零偏移、连续柔性有效性和反向动作。原 panel/frame 则保持原判据，先解决 probe 0 与分解资源问题，再进入 H/trace/restore；这条研究线不代替当前 EP5 结构。
2. **现场立即按同一 specimen 采集。** 完成 10/7/12 身份、原件、尺寸、方向和功能基线，冻结真实屏幕与 FPC 成品合同。缺输入的材料、载荷、OEM 指派与阈值继续保留 unknown，并由相应硬件、显示、机械、电气和测试职责提供来源。
3. **按实际输入冻结下一候选。** 真实包络、第二层 KEY 台阶修复、FPC/OLED 方案、OEM 接线与当前结构改变时，保存清晰差异和新的源码身份；重新执行受影响的完整域及新候选资格，不把 C2 回执换 SHA 复用。
4. **完成实物合同后顺序 G3→G4→G5。** G3 无电装配/动作与导通，随后同版本同样件 G4 带电功能与动作，再执行有来源的 G5 寿命、环境与工艺计划。阈值、校准、不确定度、采样、时基、循环与失效/维修/换件记录必须先闭合。没有给尚无依据的寿命或工艺试验编造完成日期。

逐一对应用户十工作包的状态和下一轮窗口见 [执行状态与 Work Plan](WORK_PLAN.md)。原始证据入口见 [机器汇总](SUMMARY.json)、[完整证据索引](COMPLETED_EVIDENCE_INDEX.json)。

## 8. 复现边界

以下完整软件入口检出当前已验证 S4。历史 ECAD、canonical、SLIDE/SEATING、D4、L1 与 N1/N2/N3 必须另检出各自回执中明确的 C2 身份并使用对应原编排，不能将此处 S4 命令换贴到旧结果。

下载本次证据后，复现当前完整软件验证应检出 **S4 源码**，为每次运行选择新的仓库外输出目录；不能在本文件所在证据/台账提交上填写 `--expected-head S4` 冒充同一执行。

```bash
git switch --detach dd7def6e6a4de9f47dc91ca2ab336fb1a8828560
uv sync --locked --no-cache
uv run --locked python -B tools/check_environment.py
uv run --locked python -B tools/verify.py --expected-head dd7def6e6a4de9f47dc91ca2ab336fb1a8828560 --output /tmp/razr-s4-new-unit-run
python3 tools/sync_current_design.py --check
```

几何执行还需要完整受控原生输入、原容量守卫，以及相应原命令/源路径身份；SLIDE 独立读取使用上文固定 launcher 说明。原数值 raw 包、源码哈希和环境证据均有独立索引。临时安装树或重复下载文件的回收有单独回执；不声称已经回收的 KiCad 运行树仍原位可用。

## 9. 证据公开范围

自动审批拒绝了把新增 N3/D5 完整原始运行归档直接写入公开 GitHub 的动作，理由是这些原载荷可能包含敏感环境信息，当前授权未明确覆盖公开原载荷。后续只读检查确认有 API 作者邮箱、私有文件定位和实际运行环境记录。

本次采用已完成的替代交付：原始文件逐字节保留并单独私有保存；公开 PR 提供工程结果、受控源码身份、原始文件大小与 SHA256、独立复核的工程摘录。`derived_public_summary` 标志与 `.reference.json` 明确区分摘录和原件，不把公开摘要称为完整原日志，也没有通过其他通道公开被拦下的 raw 载荷。[证据访问说明](EVIDENCE_ACCESS.md) · [原始文件哈希目录](LARGE_EVIDENCE_PERSISTENCE.json)
