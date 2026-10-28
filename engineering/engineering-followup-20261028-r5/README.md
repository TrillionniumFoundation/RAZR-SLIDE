# R5：已执行到 V5 的工程与科学证据

本检查点包含实际完成的原件恢复、云端包络计算及独立验证。**全部 blocker 尚未闭合。** 原完整边界模型的结果、新增裁剪实现类的条件结果、缺失真实输入和未执行工作分别记录。

## 当前完整 factory 原件恢复

已恢复原 run `40285103942` 的 near／far 两份完整 K3 factory 科学 ZIP，每份逐成员核对字节、CRC 和 SHA。对应 slide 为 `23.142044210239405 / 60.880681403413135 mm`，其 KEY 源坐标 q 为 `3.482188470506243 / 9.160729490168748 mm`；两组坐标不能互换。

每姿态 154 个名义体、11,781 个体对，包含原 factory 与原独立 reader 两套全对记录；两姿态共 47,124 行当前体对结果。两侧当前 panel／KEY 的直接 Common、严格 Common、全对和原独立读回结果一致。当前材料原字节、原 S4 来源与 F1／K1／K3 改版关系均保留；旧 F1 真干涉没有被覆盖。

本轮做的是完整历史原件恢复与跨作者实际读回，没有重新运行 CAD，也没有把该两姿态提升为全连续域证明。见 [native](native/README_R5_CURRENT_FACTORY.md) 和 [原件独立审核](review/native-archives/README_R5_INDEPENDENT_NATIVE_REVIEW.md)。

## 包络的实际运行

| 方法 | 实际执行 | 原 `1e-7 mm³` 阈值的结果 | 范围 |
|---|---|---|---|
| R5 V3 完整边界外部通道 | run `40641230212`，五阶段完成，约 9.73 s | 原完整边界模型 4／16 | 原 full D 与所有闭载体保留；native 边界语义与编译误差仍未由该证明建立。 |
| R5 V4 原端点分盒 | run `40643098035`，单盒 producer 完成，checker 真报错 | 真实 cell 202 上界仍 `0.4800000000000019`，未过门 | 6 splits／13 nodes／7 leaves；无体积排除。checker 完成12项拒绝控后因无 excluded 叶而报错；后三阶段未执行，post-verification 阈值 guard 未到。 |
| R5 V5 裁剪实现类 | run `40645988108`，五阶段完成，约 12.35 s | 新条件模型 8／16 | 另有明确的 inner-hole／端点闭合类前提；原 V3／V4 结果不重分类，native membership 未证。 |

V5 首个原 cell 202 在新模型下排除全部正体积，闭边界仍保留。全 16 帧中的四个 panel／KEY 上界为 `1.8943394070663295e-14`、`3.793469827035721e-14`、`1.9246042482697247e-14`、`3.8554187302266483e-14 mm³`。四个原 SPRING／STOP 极小位移帧保持通过。八个 KEY／STOP 帧经 387 次精确分盒后仍各约 `0.016 mm³`；这些是尚不能证明净空的上界，不能直接称为实体干涉。

原时间、RSS、共享内存、磁盘和输出门未调宽。V5 实际独立 checker 完成来源、孔核心、UV 闭覆盖、原边／顶点、完整 D、全部 roots／树和适用正负控检查。第三位作者的实际完整读回正在进行，后续记录单独追加。新增裁剪模型不是原生几何、当前完整 factory G2、制造或实物资格。

完整原运行产物保持字节不变：[V3](envelope/actions/run-40641230212/)、[V4 实际失败](envelope/actions/run-40643098035/)、[V5](envelope/actions/run-40645988108/)。当前执行源码与锁位于 [compute](compute/)，早期实现和未执行草稿位于 [source-history](envelope/source-history/)，实际汇总位于 [publication](publication/)。

## 原数值资格及当前结构的边界

本轮完整读回原 N15 H／restore 科学 ZIP 的 384 个成员，并交叉核对八份原报告。原 panel／frame 五探针各为 5／5 通过原 float64 `1e-7` 门，原 H／restore／四载荷线性种子资格保持其原范围。R5 没有重跑 solver、K 乘积或 H action。

原 H 每体 3,885 列；原独立 H／restore 检查不等于全部 7,770 列独立 K 残差复算，也没有保存全部 H 列的全场。任意 RHS 逆算子、有限 QP checkpoint／resume、当前 K1／K3 FE 和实物资格没有从这些记录取得。见 [原数值范围与原残差](numerics/README_R5_ORIGINAL_NUMERIC_SCOPE.md)。

## 真实器件、FE 与逐级实物门

已实际接收完整 XT2551-3 官方快速指南并核对内部 revision；它仍是型号资料，不能替代同一样件或 OEM 的部件资料。原 228 项事实中新增合格绑定为 0；没有新 G3、G4 或 G5 真实 pass。

[交接合同 V2](handoff/README_R5_EXTERNAL_BLOCKER_HANDOFF.md) 将现有要求分为13个交付包，228个原ID唯一对应，207项同一样件与21项所选部件 revision 的要求保持。当前材料／工艺／载荷／公差、OEM互连与完整叠层、有来源的阈值／采样／校准，以及同候选同样件 G3 → G4 → G5 仍需实际证据。缺测、失效、维修与换件分别保留。

## Git 和原件边界

本分支以实际可核对的 R4 提交 `c5f6606924937d716b007cd3ffa8e54df8ecfa5d` 为来源。原授权精确提交 `a11b00f71231ef3516d2a79c73fa441c375ac755` 的 Git 对象当前尚未取回；本分支没有替代它，也没有伪称完成原 SHA 的推送。

公开投影与原件身份分别见 `R5_STABLE_PUBLIC_EVIDENCE_MAP.json`、`R5_EXECUTED_PUBLIC_EVIDENCE_MAP.json`。完整原运行数据、真实失败和所需原科学 ZIP 身份继续保留；GitHub job success 只说明登记流水线完成，不等于全部几何或实物门通过。
