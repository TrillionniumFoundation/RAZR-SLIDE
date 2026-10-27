# L5d：原始 null Boolean 的六次构建诊断

本分支只定位 L5c 已保留的第一个失败 `cut`，并评估具名状态包装器 `raw_boolean_status_l5d`。它没有修复原报告，没有把 null 拓扑替换成空材料，没有执行原七个实体对或 current 七个实体对，也不证明连续包含、11,781 全对、真实 15 维域、K3 或实物合格。

## 实际起点

L5c head `f544f33c563ef4a44e8baa38c3e1225ad6e60b9e`、run `40468054101`、artifact `12717347119`。完整科学 ZIP 为 128,633 字节，SHA-256 `71f96228c6f8f5e3cbcb5ddb1f44d76ecb3cbf635bcd6e71eac7ba4c36aaa49a`。独立内存读回已经核过全部 52 个 manifest 成员及 manifest、每个 CRC、字节数与 SHA。原报告、8 个原几何文件均按绑定复制；两份失败的 STEP 及两个实际读回 root 都保留。

原完整 BREP 是有效 Solid，1 solid、10 faces，有向体积 `4.453452962600495e-10 mm³`。`t=0.25` 平移后仍是有效正实体。原直接 subtract 和单独拆开的 trace 都在第一次 region 0 `cut` 失败，尚未进入 clean 或体积门。完整体 STEP 导入得到有效 Shell、0 solids、6 faces，被原 `p.single` 拒绝；face STEP 导入得到无 faces 的无效 Shell。Shell 的 raw mass accessor 不是已接受的实体体积。

官方 [CadQuery v2.7.0 shapes.py](https://raw.githubusercontent.com/CadQuery/cadquery/v2.7.0/cadquery/occ_impl/shapes.py) 的 183,973 字节 SHA `48331311a0e6de8dc324c3bf76e4ed3c3769f47d007a0243ac25f454cc22bb47` 与实际锁定运行依赖逐字节一致。其固定异常常量 `Null TopoDS_Shape object` 的 24 字节 SHA 为 `6ec2e46348dbe80afad13cbcb89fd614c1d61a7905475c9e817ca619cd0b3d5c`，与两个原失败相符。原 wrapper 在 Build 后直接 cast Shape，没有先检查 IsDone 或 HasErrors。

[OCCT 7.8.1 BRepAlgoAPI_Algo.hxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_1/src/BRepAlgoAPI/BRepAlgoAPI_Algo.hxx) 明确 Shape 本身不检查是否建成；[BOPAlgo_Options.hxx](https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_1/src/BOPAlgo/BOPAlgo_Options.hxx) 的 HasErrors 查询 Fail alerts。这些源码支持检查状态的必要性，不证明当前 null 是合法空集。

## 固定六次构建

1. 原 CadQuery `a.cut(b)` 再现，原失败和固定异常 hash 单独记录。
2. 同参数底层 `BRepAlgoAPI_Cut`，保留实际 Build、IsDone、HasErrors、HasWarnings、GetReport 与 Shape。
3. 同一原材料的底层 Common，仍执行原正向有向体积及 Common 上界门。
4. 反向 Cut，提供对称算子观察，不作为原失败的替代结果。
5. 完整单位 box 被较大 box 包含的合法空 Cut 控制。
6. 两个分离单位 box 的非空 Cut 控制。

每个真实材料操作都重新从冻结 BREP 导入，不复用上一次 Boolean 后的对象。原默认参数不改，不增 fuzzy tolerance、不改 non-destructive 或 CheckInverted。实际参数单列，原 wrapper 的 RunParallel=True 保持。每个实际底层操作后的两个输入 BREP 单独保存，后续仍重新导入原文件。

null 只记录为 `null_result_not_accepted`，不 cast、不生成空 Compound、不赋零体积。非 null 结果也必须经过原 whole_material 的 valid/signed/完整拓扑门。Build 未完成或 HasErrors 时，即使有结果形状也不能当成成功材料。GetReport 只输出受控类名和计数；未知异常文本只留 hash 和字节数。源追踪明确区分 S4 Git 源、锁定依赖字节和新诊断源码。

合法空控制要求实际非 null、原门接受的 0 solid/0 volume 结果。未知 ValueError、null、invalid Shell 都不能借用这个分支。普通非空控制要求原正实体和原 `1e-7` 体积差门。原七实体对的完整 Common 总门仍未执行，也没有被替换。

## 容量与退出

L5c 完整 worker 实测 4.114908292 秒、峰值 RSS 517,107,712 字节，第一个失败 cut 0.086183886 秒。本次据此登记小规模六次构建；没有承诺未测算子的完成时间。原 worker 1800 秒、1536 MiB、共享内存 6.8 GiB、起始盘 200 MiB、运行盘 100 MiB、host 2220 秒、job 40 分钟和拥有子进程的全部生命周期守卫保持。

新增最多 32 个几何文件、8 MiB 保存后停止上限、4 MiB JSON。8 MiB 在 native 保存后检查，可能超出一个文件，不能称写前硬上限。输出保留仍受原磁盘、RSS、wall 监督。每个 gravity 最多 32 alerts；超限和无法完整提取均保留未决。

`execution_completed` 表示六次受限调查到达末尾；所有原门的结果独立保存。原直接 cut 或任何所选原门失败，worker 仍 exit 2，workflow 保留红色；always exporter 和 upload 仍保存可用科学原件。`original_null_failure_repaired` 与 `conservative_continuous_containment_proved` 明确为 false。新 wrapper 目前只让原失败更明确，不能据此启动或声称原七对通过。

本地检查仅验证新源码、实际嵌入的 transport、受控 exporter 和失败保留。没有本地 CAD、没有改 S4、没有公共 raw runtime。
