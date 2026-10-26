# XT2551-3 正式只读采集与部分身份导入

## 真实来源

采集发生在 **2026-10-20 02:59:58.946837 至 02:59:59.249960 UTC**，执行位置为 Pocket4 已有的独立 Git checkout，源码提交为 `f4db100cb62c0ac492118bf605b0e9e7ac7cce32`。

原件位于 [身份记录目录](../../hardware/records/xt2551-3-20261020-f4db100-identity)。采集文件为该目录的 `raw/formal_readback.json`，SHA256 为 `28fb380ee5d992893f248241b8bde70825b62057851d7d956ea060b66fe44702`。导入记录 SHA256 为 `b4200d53ab68ec95733eb00d26b3e53ee35a3055d448c8b70d81b024910cad7f`。

| 项目 | 实际结果 |
|---|---|
| 型号与 boot SKU | XT2551-3 |
| 设备身份 | serial SHA256 `41ad305f8562a6c47710afe71fabf30cb8692a71d3de1a47ca9949b669bcc6c1`，与此前 USB/ADB 观察相同 |
| ADB 服务 | `127.0.0.1:5061`，已有进程 PID 1846357，起止 boot ID / PID / start ticks 一致 |
| 设备 transport ID | 起止均为 37 |
| ADB 二进制 SHA256 | `00108217733707a40debfc92c86d4232fd6e68870be5966515d74c071193ea90` |
| 采集器 SHA256 | `b2dada86400ec43ba1ace3a02b657fcf6790744656a4bfb8f322b4bcd091b351` |
| 原始命令 | 17 条，全部 return code 0；每条均记录 `-H 127.0.0.1 -P 5061` |
| 设计身份 | 起止不变，两份工作输入均与上述提交的 Git blob 相同 |
| 运行时 | 自定义 Android 17，`leap`；原始 fingerprint 完整保留 |
| 硬件版本属性 | `ro.boot.hwrev` 返回空，保留 null |

首次外围预检脚本因 PID 正则转义错误未识别已在监听的服务，因此在执行任何 ADB 命令前停止。原始 `preflight_parser_failure` 记录保留；修复外围解析后才执行上述正式采集。该首次预检错误不代表服务或 donor 不存在。

## 导入确实执行了什么

现有 `import_hardware_evidence.py` 实际导入 5 份原始观察，保存其原字节、导入清单和两份设计输入。传输前后每份 SHA256 相同。导入器没有改配置；随后采用其叶级建议，更新 `donor.model` 和 `donor_evidence.identity_record`，并把旧默认端口空观察保留为历史主机／时间范围。

`physical_execution_occurred=true` 在此记录中指**真实只读设备采集发生过**。记录明确保留 `platform_frozen=false`、`physical_phone_verified=false` 和制造相关 false 标志。

导入后的独立核对实际通过：原件记录可读且哈希完整，`observed_record_compatible=true`，接口语义哈希未变；当前 donor 值与记录相同。`donor_identity_bound=false`，12 条接口的 `terminal_evidence_bound` 全部为 false。

新增 ADB 传输字段与服务进程稳定性由本轮执行回执额外核对。原有导入器的 `readback_trace_consistent` 不强制验证这些新字段；也不能把 `donor_identity_bound=false` 自身当作原件完整性检查。导入器允许如实声明的工作输入差异，本轮另行实核 `inputs_match_commit=true`。

## 确认与未确认的范围

实际采用的身份字段只有 **model**。以下 10 项仍为空：region、mainboard_revision、runtime_panel_id、display_module_part、display_module_revision、touch_revision、pack_A_label、pack_B_label、USB_roles、USB_version_rate。

带原始标签的实物库存为 0；缺少 mainboard、display、touch、COF、pack_A、pack_B、USB_port_board 共 7 类角色。端子、尺寸、受保护电池的项目 A/B 对应、动态材料资格和新整机功能均未验证。

此前 [Pocket4 模组软件观察](../../phase2-20261019/hardware/pocket4-20261020/README.md) 仍适用其原始时间和采集范围：软件设计值为 3430 / 1140 mAh，合计 4570 mAh；匹配型号的中国 OEM 手册典型值 4700 mAh、额定值 4540 mAh。软件设计值与 OEM 额定值相差 30 mAh，原因未确认。它们不能替代两块实物电芯标签、原保护拓扑、项目舱位对应、容量实测或新布局的空间证明。
