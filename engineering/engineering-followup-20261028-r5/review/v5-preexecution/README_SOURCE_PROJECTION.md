# V5 来源投影的独立读回：只验证来源，不授予几何资格

独立审核已确认 `R5E_V5_PLANAR_TRIM_SOURCE.json.gz` 的来源投影保留了所有选中的完整原 face 字段。原 native inventory 的 53 个唯一材料记录中，V5 投影所需的 32 个材料对应原 16 个 case/frame；40 个完整候选 face、80 个候选 inner wire 与原记录逐字段一致。原 pcurve、参数、方向、location、tolerance、各 face canonical SHA、完整 boundary canonical SHA 及输入 BREP 身份均对应。

| 来源 | 字节数 | SHA-256 |
| --- | ---: | --- |
| 原实际 native inventory JSON | 65,374,048 | `f1c6bcb76d32f9dead19296ff37a64805eff59a8bcc4f696f99cc5821c370c5d` |
| 新投影 gzip | 35,630 | `bc778c13f9efbc280bcb93e59edbc821d2a7b751f0b8730231d1b0bd855e2804` |

原 inventory 的身份与已发布 R4 report 的 `input_identities` 一致。所有 frame 的 moving/fixed 材料侧、whole BREP 字节身份、原 proof 身份和完整 D 都已对应，没有交换两侧或使用静止截面替代原 D。

审核先登记 90 秒、384 MiB RSS／地址空间、1 MiB 输出预算，再执行独立标准库程序。原 inventory 只解析一次；16 个 R4 gzip 文件只解码各 16 KiB 的输入头部，合计 262,144 B，未重新解码全套 support proof，更没有重跑 R4 数学证明或 native worker。实际用时 **1.093092 秒**，peak RSS **174,891,008 B**，预算满足。

`audit_v5_source_projection.py` 没有 import 或执行投影作者程序、V5 producer、checker、driver 或 CAD。候选筛选使用四条轴向 line pcurve，只是来源分类条件；本审核没有把它解释为有效矩形、完整闭环、原生 trim 内外分类或保守几何替换的证明。

**V5 数学／解析控制执行数量为 0。** 后续 worker、checker、driver 和锁需要在最终稳定版本上作另一次源级复核；实际 CI、原资源门、完整 roots／树、完整位移、几何包含和原阈值也需要各自证据。本来源读回不改变 V4 的真实失败，不把 V4 的 12 个实际负对照计入 V5。

机器报告 `R5_V5_INDEPENDENT_SOURCE_PROJECTION_AUDIT.json` 保留逐材料、逐 face、逐 frame 的具体身份，预算文件绑定独立审计源码。`native_trim_class_membership_verified=false`、`full_continuous_G2=false`、`all_blockers_closed=false`。
