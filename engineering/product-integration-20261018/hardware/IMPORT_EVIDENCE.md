# 实物采集、原始证据导入与同一版本绑定

这是可执行工具的输入约定。当前没有借这些工具产生真实 donor 料号、针脚、尺寸、容量或手机功能通过记录。`integration/product-study-tests/test_hardware_evidence.py` 中的全部样例是临时目录内的 **synthetic unit fixtures**，不会进入实测证据目录。

## 1. 先采集可识别的实物与设计身份

给实际拿到手的整机或匹配模组组分配一个稳定的 `specimen_id`，标签照片、量测、端子表和运行日志共用它。它不是 Android 序列号。使用当前仓库执行：

```bash
python3 tools/read_donor.py --specimen-id YOUR-ACTUAL-SPECIMEN --output engineering/product-integration-20261018/hardware/observations/NEW-SESSION/adb-readback.json
```

有多个已授权 Motorola 设备时增加 `--serial`。输出文件必须是新文件。工具保留每次 ADB 命令的参数、返回码、原始输出文本、超时/错误和耗时，序列号替换成 SHA256；读取结束再次检查连接。读取中断时保留已完成的属性和失败命令，不将它记为完整读取。返回码 `2` 包括未选择到设备、读取失败、读取结束已掉线或设计输入改变；原因以 `capture_status` 和 `command_records` 为准。返回 `0` 只表示软件身份读取完成且设计输入未改变。

v2 的 `design_binding` 同时记录 Git HEAD、两份设计 JSON 的实际字节 hash、该 commit 内的文件 hash，以及 `inputs_match_commit`。因此未提交的设计修改不会被写成“该 commit 的原样设计”。`collector_sha256` 与 `interface_contract_source_sha256` 分别标识实际采集器和接口语义 hash 算法的源文件。物理模组、尺寸、端子和手机运行完成状态仍然不从 Android 属性推断。

从同一个工作区取得导入所需的完整绑定对象：

```bash
python3 engineering/product-integration-20261018/hardware/import_hardware_evidence.py --print-binding
```

将原始采集时的完整对象保存到测量 manifest 的 `design_binding`。历史记录可以在仅增加说明文字之后导入，但该源 commit 必须真实存在，其已提交文件 hash 必须正确，当前两份设计输入的实际字节也必须与记录相同。不能把旧测量的 commit 手动替换成最新 HEAD。更换几何、布线路径或接口合同后应建立新记录，原记录保留。

## 2. 一个导入器，四类真实记录

导入命令如下；输出必须是仓库内尚不存在的目录：

```bash
python3 engineering/product-integration-20261018/hardware/import_hardware_evidence.py --manifest /path/to/actual-session/manifest.json --output engineering/product-integration-20261018/hardware/records/NEW-RECORD
```

共同输入字段：

| 字段 | 内容 |
|---|---|
| `schema` | `razr-hardware-import-v1` |
| `record_type` | `donor_identity`、`terminal_map`、`dimensions` 或 `phone_function` |
| `is_template` / `physical_execution_occurred` | 实际观察发生后分别为 `false` / `true`；模板和计划不会导入成实测 |
| `specimen_id` | 实物编号；更换整机或匹配模组组时建立新编号 |
| `recorded_at_utc` | 带时区的实际记录时间，例如 ISO 8601 格式；不是运行导入脚本时自动补造的测量时间 |
| `measurement_method` / `operator_or_instrument` | 实际方法、记录人员或仪器身份；不能只写“通过” |
| `design_binding` | 上节完整绑定对象，保留原始 Git 与工作区差异 |
| `observations` | 原始文件数组，每项含 `id`、`kind`、相对 manifest 的 `path`、原始文件 `sha256`；实物观察还须有同一个 `specimen_id` |

`kind` 接受 `physical_label`、`physical_measurement`、`manufacturer_document`、`device_readback`、`instrument_log`、`operator_observation`。除厂商通用原始资料外，每个附件都必须声明所属实物。附件路径不得逃出 manifest 所在目录；附件内容必须与事先记录的 hash 相符。

输出包括原始文件的逐字节副本、原始 manifest、两份精确设计输入、`record.json` 和 `proposed-config-update.json`。源文件后来被移动或覆盖不会改变已归档记录；归档副本后来发生变化则使绑定失效。导入器验证关联关系和记录的一致性，照片/规格是否真实、标签是否读对仍须由操作者核对。hash 自身不证明测量真伪。

### 2.1 `donor_identity`：标签和设备必须属于同一套实物

额外字段为 `device_readback_observation`、`field_evidence` 和 `part_inventory`。

`device_readback_observation` 指向 v2 ADB 文件的 observation ID。导入器读取该原始文件，验证完整命令轨迹中的型号和属性与摘要相符、最终设备仍在、实物编号一致、原始设计 commit 和输入字节一致。型号还必须与 `ro.product.model` 的实际输出一致；同型号的另一台设备不会通过后续运行日志的序列号摘要比对。

`field_evidence` 的键是 `design/product_interfaces.json` 中的 donor 字段；每个已知项是：

```json
{
  "value": "实际读到的字段值",
  "observation_ids": ["对应原始附件的ID"],
  "locator": "照片中的位置、规格页码/表行或原始记录位置"
}
```

未知项不填写，导入器保留 `null` 并列出缺项。主板修订、显示料号/修订、触控修订和两块电池标签必须引用实物标签、实测或原厂资料，不能引用软件属性来替代。软件中出现的驱动家族名不成为 COF 料号或连接器针号。

`part_inventory` 为实物部件数组。每项含稳定 `part_id`、`roles` 数组和上述格式的 `label`。主板、显示、触控、COF、A/B 电池、USB 端口板对应角色分别为 `mainboard`、`display`、`touch`、`COF`、`pack_A`、`pack_B`、`USB_port_board`。集成在同一个实物上的多个角色可放在同一 `roles` 数组中；不为满足清单而编造独立 PCB。任何角色缺失都会明确列在结果里，不形成完整 donor 绑定。

建议更新文件只给出已观察 donor 字段和 identity record 的引用。应将这些字段合入原配置，保留其他 `donor_evidence` 内容；脚本不会修改配置，也不会自动把 `actual_donor_selected` 设为 true。完整 donor 绑定仍不等于所有接口、尺寸、空间和手机运行已验收。

### 2.2 `terminal_map`：逐个板端、连接器和端子关联

先将已复核 identity 的值和引用合入配置。端子 manifest 的 `donor_identity_record` 必须等于该配置的 path/hash 引用，`interface_id` 必须是现有接口 ID，`terminal_csv_observation` 指向原始端子 CSV。

CSV 列名：

```text
net,source_connector,source_pin,sink_connector,sink_pin,observation_ids,locator
```

多个证据 ID 在单元格内用 `;` 分隔。CSV 是操作记录，不替代用于识别端子的原始照片、显微图、规格页或测量输出。每行的 `locator` 要能找到原始观察位置。

manifest 的 `connectors` 是按连接器 ID 索引的对象；每个连接器包含属于已观察部件清单的 `part_id`、实物上识别出的完整 `observed_pins` 数组以及 `label` 证据对象。连接器 ID 必须能区分板端，例如将稳定部件 ID 纳入名称，不在所有板上都只写 `J1`。

导入器对比每个源端/目的端是否存在于观察清单，拒绝把一个实体端子同时赋予相互冲突的网名。所有观察到的引脚都必须由记录覆盖，才能得到该观察清单范围内的完整绑定；未映射的引脚逐项列出，不能删掉真实引脚来消除缺项。当前版本不支持将未解释的 NC、混合接口、分叉或屏蔽接触默认为已解决；遇到这些情况应保留不完整结论，再按原始端子结构扩展明确的模型。

建议更新文件包含保持原顺序的 `actual_pinmap` 和新记录引用。`extension_approved` 始终为 false。真实针脚被绑定仅说明连接身份已有原始依据，不证明新增延长件的供电能力、阻抗、信号完整性或动态弯折能力。

### 2.3 `dimensions`：把尺寸原始数据导入成可引用值

额外字段为 `coordinate_frame` 和 `measurement_csv_observation`。CSV 列名：

```text
part_id,quantity,value,unit,uncertainty,observation_ids,locator
```

`value` 和 `uncertainty` 必须为有限数，后者不能为负。单位支持 `mm`、`g`、`deg`、`mm2`、`mm3`；坐标允许负值。必须说明原点、坐标轴和基准面。外形、元件高度、连接器出口、极耳和保护器件应有分别可定位的行；未测到的量不要写零。

导入器规范化数字、单位和原始证据引用，保留完整 CSV，不自动移动现有 CAD 占位体或宣称真件装配通过。CAD 中对应的部件替换和全部状态复核是后续使用这些测量的步骤。

### 2.4 `phone_function`：原机基线与装机运行记录

额外字段为同一个 `donor_identity_record`、当次的 `device_readback_observation`、`timebase_id` 和 `function_csv_observation`。当次 readback 必须属于 identity 所绑定的同一设备；不能将另一台同型号手机的显示录像与本样机的 USB 日志拼成一次成功。

CSV 列名：

```text
time_s,phase,function,reported_outcome,metric,value,unit,observation_ids,locator
```

`time_s` 是同一时基下从实际记录起点开始的秒数，必须单调不减。`phase` 写原机 baseline 或实际动作/姿态。`function` 支持 `display`、`touch`、`power`、`usb`、`camera`、`rf`、`audio_sensors`。`reported_outcome` 仅接受 `observed_ok`、`observed_failure`、`not_observed`。数值没有测到时 `value` 留空；数值不为空时需同时填写 `metric` 和单位。

记录必须链接实际画面/触控测试记录、仪器输出、USB 传输日志等原始文件。导入器保留失败、时间范围和记录到的功能/姿态，不把稀疏的状态点填成连续采样，也不把操作者填写的观察结果提升为整机资格结论。机械位移、力和 FPC 阻值的时序分析使用同一个 `specimen_id`、设计输入和命名时基与本记录关联。

## 3. 旧记录、新结论与实际边界

`razr-observed-donor-identity-v1` 和 `razr-physical-terminal-measurement-v1` 仍可由原读取入口校验原始 path/hash，历史记录不会被删除。它们缺少新增的实物与版本绑定，不会再被用于建立新的 `actual_donor_selected` 或 `physical_terminals_bound` 结论。需要回到原始附件补全 v2 记录，不能仅修改 schema 名。

接口合同 hash 排除证据指针、是否选中 donor 和声明针脚表，避免“把记录 hash 写回配置又使记录 hash 失效”的循环。donor 字段另与 identity 逐项相等比较；针脚表另与 terminal record 逐行比较；几何字节必须相同，归档接口 JSON 的语义也必须相同。改路线、结构、材料声明或接口设计会使旧物理绑定失效，而单纯挂入已有记录的引用不会失效。

导入器的 `candidate_go`、`fixture_fabrication_go`、`manufacturing_go`、`physical_phone_verified` 全部保持 false。它交付的是可追溯的真实观察链，不代替实物的制造、测量或工程验收。
