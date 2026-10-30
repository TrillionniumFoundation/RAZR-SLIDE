# R9 连续包络：原 16 帧的条件源模型验收

本轮完整 producer 已在原预算内完成 **16/16** 原帧：从全部 **1,537 个原根**重新计算，使用 **718 次全局分割**，最大深度 **18**，实际 **4,722,120 次原边界片测试**。含全部证书序列化的记录耗时为 **552.217835624 秒**，峰值 RSS 为 **449,392,640 字节**。最坏交集体积上界为 **9.321533029448826e-8 mm³**，低于原 `float64 1e-7` 门槛。

独立读取器已在 **265.905903066 秒**内实际完成 **16/16**，峰值 RSS **313,413,632 字节**，全部精确上界与 producer 一致，三个真实证书篡改负控均按预期拒绝。报告为 `independent-cylinder-slab-all16-attempt1/report.json`。读取器从不可变原件重建完整 D、原根、分割树和所有原边界片；不导入 producer 或 CAD 内核。`R9_ENVELOPE_SCOPE.json` 与交付清单在该结果完成后生成。

**此结果只资格化这 16 个固定原域上的条件序列化源模型体积上界。** Native BREP 包含、filling、连续 native 包络拓扑、统一编译误差、完整机械允许域及 G2/G3/G4/G5 都没有因此通过。四类 L1 原失败仍逐项保留。

## 原预算与逐帧结果

原门槛严格保持为 `Fraction(1e-7)`，即
`944473296573929/9444732965739290427392` mm³。没有把它换成较宽的十进制近似。原正 tiny-box 阈值也保持不变，全部 **1,493 个正 tiny 节点**计入保守上界，没有当作零丢弃。

| 原 case | frame 1 上界 / mm³ | frame 2 上界 / mm³ | 当前 producer 原门槛 |
|---|---:|---:|---|
| 001 | 1.8943394070663295e-14 | 3.793469827035721e-14 | 2/2 |
| 006 | 1.9246042482697247e-14 | 3.8554187302266483e-14 | 2/2 |
| 028 | 4.151194516185377e-8 | 4.1511945517125275e-8 | 2/2 |
| 037 | 9.321533006737572e-8 | 9.321532924909036e-8 | 2/2 |
| 054 | 3.005784630472342e-15 | 6.2902684265234054e-15 | 2/2 |
| 063 | 8.302388007783139e-8 | 8.302387990463687e-8 | 2/2 |
| 072 | 9.321533029448826e-8 | 9.321532944834535e-8 | 2/2 |
| 089 | 4.3767635399126336e-15 | 3.7198667807024215e-15 | 2/2 |

原上限仍为全局 4,096 splits、depth 24、12,000,000 片测试、600 秒、805,306,368 字节 address space。RSS 与 address-space cap 是不同量。记录时间涵盖初始化、所有新根计算及完整证书序列化，采样发生在最终 report 写入前；没有把该记录冒充外部独立 wall-time 测量。

通过的具体含义是交集总体积上界不超过原阈值。未排除的格继续使用原正盒体积并计入总量；scope JSON 分列最终 leaf 的原 tiny、whole-box、cylinder/slab 与完全排除项，保留各自上界贡献。全树历史还含被后续分割的未决节点，不能与最终 leaf 数量混用。

## 为什么这次上界收紧

原八个未通过帧的重要损失来自相关性：一侧材料被原圆柱面限制，另一侧材料被原平面/直线投影限制，分别使用包围盒会丢掉两者共用的薄层约束。

本轮先在真实保留叶 `case-037/frame-2/root60/node671` 完整扫描原 12 条外出通道，发现原 cylinder face 0 与另一侧 plane 64、line 154 的组合。完整非零 D 保留后，这个体积为 `3.2314619085709764e-9 mm³` 的原格，取得上界 `8.973910713019907e-20 mm³`。该小型真实证据经过独立读取和篡改拒绝后，才进入整轮策略。

圆柱通道逐片核对完整原边界，验证所有未排除片属于同一原圆柱，且径向二次型沿完整外出通道单调。另一材料的完整通道给出投影下界 L。保存原基向量、原 D 和轴向区间，使用有理外舍入平方根求投影上界 U。交集于是被包含在原格 B 中的 `L <= n·x <= U` 薄层内。沿任一非零 `n_j` 轴积分给出保守体积上界：

`min(volume(B), max(0, U-L) / abs(n_j) * product(other box widths))`。

此值是上界，不声称等于切割多面体的精确体积。原格的正体积与分割守恒另行精确检查；“移除体积”字段仅表示已证明的移除量下界。完整推导见 `CYLINDER_SLAB_PROOF.md`。此处没有把一次有限 native Common 当作连续证明。

## L1 四类原反例的真实范围

`inherited-native-source-scopes/` 保存 27 份字节未改的 R3E 原证据，包含 17 个原 case result、25 个原 ValueError 的映射、实际修复/失败历史、独立审查及来源绑定。完整原科学归档为：

`RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027.zip`

SHA-256: `ebb5231bb6418a1da79b56f810d7759a947ec90cb07cefcb727910f924321fb5`。

| 原问题 | 保留的原失败 | 已有实际条件修复 | 本轮与未决 |
|---|---|---|---|
| 临时 prism 拓扑/有向体积，case 011–015 | 原 native signed volume 约 `-2.25663550699e-10 mm³`，正材料 guard 失败 | R3E 从完整原 source face 构造独立定向有理 carrier，检查闭合、方向及正有向体积；上界约 `1.51362766e-8 mm³` | 本轮按 hash 继承，未重建或资格化 native prism；原失败保留 |
| Common 上界，case 017–019 | 原 C 为 `0.16493361431346365` / `0.16493361431346365` / `0.051836278784231485 mm³`，原 min-volume-plus-TOL guard 失败 | R3E 使用完整 A-material 边界 carrier，上界为 `9.8401015111e-9` / `5.2066902075e-11` / `9.8401015111e-9 mm³`，旧 C 不作接受依据 | 本轮按 hash 继承；native Boolean 集合正确性与原 C 修复仍未资格 |
| EXTRUSION，case 016 | 原 unsupported advancing surface EXTRUSION | R3E 完整 affine-trim 斜向有理 sweep，在原四个位移条件下通过条件界 | 本轮按 hash 继承；一般 EXTRUSION、新 native swept BREP、统一编译误差仍未资格 |
| 极小位移与相关性，case 001/006/028/037/054/063/072/089 的双 frame | 16 次 finite nonzero displacement required；后续整根方法曾仅 8/16 | 本轮从所有原根、完整 D 新算 cylinder/slab 保守上界，producer 16/16，完整独立验收另存 | 原固定域的条件模型得到推进；native 包含/filling、源到安装二进制对应、完整真实允许域仍未解决 |

R3E 的旧 tiny 方法含“观测 base Common 是可靠上界”这一额外前提。本轮整根方法不使用该前提，不把旧 tiny 结论与当前证书混为同一次执行。原 12 次 degree-1 pcurve 超出末 knot 的源语义问题仍保存；对应安装二进制与舍入界没有新增证明。

## 失败历史、读取器修复及异常保存

`balanced-all16-attempt1/` 和 `gradient-all16-attempt1/` 均是实际完整执行、实际独立读回，均保留 **8/16** 的原门槛失败。前者 517.482501109 秒，后者 348.126441491 秒，各用完 4,096 次分割。新的成功不能覆盖这两次数据。`BALANCED_ALL16_BASIS.md` 中早期“1640 roots”笔误也保留原 bytes，并由 `BASIS_COUNT_CORRECTION.md` 明确更正为实际 1,537；执行代码一直枚举完整原根。

另修复了一个真实独立读取器缺口：旧 R8 数学检查器能证明一个宽泛二次型界保守，但旧 channel reader 没有强制其严格处于圆半径内侧或外侧。R9 在实际成功 channel 上构造“仍保守但分类 unresolved”的篡改：旧读取器实际接受，新读取器以 `strict_quadric_required_for_exclusion` 拒绝。旧数学界本身并未因该发现失效；缺口在把未决界当作排除的接受逻辑。

本次全量成功使用 `cylinder_slab_all16_r9.py`。真实小型控制已证明原子 split 在子节点构建失败时保留旧 committed tree。该 v1 仍有两个异常路径限制：提交后清空 pending 标记前中断，标签可能不精确；序列化中断时不能保证保存尚未输出的所有 committed frame。实际成功轮没有触发这两个异常。

另命名 `cylinder_slab_all16_r9_v2.py` 修复了 pending 标签与 recovery serialization。`RECOVERY_SERIALIZATION_CONTROLS.json` 真实注入第二个 gzip 写入中断，保留原截断文件、原异常，并独立读回两个完整 recovery payload；失败后资格始终为 false。**v2 未执行全 16 帧，v2 小型控制不回填 v1 不存在的异常资格。**

候选双通道优化的 7 份源码/依据保留为准备材料：`SELECTED_CYLINDER_SLAB_BASIS.md`、两个 selected 核心、`original_input_cache_r9.py`、selected pilot、selected producer、selected reader。它们没有实际 pilot、全量或性能资格。本次全 12 通道已在原预算内完成，按收尾决定停止可选新轮。

## 复现及交付

从仓库根目录执行；输出目录必须不存在。`--originals` 指向保持原 bytes 的 method 恢复目录。以下使用本次实际输入位置；若重建环境改变绝对路径，需按报告中的 SHA/bytes 重新绑定来源，不能静默改写已执行报告。

```bash
python -B engineering/engineering-followup-20261029-r9/envelope/cylinder_slab_all16_r9.py \
  --originals /workspace/scratch/36649508b53f/recovered/method \
  --output engineering/engineering-followup-20261029-r9/envelope/cylinder-slab-all16-replay

python -B engineering/engineering-followup-20261029-r9/envelope/read_cylinder_slab_all16_r9.py \
  --originals /workspace/scratch/36649508b53f/recovered/method \
  --producer-report engineering/engineering-followup-20261029-r9/envelope/cylinder-slab-all16-replay/report.json \
  --output engineering/engineering-followup-20261029-r9/envelope/independent-cylinder-slab-all16-replay
```

`R9_ENVELOPE_SCOPE.json` 是事实与范围投影。`R9_ENVELOPE_DELIVERY_MANIFEST.json` 为该目录全部交付文件逐个列出 bytes/SHA-256，包含三轮完整 16 帧 forests、全部实际失败、读取器结果、控制、源码和继承证据；清单仅排除自身及 Python 缓存。原 R8 完整证据与父任务管理的科学归档另保留。任何精简展示只作投影，不能替代完整 forests 或原失败记录。
