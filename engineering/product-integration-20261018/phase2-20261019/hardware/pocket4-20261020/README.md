### 实际 donor 已连通，物理平台仍待冻结（2026-10-20）

**已在 Pocket4 的 ADB 5061 端口连接并读到 1 台已授权 donor，型号记录一致为 XT2551-3。** 六次只读探测发生于 2026-10-20 01:12:24–01:25:06 UTC；其中 donor 身份读取时间为 01:17:51 UTC。USB 描述符 `22b8:2e81`、ADB `device` 清单及后续模块读取的样本序列号 SHA-256 相同：`41ad305f8562a6c47710afe71fabf30cb8692a71d3de1a47ca9949b669bcc6c1`；USB 产品名、`ro.product.model` 与 `ro.boot.hardware.sku` 均为 `XT2551-3`。[USB 记录](usb-observation.json)、[donor 身份记录](donor-identity.json)

Pocket4 默认 ADB 5037 的空清单仍保留，但当时另有 5061 服务正在运行；本次明确指定 5061 后取得了上述授权设备。此前 main 主机的空清单也只描述该主机的探测范围，不能据此继续把“没有接通 donor”列为全局未知。[ADB 服务记录](adb-servers.json)、[USB/ADB 接口记录](usb-adb-interfaces.json)

| 记录层 | 本次实际读取 | 可以据此确认的范围 |
| --- | --- | --- |
| 系统身份 | `leap` / `trillionnium_leap`；`ro.soc.model=SM8750`；SoC sysfs 为 `SUN`、`618`、`2.0` | 软件报告的产品、平台与 SoC 身份；主板物理版本和器件丝印尚未核对 |
| 当前软件构建 | Android `17`；fingerprint 为 `motorola/trillionnium_leap/leap:17/CSV1.260518.010/eng.qq:userdebug/test-keys` | 当前自定义构建的身份；不当作 OEM 出厂系统或实物模块版本 |
| 显示与触控 | `wm size` 返回 `Physical size: 1224x2992`；两个显示/DSI 注册；`goodix_ts` 标记 `IsExternal=false`，`fts_ts` 标记 `IsExternal=true` | 像素尺寸及软件显示/输入注册；尚未取得屏幕、COF、连接器实物标识，也未在本次探测中验收显示画面或触控操作 |

上述系统、显示和输入结果见 [donor-identity.json](donor-identity.json) 与 [module-readback.json](module-readback.json)。`wm` 的 `Physical size` 是命令返回的像素描述，不能替代毫米量测或 OLED 材料长度。

**4700 mAh 已有匹配型号的 OEM 整机规格依据；本项目新滑盖包络的容量目标仍待实际电芯和布局证明。** 联想中国支持站原稿第 2 页将 `moto razr 60 Ultra` 对应到 `XT2551-3`，手册编号 `SSC8E69755-B`，列出典型容量 **4700 mAh**、额定容量 **4540 mAh**。[OEM 手册，第 2 页](https://www.lenovocare.com.cn/ideaservice/535125b81e2f46eabffa9c1568443961.pdf)

| 软件节点 | `CHARGE_FULL_DESIGN` 原值 | 按标准 `CHARGE_*` 单位换算的设计值 |
| --- | ---: | ---: |
| `main_battery` | 3430000 µAh | 3430 mAh |
| `flip_battery` | 1140000 µAh | 1140 mAh |
| `battery` 汇总节点 | 4570000 µAh | 4570 mAh |

原值见 [module-readback.json](module-readback.json)；µAh 单位及设计值语义依据 [Linux power supply class 的 Units / CHARGE_FULL_DESIGN 定义](https://docs.kernel.org/power/power_supply_class.html)。**3430 + 1140 = 4570 mAh，比 OEM 额定 4540 mAh 多 30 mAh；该差异保留为未解释项。** 软件设计值、OEM 额定值与 OEM 典型值分别记录，没有容量充放电实测，也没有由这些数值推定串并联、保护或合流拓扑。

型号字符串 `NFG_ATL_RS35NVT_3520MAH` 出自 **`battery` 汇总节点的 `POWER_SUPPLY_MODEL_NAME`**；本次 `main_battery` 的 uevent 没有 `MODEL_NAME`，因此不能把该字符串直接当作主电芯物理标签。`main_battery` / `flip_battery` 返回的 `TYPE=Mains` 也按原样保留。`balance_master` / `balance_slave` 的原始字段不统一赋单位、不换算，其驱动定义尚未核实。[模块原始读取](module-readback.json)

六次探测共保留 **24 个实际文件**：每次的 JSON、原始 stdout、探测脚本和 provenance。各次捕获均完整结束，stdout 哈希与 provenance 一致；内部仍有 **9 项读取失败**，包含权限拒绝、缺失目录及首轮 SoC 循环命令的语法错误，均保留原始返回码和错误。后续 SoC 单文件读取已成功，但受限的面板/设备树目录、空硬件版本属性及 `screenPartStatus=UNSUPPORTED` 没有被转成已识别零件。[donor 读取](donor-identity.json)、[模块读取](module-readback.json)、[可读节点范围](available-nodes.json)

下一步 WP1 的输入已收敛到这台具体样本：取得主板、屏幕/触控、COF、两块电芯及连接器的实物标签与量测，确认实际端子、保护/充电拓扑和复用边界，再将真实包络交给 WP2、WP3/WP4。等尺寸双舱、79.75 mm 上滑、8.2 mm 就位和 B 舱平储 OLED 的约束继续保留；RF、散热、极耳、膨胀及动态材料条件仍须随同真件进入同一设计。本次完成的是 donor 连通和只读身份取证，**物理平台、几何和端子尚未冻结；没有加工、改造后的受控上电或手机项目验收，所有项目 go 标志保持 false。**
