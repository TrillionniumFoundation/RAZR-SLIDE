# A 头部退让 / KEY 闭口槽：独立 STEP 回读说明

脚本：`read_ep4_a_relief_step_independent.py`。仅在 scratch 编写和做语法/入口检查；本说明不表示已执行 STEP 回读。实际几何读取由父任务在原生环境中执行。

## 输入与运行

同一个脚本分别读取两种已完成的原生报告：

- A：`E4/a-head-relief-9a8307f/report.json`，schema 为 `razr-ep4-A-head-local-relief-v1`。绑定退让脚本 SHA `04ba12fd1c3d58acdcfd8de039a8e7cca72dec29762834ffb6105deb6ffddcda`，以及冻结 EP4 模块和配置。
- KEY：`E4/key-local-study-9a8307f/native/native-report.json`，schema 为 `razr-key-endcap-local-native-v1`。绑定研究脚本 SHA `6c6b1fb9b5affd36a6d3d5848ff2dd20c0856409ad599019eabd64653eedaa90`，逐项核对原报告绝对路径 `source_sha256` 字典。

两项基准 N 为 `9a8307fe4bd4163b53515698fb12cfc0a8cc27e7`；运行时分别记录原报告中的实际提交与回读时观察到的仓库 HEAD，核对实际源文件字节。默认 `--mode auto` 按原报告 schema 判断；也可显式选择 `--mode a-relief` 或 `--mode key`。模式与 schema 不符时失败。

必填参数：

- `--manifest`：上述已完成的原生报告完整路径。
- `--repository-root`：包含冻结源码及 P3 独立 reader helper 的仓库路径。
- `--output`：尚不存在、位于仓库源码之外的结果目录。

若原生报告记录的退让脚本绝对路径已不可用，可以用 `--relief-script` 指定迁移后的同字节副本。其 SHA 必须与原报告及已审脚本一致；不允许靠改路径绕过字节身份校核。

输出为结果目录中的 `report.json`。成功返回0，检查失败返回1并保留原因；输出目录必须是新的。脚本不会修改冻结源码或输入 STEP。

两种输出统一包含 `execution_completed`、`declared_readback_checks_passed`、`failures`、`retained_input_files`、`native_source_commit`。`retained_input_files` 为绝对路径到读取前的字节数 / SHA 的字典；完整读取后的对应清单在 `input_files_after`。

## 实际覆盖

| 原报告 artifact | 回读检查 |
| --- | --- |
| `complete_endpoint` | 必须保留声明中的20个源参与件；展平后的20个正体积有效实体，对全部按名字记录的原指标进行匿名一一 bounds/volume 匹配，同时匹配export分量表与整体指标。重复螺钉不能共用一个观测实体。 |
| `removed_material` | 回读全部正体积分量；数量、一一指标、整体范围/体积和SHA均与原报告比较；总去料量另外与材料账比较。 |
| `explicit_head_clearance_tool` | 回读1个正体积工具实体；比较原指标和SHA，并独立用圆心(0,−15)、R1.95、Z0.85..1.65计算圆柱 bounds/volume再次核对。 |

KEY 模式遍历 `artifacts` 的全部条目，回读每一个非空 `shapes/*.step`，不按某个局部检查是否通过来筛选文件。每个非空文件都要匹配全部实体数、全部实体的有效性 / 正体积、完整匿名一一 bounds/volume 指标表及整体指标，且不允许重复文件路径。`empty=true` 条目必须原本声明零体积、空实体表、无 bounds、无 STEP 文件和 SHA；这些空差集仅保留原始清单，不声称独立重新计算其为空。

每个STEP在读取前记录SHA、字节数、绝对路径，读取后再次比较。全部读取结束后，再检查原报告、reader自身、冻结helper、生成脚本、所有原生记录源文件和全部读取STEP的前后哈希。KEY 原报告中的绝对源文件路径必须仍可读；不会静默改映射。

回读只导入冻结 P3 独立 reader：`engineering/product-integration-20261018/phase3-20261020/read_ep3_step_independent.py`，其 SHA 必须为 `14b2aa3362aba950a39244b0130021b72231fa2866e15d96e2f34a6dac6798c5`。不导入或调用端件、路径、装配生成器；运行结果同时记录是否出现这些生成器模块。

数值比较容差沿用冻结 reader：bounds为1×10⁻⁶ mm；体积为max(1×10⁻⁶ mm³,1×10⁻⁹相对误差)。这是数值回读容差，不能用作制造公差。

## 结论边界

`declared_readback_checks_passed` 只表示上述字节、数量、有效性和一一数值指标检查完成并通过。它不证明完整材料/拓扑等价，不证明STEP标签身份，也不重算190对碰撞、承压环、侧柱保持或材料子集。

材料账检查包括：去料STEP总量、新carrier记录量、`原体−去料+新增=新体`的数值一致性。旧carrier没有作为本次输入STEP提供，因此脚本明确记录没有重新执行旧/新布尔差集。原生报告若给出严格子集结论，脚本要求其实际记录的新增材料为0；仍不把这个原生结论改称为reader自身的布尔证明。

源报告的局部几何验收结果与STEP回读结果分别记录。KEY 的 `all_declared_local_checks_passed` 与 `declared_failures` 原样保留；原生局部失败不会阻止按其实际导出文件进行回读。KEY 原生源检查和未提前记录的加载源清单亦保留，reader 只核对源字典实际列出的输入字节及本次读取前后是否一致。回读通过不会将整机状态、强度、螺钉保持、KEY 装配保持或制造状态改为通过。
