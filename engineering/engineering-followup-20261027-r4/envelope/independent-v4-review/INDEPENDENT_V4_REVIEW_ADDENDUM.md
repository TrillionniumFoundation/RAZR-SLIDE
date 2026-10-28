# V4 精确并盒与实际结果：独立追加审阅

本追加审阅由 `/root/r4_real_sources` 完成；原 `independent-source-review` 的 V2/V3 审阅保持冻结。本次没有重跑数学 producer，也没有重复另一实现的完整组合穷举。

## 实际读回

独立程序实际 exit 0，耗时 **17.955591885001922 s**，处理全部 **16 帧 × 3 种覆盖＝48 covers**：

- **18,517 个细正盒**逐项对应至 **1,911 个并盒 run**。
- 每个 run 的细盒顺序、无遗漏／无重复、轴向相邻无正宽 gap、横向两个范围完全相同，以及精确并集端点全部核对。
- 全部 **56,869 个已输出正 cell**重新核对三 run 交集、唯一索引、正仿射宽度、行列式体积及各 cover 的精确求和。
- 所有原细切面继续保留为零体积载体；没有通过去掉零体积接触面来改善结果。

另一实现已实际执行 X/Y/Z 固定顺序的完整组合枚举，不使用 producer 的 bisect 优化，完成 16 帧检查。其 worker 实际耗时约 55.01 s，峰值 RSS 269,647,872 B；producer 约 111.14 s，峰值 RSS 255,623,168 B。两者 canonical entry 与 owned controller 的真实成功回执已核对，原 600 s／768 MiB 及其余门未变。

本追加程序审核了另一实现的源码与冻结成功记录，并对全部实际并盒和输出 cell 作独立读回；不把这称为第二次完整 source-support／三重穷举运行。

## 为什么新增优化仍保守

相邻轴盒只有在共享端面且其余两个坐标区间精确相同时才合并。这时合并盒就是原闭盒的精确并集，既不增加材料假设，也不丢掉任何正体积区域。各轴 run 仍按该轴排列，内部不重叠，因此 starts／ends 单调。producer 的两个 bisect 条件只排除端点相触或完全分离的区间，正宽重叠候选不会被排除；接触点仍由原切面载体保留。

每个正 cell 是外向单位立方体经 `x -> lower + diag(widths) * x` 的像。三项 width 都严格为正，所以映射单射、行列式为正、面棱顶点关联和外向性保持；有向体积等于单位立方体体积乘三项 width 的乘积。无需为每个不同有理坐标的盒重复构造并积分同一组 12 个三角面。

这些是精确有理盒载体的集合与拓扑结论。原材料边界语义、编译后二进制误差和实物资格仍不是本方法证明的对象。

## 两个原门必须分别计数

| 项目 | V4 实际结果 |
|---|---:|
| 原 `upper <= min(volume) + TOL` 门 | **16/16 通过** |
| 原 `upper <= 1e-7` clearance 门 | **4/16 通过，12/16 失败** |
| 共同 L2 球公差诊断 clearance 门 | **0/16 通过** |

旧 aggregate 字段 `conditional_upper_bound_gate_failures=12` 的实现实际统计 clearance 失败，不能解释为 min-volume 上界门失败。原逐帧字段未变，本追加报告重新分别计数。

原 V3 最终 controller 为 **completed=false、worker exit -15、resource_stop=wall_seconds、600.255199149 s**。该容量失败已读回并保留，不因 V4 成功而改写。

V4 的上界门改善是实质计算进展；它没有增加 clearance 通过帧数。`native_boundary_semantics_verified`、`compiled_error_bound_verified`、`full_continuous_G2` 和 `physical_qualification` 继续为 false。
