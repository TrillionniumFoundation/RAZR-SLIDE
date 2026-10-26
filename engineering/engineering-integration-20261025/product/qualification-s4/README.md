# S4 同版 G3—G5 空采集包

本包绑定功能源码 **`dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`（S4）**。四份模板均是原生成器输出的原字节，未填写样机、测量、批准人或工程限值。**本轮新增实测为 0；G3 未执行物理资格评估，G4/G5 原评估结果均为 `unknown`；全部实体资格和放行标志为 `false`。**

## 现场使用顺序

| 文件 | 填写前必须具备的真实输入 |
|---|---|
| `templates/G3-EP5-as-built.template.json` | 同一 specimen 的 CAD、routing、BOM、图纸、材料、工艺、固件七类证据；实物/批次身份、方法、时间、定位与原件 SHA。它们是证据类别，并非七个实物零件身份已补齐。 |
| `templates/G3-EP5-plan.template.json` | 预先批准的无电动作计划、采样与对时要求，以及力、行程、偏斜、保持漂移、OLED/FPC 半径和电阻等限值的来源。 |
| `templates/G4-plan.template.json` | G3 前提与同样机功能基线；原电池和原充电两模式的完整动作覆盖、九组功能规程、十四类通道的物理测点身份/校准/限值来源。 |
| `templates/G5-plan.template.json` | G4 前提；寿命次数、样本数、检查点、载荷/速度/温湿度、关键尺寸与工艺验收来源；逐样本原始暴露记录和各 cycle/phase 的时间窗口。 |

1. 先补齐真实 donor 的十个缺失身份字段和十二接口原件；具体字段见 `OUTCOME.json`。保留同一 specimen 的标签照片、尺寸、连接器方向、原机功能基线及原始记录。现有历史观察的重读不会替代新采集。
2. 将本包复制成新的现场工作副本；由负责工程师依据实际器件、材料、测量系统和用途确定并预先审查各项来源。所有 `null` 都表示尚缺依据，不能凭经验填入任意数字以使程序通过。
3. 完成真实记录后再使用原合同评估。G5 必须提供原始逐样本暴露和动作窗口，不能只填每周期最小/最大值、摘要采样间隔或动作顺序来取得通过。缺失仍为未知，实测失败必须保留。
4. 任何源码、接口、实物或工艺版本变化都需要重新生成对应版本的绑定；不能把本包或旧 C2 包的 SHA 直接改成新版本。

## 本次实际检查

独立 S4 检出中，原生成器产生七份 JSON；121 个源文件和 13 个 native 输入均核对了真实字节身份。native 输入只读取并计算摘要，没有导入 CAD 或重算。原 G3 `validate_current_routing_binding` 与原证据读取器通过 EP5 配置/生成器结构检查；原 G4/G5 CLI 在不提供 acquisition 的情况下再次评估，结果与生成器原输出相同。源身份检查通过只说明空表对应这一版本，不能授予实体资格。

公开目录仅含四份原字节空模板、工程聚合和内容摘要。带历史 specimen 标识或运行位置的原 inventory/readiness/执行回执作为完整原件另行保留；`ORIGINAL_OUTPUT_REFERENCES.json` 给出七个原输出的大小与 SHA256。旧 C2 历史包保持原样。

## 原命令复用

在已准备原锁定环境的独立仓库检出中运行；输出目录必须是新的。以下命令只生成和检查空表，未提供真实 acquisition。

```bash
git checkout --detach dd7def6e6a4de9f47dc91ca2ab336fb1a8828560
.venv/bin/python -B engineering/engineering-integration-20261025/product/build_product_delivery.py --output ../qualification-s4-new
.venv/bin/python -B integration/product_qualification.py --repository . --plan ../qualification-s4-new/G4-plan.template.json --output ../qualification-s4-new/G4-repeat-readiness.json
.venv/bin/python -B integration/product_qualification.py --repository . --plan ../qualification-s4-new/G5-plan.template.json --output ../qualification-s4-new/G5-repeat-readiness.json
```

## 不可变合同来源

- [S4 原采集包生成器](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/dd7def6e6a4de9f47dc91ca2ab336fb1a8828560/engineering/engineering-integration-20261025/product/build_product_delivery.py)
- [S4 G3 原结构与物理评估合同](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/dd7def6e6a4de9f47dc91ca2ab336fb1a8828560/engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py)
- [S4 G4/G5 原采集、覆盖与资格合同](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/dd7def6e6a4de9f47dc91ca2ab336fb1a8828560/integration/product_qualification.py)
- [S4 donor 与十二接口合同](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/dd7def6e6a4de9f47dc91ca2ab336fb1a8828560/design/product_interfaces.json)
