# 剩余 KEY／STOP：已有 Common 与构造来源的独立只读审阅

R5 V5 仍未过条件上界门的八个 frame，对应四个原 case，各有两个参考坐标系。已有 R3E producer 和 reader 对这些保存起点的直接 Common 均为 `0.0 mm³`，有效完整材料标记均为 `true`；原严格 Common 也均报告 `native_common / 0.0 mm³`，失败字段为 `null`。这组已有记录中没有正体积交叠证据。它们不证明完整剩余位移域，也不把 V5 约 `0.016 mm³` 的包络上界改成零。

## 精确原件与执行范围

机器结果 `R5_SAVED_KEY_STOP_COMMON_AND_SOURCE_REVIEW.json` 保存完整原 target/specification、每个 frame 的原 native 行、原材料身份和来源函数定位。只读脚本 `read_saved_key_stop_sources_r5.py` 已实际执行成功，未 import CAD/native 运行时，未新调用 Common 或拓扑操作。

原证据根目录为 `recovered-inputs/RAZR-R3E-COMPLETE-SCIENTIFIC-EVIDENCE-20261027/`。

| 原报告相对路径 | 字节数 | SHA256 |
| --- | ---: | --- |
| `native-and-math/producer/worker/report.json` | 65,374,048 | `f1c6bcb76d32f9dead19296ff37a64805eff59a8bcc4f696f99cc5821c370c5d` |
| `native-and-math/reader/worker/report.json` | 65,385,052 | `83e527ccbc849701f5d99c4e4b4ddbd099370ee52c7f10a1e11923c27b8742ce` |

本次核对这两份原报告的完整身份；八个选中 `tiny_base_Common` 行逐值相等。对应 16 个 producer/reader Base Common 导出文件及 16 个原输入 BREP 均按原 bytes/SHA256 实际读回。每个 Base Common 为 171 B，SHA256 `396c108ce1871b60b5076fddd4baa0266797a2294b4a401a689a9ed7ca1e2de0`。未对这些二进制文件进行新的原生几何读入。

## 原位姿与剩余域

四个 case 的原 binary64 q 区间相同：`[0.6429179606749895, 0.64291796067499] mm`，原端点十六进制为 `0x1.492c8afe385e4p-1` 和 `0x1.492c8afe385e8p-1`，差为 `4.440892098500626e-16 mm`。原十进制有理区间及原 binary64 值在报告中分别保留，未相互替换。

令 `a=1/2251799813685248`、`b=1/1125899906842624`。下表为原完整剩余位移盒 `(Dx,Dy,Dz)`；两个参考系使用的材料不同，全部原身份见机器报告。

| Case | 原体对 | Frame 1 full D | Frame 2 full D |
| --- | --- | --- | --- |
| case-028 | L_KEY / L_STOP_0 | `([0,0],[0,a],[0,0])` | `([0,0],[-a,0],[0,0])` |
| case-037 | L_KEY / L_STOP_1 | `([0,b],[0,a],[0,0])` | `([-b,0],[-a,0],[0,0])` |
| case-063 | R_KEY / R_STOP_0 | `([0,0],[0,a],[0,0])` | `([0,0],[-a,0],[0,0])` |
| case-072 | R_KEY / R_STOP_1 | `([-b,0],[0,a],[0,0])` | `([0,b],[-a,0],[0,0])` |

Frame 1 原移动材料为 ID 3，原固定材料为 ID 2；Frame 2 则为 ID 4 / ID 1。各原 `source_start_route` 均为 `original_lower_parameter_corner`，且保留后续独立参数区间。这里的零 Common 对应这些保存起点，不能代替对上述 full D 的保守证明。

更早 L1 的四个 `inputs/case-NNN/result.json` 仍记为 `unresolved_evaluation`，错误为 `finite nonzero displacement required`；其 `trace.actual_strict_Common_calls` 均为空。本审阅没有把这四次中止记成成功零交叠。

## r0.1 pin 与 r0.16 凹口来自哪里

`cam_coupling.py` 的 `parent()` 从 mounted manifest 和 SHA 绑定的 tar 读取原 STEP。`templates()` 将原 KEY 与 yoke 延伸体融合；`phone_scene()` 使用保存的 thin profile 平移原 STOP。代码中另有 `PIN_RADIUS=.4`，它指新传动 follower，不能作为 STOP 接触 pin 的半径。STOP 的 r0.1 和 KEY 的 r0.16 从继承材料传入。

本次只读核对 `r4-native/inputs/original-archives/mounted-native-geometry.tar.gz` 与原 manifest，archive SHA256 为 `684802dbcd35a51170734b16a359e7df40c240f430cd09f1dde7225562c2d933`，并核对其中两个 KEY、四个 STOP 原 STEP 成员。它们的 STEP 明文原语直接给出：

- L_KEY 的 `#2069/#2126/#2211/#2959/#3016/#3101` 为半径 `0.16` 的 `CYLINDRICAL_SURFACE`；右侧对应原记录也完整保留在机器报告。
- L_STOP_0/1 的 `#32`、R_STOP_0/1 的 `#33` 为半径 `0.1` 的 `CYLINDRICAL_SURFACE`。
- 原 thin 验证四条 profile 的 pin radius 均为 `0.1`；`cam_contact_native.extract_profile()` 从原材料识别这一族并建立证明用 pin carrier。

原 R3E case-028 库存再次绑定了 material 2 face 0 的 r0.1 圆柱、material 3 face 78 的 r0.16 部分圆柱；material 3 face 37/39 各有一个外圈，18 个 occurrence 为 15 条 Line 与 3 条 Circle。四个完整 face 的 canonical SHA 在 producer 与 reader 中相等。

这条链能定位继承 STEP、保存的原曲面参数和变换源码；本次限定只读未恢复最早创建这些凹口和 pin 的设计构造脚本。也没有证实原生 trim／closure 语义可直接等同于某个条件数学模型。若扩展 V6，仍需独立证明新模型的包含关系、保留全部非适用材料和完整原 D，并维持原阈值及未决事项。
