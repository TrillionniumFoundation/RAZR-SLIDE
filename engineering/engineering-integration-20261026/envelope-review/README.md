# L2/L3 独立工程读取与 V4 后续接口

本目录按独立阶段保留结果：L2 首轮 run 40273642963 在准备期失败、0 次 native；修正配置后的 L2a run 40274339675 完成 89 个原调用（19 个不同实体对），仍为 4 clear / 85 unresolved carrier overlap；L3 run 40274745040 另用相关性方法执行 70 个原调用（8 个不同实体对），70 clear。组合对照余下 15 个原调用、9 个不同实体对，不是一次全量通过，也没有改写 L2a 报告。

`scientific/` 中的 report、MANIFEST、CONTROLLER_OUTCOME 是实际四个科学 artifact 的逐字节原件。完整科学 ZIP 和 carrier BREP 的 identity 由 `SAFE_ENVELOPE_RESULT_INDEX.json` 绑定；此合入不重复保存这些二进制文件，也不声称远端持久归档已经成功。

两个 ALL89/ALL70 文件和容量观察文件为带明确 wrapper 的派生工程投影：`engineering_record` 保留全部科学字段，仅删除原记录的本地 ZIP/旧归档定位字段；原记录字节数、SHA256 和具体删除字段在 wrapper 中。它们不会覆盖私有原记录。`analyze_l2_science.py` 与 `analyze_l3_science.py` 是实际独立读取代码；本次只读验证 hashes、材料身份记录、原 source/postguard 和 Common 总和，没有另行 CAD 读回或第二内核验证。

L2 全部原 postguard 保持通过；85 个正 carrier Common 继续 unresolved。case-014 的 1.2793811944413415e-7 mm³ 仍高于原 1e-7 门槛。L3 的 70 个 native carrier 总 Common 都为 0，同时 70 个穿透负控制为正；这不构成全部动态允许域、力学或实物资格。V2 直接 EXTRUSION 专项分支与数值 bounds 的严格区间包含仍没有证书。

完整 L2/L2a/L3 方法、driver、supervisor、binding、原测试/检查、README 和 workflow 的 19 个冻结源码位置及逐字节 SHA 在 safe index 中，可从已发布 commit 复用。首轮 L2 错误 source-tree literal 的失败记录保留在相邻 `envelope-L2/L2_FIRST_RUN_PREPARATION_FAILURE.json`。

V4 的源码、schema、六项纯检查和原 11,781 对历史容量分析是后续研究准备。尚未执行 V4 native，更未跑 K1 全量 SLIDE。容量阶段只能在实际 K1 双姿态完整 producer/reader clear、冻结材料 binding 和 loader 通过后启动；原域、1e-7 总体预算、有效拓扑、有向体积、4,096-region cap 和资源门槛继续保留。相关性的证明范围、native 数值界限、每 case 新方法耗时缺失和九分片备选的条件见 `FULL_SLIDE_INTEGRATION_PLAN.md`。
