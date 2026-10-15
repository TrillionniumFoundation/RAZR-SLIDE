# 严格 signed-volume 运动复算，2026-10-13

本目录修复已发现的软件证据缺口：`cad-review-20261013/cad_motion_audit.py` 仍调用历史 `r40_occ.intersectvol`，它在验证参与体之前先作含 1e−9 容差的 AABB 剪枝，且没有检查原始 signed common。历史报告与模型保留；本轮不改变 R44/R45 研究几何，不改 A/B、OLED、导轨或原厂部件，不将旧 numeric receipt 追认为已经运行新守卫。

完整入口是 `strict_intersections.strict_common`。每个参与体先验证 valid、有限且严格正 signed volume、一个实体；历史 Boolean 产生的单实体 Compound 只允许每层恰有一个 direct child，最终为完整 Solid。不能过滤掉额外 Wire/Face/Edge/Vertex 后冒充单实体。容差必须有限且非负。仅有严格正轴向 AABB gap 才可剪枝；零间距、微小重叠均进入 OCC Boolean。每个实际 common 保留原始 signed volume，并检查非负及不超任一参与体体积加 1e−7 mm³ 数值容差；任何负值，包括 −1e−15，都不能 clamp、abs 或解释成净空。

`occ_signed_volume.py` 是旧 guard 的精确 SHA 副本（`5c227c88574ebb651a25736d9e320d23d0cbf1422cfffb02917694bd541c77b8`），供原始数值合同复用。完整 Compound 和剪枝前验证由新增入口执行，不能跳过它直接调用旧 helper 并称为同等审计。`source_provenance.json` 锁定已发布 de3 基线、原 builder、旧报告和源 manifest。build/obstacles/frame 函数逐字保持不变。

| 实际执行范围 | Cloud | X230 |
|---|---:|---:|
| 完整原生运动程序 exit | 0 | 0 |
| 121 位姿 × 23 障碍 | 完成 | 完成 |
| 3 易轴负例 × 23 障碍 | 完成 | 完成 |
| 总参与体配对检查 | 2852 | 2852 |
| 真正执行 OCC common | 262 | 262 |
| 已验证参与体后严格正 AABB gap 剪枝 | 2590 | 2590 |
| 硬轴研究形态 kernel common > 1e−6 mm³ 的位姿 | 0/121 | 0/121 |
| 旧 6 STEP 的正体积单实体叶 | 138 | 138 |
| 程序报告耗时 | 520.342 s | 1065.483 s |

X230 使用已存在的源缓存和其自身上一轮六份 STEP，在新专用目录执行。252 项源输入、原 STEP、旧 receipt 和运行源码前后 SHA 全部相同；`X230_full_operator_status.json` 记录真实 durable job native exit 0、完整输出与未截断日志。两台机器使用同一冻结算法和 CadQuery 2.7.0/OCP 核心；这是两机同源复算，不能代替独立物理模型或台架验证。

最终 `X230_semantic_comparison.json` 比较 62705 个数值、全部 2852 配对的参与体/原始 common/剪枝方法/容差、全部位姿长度/体积/截面帧、三负例、STEP 体积/边界/面积/质心匹配，以及完整 transferred payload 的 138 个 Solid 叶。实际最大数值差 0.0，比较容差 1e−5；布尔和整数严格分型，双方 `candidate_go`、`manufacturing_go` 和连续运动资格声明均检查。仅排除环境、耗时、各机旧 serialization SHA 及 `imported_part_index` 标签；叶体积数组仍按 transfer 顺序比较。

本轮没有重算四个主障碍的精确最短距离。它们仅引用旧 receipt SHA `fc2a786921be8c2c9be03b0811112b78b29d5bc9edb12e3ee9f3210167557b4e`；不能将引用包装成新执行。原未切削 B 的 AABB 距离下界为零，也不能解释成正净空。六份已有 GHOST STEP 按原 SHA 重导入、正 signed volume 检查并配对体积/边界/面积/质心，不另交重复 serialization，也不称这些量相同就证明拓扑身份。

`verify_step_payload.py` 检查 `.vals()` 的所有 transferred roots 并递归 Compound direct children，拒绝所有 free 非实体叶；没有先 `.solids()` 再检查。实际带独立 Wire 的 STEP 反例证明过滤式导入会默默只剩一个 Solid，完整 parser 会拒绝。这里的证明范围是全部成功转移对象；CadQuery importer 不核验逐个 `TransferRoot` 返回值，不能冒称 STEP 每个声明实体均已成功转移。

数值分辨率反例必须保留：`UNCERTAIN_subtolerance_overlap_counterexample.json` 的两个单位盒由独立区间公式得到约 1e−8 mm³ 正交叠，OCC 返回 0。signed guard 接受该 kernel 零值，因此它解决坏数值与验证绕过，不能证明任何尺度都无交叠，更不能提供物理接触/公差资格。易轴 STOW 的 OLED kernel 交叠仍为 2.0030464 mm³；三代表姿态下侧 Z 超预算仍约 0.35 mm。真实反向实体、有效且 Volume 为正的 Wire、多实体 Compound、重复既有 Wire、零间距触碰、非法容差等 14 个测试已通过；完整 payload 另 3 项测试通过。

人工失败 STEP 的首次 Cloud 字节存在明确留存缺口：根代理独立重跑旧导出测试时覆盖了它，首次准确字节与 SHA 没有可信副本。没有反推或重构它。当前 `ROOT_REVERIFY_solid_plus_loose_wire.*` 是那次 17 项 native exit 0 重跑的精确变体；`witness_regeneration_provenance.json` 如实记录此事，旧测试精确源码保存为 `historical_full_step_payload_test.py`。X230 有自身独立、SHA 验证的对应 STEP 变体。六份原 GHOST STEP、728 份原始材料、冻结几何和 121 位姿主报告均未受影响。当前 `test_full_step_payload.py` 已改用 `TemporaryDirectory`，3 项实际重跑 exit 0，证明不会改动研究 witness；`corrected_test_native_receipt.json` 绑定新源码 SHA。历史测试只有在物理复制源码到隔离目录后才可运行，仅换 cwd 不足以隔离它的写入。

复现时使用可信源 manifest 和新输出目录：

```bash
python -B cad_motion_audit.py --minimal-source --cache /verified/source/cache --prior /prior/audit-with-source-and-cad --out /new/output
python -B -m unittest -v test_strict_intersections test_full_step_payload
python -B verify_step_payload.py --prior /prior/audit-with-source-and-cad --out /new/full_step_payload_validation.json
python -B compare_machines.py --peer /actual/peer/strict_motion_audit.json --peer-step /actual/peer/full_step_payload_validation.json --out /new/comparison.json
```

本轮仅闭合可计算的软件验证缺口。FPC 仍未真实端接并释放应力；材料层叠/宽向动态弯曲许可、原厂 OLED/COF 和 OEM 引出 CAD、连续同步运动、公差/受载变形、机械失效安全与电气/OLED 实物资格仍缺证据。原产品约束保持不变：两舱同尺寸、单块约 7 英寸柔性 OLED、79.75 mm 上滑、8.2 mm 法向就位、A 优先大电池。`candidate_go=false`、`manufacturing_go=false`。
