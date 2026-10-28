# R5 现场受理接口的作者阅读说明

这份说明由 `receive_evidence_r5.py` 的同一作者整理，供根或另一作者交叉阅读，**不是跨作者独立保证**。本次没有改写原程序、合同、已冻结的科学 ZIP 或公开投影，也没有追加泛化测试。

## 可核对的关键条件

| 位置 | 实际条件 | 能支持的结论 |
|---|---|---|
| `receive_evidence_r5.py` 的 `receive()` | 明确类别、相对原文件路径、无 symlink、同样件声明一致、实际 SHA／尺寸、可选预期身份 | 文件字节确实收到且元数据声明符合入口格式 |
| `receive_evidence_r5.py` 的 `run()` | 原合同及 V2 验证器固定 SHA 在运行前后相符 | 调用的仍是绑定的原结构验证器 |
| 原 V2 `validate()` 中的 `refs()` | 207 个 same_specimen 事实引用必须声明为 same_specimen_original，并与 packet 的 specimen_id 相同 | model_literature／synthetic_fixture 标签不能直接充当这些事实的同样件原件引用 |
| 原 V2 的 supplier 分支 | 21 个 selected_part_revision 事实检查引用存在以及来源定位／revision 字段 | 仅结构引用成立；程序不认证 OEM／供应商适用性或文字真值 |
| 原 V2 的 gate 事件检查 | 声明 physical 的事件、原 decision schema、候选／样件绑定、前序结束时间以及维修／换件链 | `reported_pass_sequence_structurally_valid` 是声明记录的结构与时序结果 |
| 两个程序的最终输出 | `original_evidence_authenticity_verified` 恒为 false；`physical_gate_pass.G3/G4/G5` 恒为 false | 无论文件类别或元数据如何，都不会由本接口颁发真实物理 pass |

已对两份实际源码做 AST 字面值读取，两个程序的上述物理资格输出确实是 false 常量；没有执行额外原件模拟来把这项静态阅读包装成新实物验证。

## 必须保持的解释边界

原 V2 对 selected_part_revision 的 21 项没有认证“这份文件是否真是所选 PN／revision 的 OEM 参数”。在该范围内，一个已核验字节的 model_literature 或 synthetic_fixture 可能成为**结构上可引用的文件**。如果调用者把 `structurally_present_requirement_count` 或 `review_ready_structure` 当作合格供应商资料数，就会产生错误解释。原合同明确不认证照片、采集人、样件身份、供应商适用性、物理执行或测量真值；这项边界没有被 R5 接收器消除。

相同地，文件内容中自报的 physical／pass 并不自动成为真实物理通过。原 V2 可以检查声明的 decision 格式与时序，但始终输出物理 pass=false、真实性=false。现场真实性、实际工程适用性和原物理 evaluator 的结果仍需原件及独立工程判断。

## 当前实际数值的准确表述

| 实际输入 | verified_original_bytes_count | structurally_present_requirement_count | missing 条目 | invalid 条目 | 物理门 |
|---|---:|---:|---:|---:|---|
| 原空输入 | 0 | 0／228 | 256 | 0 | G3/G4/G5 全 false |
| 官方快速指南作为 model_literature | 1 | 0／228 | 256 | 0 | G3/G4/G5 全 false |

因此应说“**收到 1 份型号资料；当前原 228 项事实仍没有结构上已绑定的值，真实性和物理资格均未建立**”。不能说“0／228 已被证明为真”或把结构完整性叫作测量合格。

256 个 missing 条目由 228 个事实值缺失和 28 个额外受理字段组成。后者包括 specimen、候选／几何／装配／功能提交标识、源码与原生载荷引用、7 个 part_binding、12 个端子表、模板状态和实际采集声明。完整原字段与缺失定位见配套 JSON，不把这两个计数混成新的 256 项工程指标。

## 尚需的原件输入

1. 原 a11 提交对象或包含该对象的完整 Git bundle。推送授权已有；原对象仍不可替代。
2. 同一样件的 10 个身份字段、7 类原件的 77 项事实、12 个接口的 120 项事实及逐端子映射；同时交原照片／日志、PN／revision、方向、实测读数及校准与不确定度。
3. 所选 OLED/COF、FPC、连接器和结构材料工艺的 21 项原厂／受控文件事实，逐项确认实际 PN／revision／lot 和参数条件，不能只确认有一份 PDF。
4. 当前候选源码／原生几何／装配版本与同样件绑定。当前 FE 还需逐体材料、13 类有来源载荷、9 类原占位体替换，以及接触、制造公差与全域最坏工况证据。
5. 原 G3 计划、as-built、G4 和 G5 计划的来源／采样／校准／阈值与实际执行数据。原模板分别仍有 24、30、118、61 个 null 字段；这些含重复来源及身份槽位，不能相加当作互不重叠的新验收指标。
6. 同候选同样件逐级真实 G3 → G4 → G5 原始时序与判定记录。未发生维修／换件时，空事件列表可以合法存在；不能为填表虚构事件。真实失败、缺测、维修和换件继续分开保留。

配套 JSON 保留全部 228 个原 requirement ID／描述、28 个额外缺失项、所有计划 null 字段的 JSON 路径，以及目前实际输出和源码身份。原现场计划中的 requirement 数组与原合同逐项相同，全部状态仍为 UNACQUIRED、值为 null、引用为空。
