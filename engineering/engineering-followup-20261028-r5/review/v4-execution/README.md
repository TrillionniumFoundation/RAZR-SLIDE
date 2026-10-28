# R5 V4 实际失败运行：跨作者独立读回

## 结论

**独立证据读回完成；V4 单盒数学阈值未通过，原 V4 checker 执行失败，后续三个阶段未启动。** 三种状态分别保留，审核完成不改变任何原运行结果。

本审核重新读回实际 CI 的完整归档、源码／合同／owned 执行链和完整单根分割树。没有 import 或执行 producer、checker、owned supervisor 或原生 CAD。只解码一个实际所需的原 R4 proof，未重新运行 R4 包络证明或完整 factory。

## 实际运行与来源

| 项目 | 证据 |
| --- | --- |
| 运行 | `40643098035`，attempt 1，push，completed / **failure** |
| 实际 HEAD | `06e4f37690e2d5b9dc2abaf69cab9ba16957f1e2` |
| 分支 | `evidence/full-sprint-20261028-r5` |
| job / artifact | `122665572124` / `12796451605` |
| 归档 | `RAZR-R5-refinement-v4-run-40643098035.zip`，21,547 B，16 个文件 |
| 归档 SHA-256 | `bb76de46294c6cc77aed277602aaf11c8548486364ace52ba31250a285757987` |
| 冻结 source lock SHA-256 | `9068291e6684299604d489fbf175cf781c0d1a1648cf690a2f5c337dec139c20` |
| 实际 workflow SHA-256 | `29445c7313ee93ee36f9f08ae42b29dce3ddbd348221410ab57c03e5b08f62e7` |

审核作者独立读取 GitHub run、artifact 元数据，以及固定 HEAD 的 workflow 和 source lock。归档 16 个成员逐个检验 CRC、字节数和 SHA，再与展开文件一致比较。最终 9 份 R5 源码／方法／来源文件、3 份 R4 owned 基础代码及 19 份公开输入重新计算字节哈希，并对应运行时来源表。CI 日志中的 HEAD、固定 lock、退出代码和实际上传归档 SHA 也吻合。

选择对象是 **实际 V3 运行 `40641230212` 的 `case-001 / frame 1 / 原正单元 202`**，此前 disposition 为 retained。其选择记录逐字对应已保存的 V3 pipeline、全量 report、独立 verifier report 和原证书。它不是 V3 的静止见证。V4 使用完整原 D，没有静止截面反展开或缩小位移。

## 单根分割树完整，但上界没有降低

重新从原根盒和切分点构造树，确认 **13 个节点、6 次切分、7 个叶、最大深度 6**。所有节点恰好访问一次；无漏根、重复子节点、不可达节点或遗漏的 pending leaf。每个切分点都来自两侧原完整边界盒的实际端点，严格位于父区间内部。两个闭子盒的并集是父盒，精确有向体积相加等于父体积，切平面和根边界继续作为零体积载体保留。

| 量 | 独立精确读回结果 |
| --- | --- |
| 原根体积显示值 | `0.4800000000000019 mm³` |
| 排除的开内部体积 | **精确 0** |
| 保留叶数量 | 7 |
| tiny 正体积叶 | 6 个，体积全部计入 |
| tiny 叶体积合计显示值 | `1.5246900275534767e-14 mm³` |
| 大保留叶显示值 | `0.47999999999998666 mm³` |
| 全部保留体积显示值 | `0.4800000000000019 mm³`，精确等于原根 |
| 原阈值 | 原 float64 `1e-7`，未改变 |
| 新增净上界改进 | **精确 0** |

精确总保留体积为：

`10961262279981815290884188059995738986490489745 / 22835963083295358096932575511191922182123945984`。

它约为原阈值的 **4,800,000 倍**。六个 tiny 叶均严格大于零且不大于原阈值除以 100000；没有四舍五入丢弃薄层。最小正叶是 retained，停止原因确为 `tiny_exact_volume_retained`，因此本次原 checker 的“丢弃最小正叶”负对照可以具体识别为一个真实 tiny retained 叶的检查。

大叶为 node 12，停止原因 `no_original_blocking_endpoint_inside_cell`。审核独立验证了其完整 12 个通道的阻挡盒和“所记录 blocker 没有端点严格处于叶内部”的条件。它们均为原完整边界 cover 的 `face` 项：第一侧索引 97、94、13、96、2、176，第二侧 23、22、14、48、17、16。机器报告保留每个方向、材料侧、原件索引和精确边界盒，便于后续方法诊断。

这些阻挡盒和保留上界不能证明真实材料穿透。原完整边界包络与原生材料的语义、编译变换误差仍是未闭合前提。

## 原 checker 的失败单独保留

原 `verify-single/report.json` 实际记录：

- 3 个 phase 负对照已执行并拒绝。
- 2 个 root coverage 负对照已执行并拒绝。
- 7 个 partition 负对照已执行并拒绝。
- `channel_negative_controls` 为空，**4 个通道负对照未执行**。
- 唯一 frame 的树统计和保留上界已写入，且与本次独立重建一致。
- `execution_completed=false`，原始错误是 `actual geometric and partition controls required`。

原因是实际树不存在 excluded 叶，原 checker 没有取得可用于四个通道负对照的实际排除证书。其末尾无条件要求 channel controls 非空，因而抛错。不能把已有的树统计及 12 个拒绝记录改称 checker 完成，也不能从 V3 或未来 V5 借用通道控制计入本次 V4。

本审核器使用自己的判据，对实际副本另执行并拒绝相同的 **12 个可实例化损坏输入**，包括遗漏 pending leaf 和删除实际最小 tiny 叶的正体积。它没有执行四个缺乏实际 V4 排除证书的通道负对照。本地 12 次独立拒绝与远程 12 次原记录分开计数。

即使以后修复 checker 对“无 excluded 叶”的处理，这次保持不变的 `0.48 mm³` 上界仍然不能达到原阈值。checker 错误和数学方法没有取得所需改进是两项不同结果。

## 实际资源与停止位置

| 阶段 | worker 秒 | controller 秒 | entry peak RSS，B | 实际状态 |
| --- | ---: | ---: | ---: | --- |
| single-retained-cell | 0.295762 | 0.440889 | 94,294,016 | 计算完成；阈值失败 |
| verify-single | 0.260502 | 0.440304 | 94,171,136 | 报错，未完成 |

两阶段均实际通过原入场条件，`resource_stop=null`；wall、RSS、shared、disk、output 和 metadata margin 六个原门与 R4 一致，没有调整。实际输出分别为 10,383 B 和 4,067 B。由于两阶段都少于一秒，持久化 controller 资源样本只有入场行，另有握手初始内存与 entry peak；没有冒充完整运行中采样。

失败链保持原值：checker entry 的 `worker_exit_code=null`、controller 观察到 worker exit **1**、supervisor exit **2**、pipeline `completed=false`。CI 总 elapsed 为 **1.015984 秒**。原 driver 在 `owned stage failed; later stages remain unexecuted: verify-single` 停止，因此**尚未执行 verify-single 后的单盒阈值 guard**。不把停止原因改写成该 guard 的实际拒绝。

归档中 `preflight`、`all-refined`、`verify-all` 的合同、controller、report 和目录成员全部不存在；pipeline 也只有前两个阶段。完整 16 frame 并未执行，原 V3 的 4 / 16 结果没有更新。失败导致 driver 未运行最终的全体来源 postcheck，报告如实记录其缺席；已存在的 stage/source unchanged 收据按各自范围保留。

## 审核预算和产物

先读最终冻结源码和 V3 审计框架，形成保留原顺序及失败路径的计划；收到实际归档后再登记准确 run、HEAD、archive/source 身份和审计范围。预算为 180 秒、384 MiB RSS／地址空间、4 MiB 审核输出。只解码实际 `case-001 / frame 1` 一个原 proof，共 1,114,119 B gzip；没有解码无关的另 15 个大型 proof。

本次独立审核实际 **0.468403 秒、90,677,248 B peak RSS**，预算满足。`R5_V4_INDEPENDENT_ACTUAL_FAILURE_READBACK.json` 包含所有精确分数、叶盒、切分身份、12 个 blocker、来源／资源链及独立负对照。`R5_V4_ACTUAL_READBACK_BUDGET.json` 绑定最终审计源码，原计划保持原样，不把等待状态倒填成事先知道结果。

完整源码、元数据、预算、报告和本说明随 manifest 冻结。`full_continuous_G2=false`、`all_blockers_closed=false` 保持不变。
