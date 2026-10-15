# FPC / OLED 制造输入审计，2026-10-13

R50 是本轮修复基座。本目录没有替换 R50/R44 路线、改变产品约束、削切 OEM 研究体、制作供应商数据或认可生产。**目前公开资料仍不能冻结直接生产用的 FPC 或 OLED；`manufacturing_go=false`。**

冻结关系：两舱成品同尺寸；单块约 7 英寸柔性 OLED；B 上滑 79.75 mm，再法向就位 8.20 mm；A 优先较大电池。约 67.32 mm OLED 研究宽来自 R17/R24 代理，不是供应商模块宽度许可。4700 mAh 仍为目标。

## 已落实的工程工作

1. 用供应商一手公开资料区分反复动态弯曲、安装弯折、滑卷技术展示和可订购受控模组。
2. 增加截面方向敏感性与**恒定材料站位**分析，阻止把 0.15 mm 厚度套到 1.2 mm 宽向曲率上，或把每姿态重新取的中心线点当成同一铜材位置。
3. 将具体询证内容变成 `supplier_input_contract.json`。所有未收到的图纸/报告哈希保持 `null`，没有伪造叠层、COF 或疲劳数据。
4. 保存 TCL 新闻稿寿命数字的检索冲突；没有挑选更宽松值，也没有将 17 英寸另一款产品的厚度移植到手机。

## OLED 候选与可使用范围

| 候选 | 可核验公开主源事实 | 本项目可用范围 / 缺口 |
|---|---|---|
| Samsung Slidable Flex Vertical | 官方 CES 2025 展示，竖向 5.1 → 6.7 英寸 | 优先询证竖滑工艺能力；不是可订购的指定 7 英寸模块。完整外形、COF、动态方向及寿命条件未公开 |
| TCL CSOT AMOLED Rollable | TCL Group 2021 正式发布稿：6.7 → 7.8 英寸，curl/slide R3 mm，配专用滑动机构 | 可询证真实手机滑卷能力；没有本项目料号、版次和资格图。检索摘要为 200k，直接正文为 100k，均不批准本项目 300k |
| BOE Dual Slidable | 官方 SID 展页：R2.5 mm，面向薄型笔记本 | 只能证明对应展示方案；没有手机尺寸与相同轨迹的模组资格 |
| BOE f-OLED | 官网技术页列出 slidable phone 应用 | 制造商能力线索，无受控可订购物料或完整图纸 |
| Visionox | 官方 SID 2021 报道列出 foldable / slidable / rollable 能力 | 可询证供应商能力，不能视为指定 7 英寸模组 |

主源链接：

- [Samsung CES 2025](https://global.samsungdisplay.com/31326?category=62&page=1&type=list)，2025-01-05；L107–109。
- [TCL Group 正式发布稿](https://www.prnewswire.co.uk/news-releases/tcl-csot-launches-two-flexible-displays-at-ces-2021-re-defining-standards-for-portable-devices-883702119.html)，2021-01-11；最新直接正文 L415–416。**0.18 mm 是 L404 的 17 英寸 Printed OLED，不是该手机 AMOLED 厚度。**
- [BOE SID](https://event.boe.com/)，Dual Slidable；[BOE f-OLED](https://www.boe.com/global/en/Products_OLED.html)，Core Strengths。
- [Visionox SID 2021](https://www.visionox.com/en/contents/191/425.html)，2021-06-03，L59–60。

BOE 2017 的 7.56 英寸 backward R5 mm 弯折展示是检索线索，但正文检索不稳定，不将其收入已冻结尺寸输入；弯折展示本来也不授权循环滑卷。Samsung 4.7 → 7.2 英寸媒体数字未找到可复核公开官方参数页，本目录不将它写成受控产品规格。没有公开料号不等于供应商无法提供定制品，只表示目前没有该制造输入。

## FPC 供应商规则与真实弯曲方向

All Flex 的 [2024 半径技术说明](https://www.allflexinc.com/wp-content/uploads/2024/03/Minimum-Bend-Radius-Considerations-in-Flexible-Circuits.pdf) 使用包含 coverlay / adhesive / shield 的总叠层厚度，给出 1–2 层 6×、更多层 12×的设计起点，强调 RA 铜、晶粒方向及工艺。它同时指出未粘合双层组会互相挤压，空气隙及交叉网格参考面需重新处理阻抗；这不能自动解决 USB SI。以上是设计起点，不是本项目宽向弯曲、扭转及寿命许可。

该厂 [设计指南](https://www.allflexinc.com/wp-content/uploads/2023/04/AFS-AllFlex-Circuit-Design-Guide.pdf) p15 给出约 10×厚度，p16 指实铜屏蔽增刚、银屏蔽不推荐动态应用；[2026-08-05 动态布局说明](https://www.allflexinc.com/blog/pcb-conductor-fillet/) 采用 12×并要求 pad / transition 离 fold line 至少 0.76 mm、孔避开弯区。公开经验值有不同适用范围，不能挑选 6×并宣称本设计已合格。

Minco 的 [2019 Design Guide](https://www.minco.com/wp-content/uploads/Minco-Flex-Circuits-Design-Guide-2019.pdf) p26 将动态应用指向单层，p22 要求依铜/镀层/层数/曲率/循环考虑实际用途，p23–25 要求完整 artwork、层叠、尺寸公差、netlist 和测试。其 [Flexibility 技术说明](https://www.minco.com/wp-content/uploads/Designing-a-Flex-Circuit-for-Flexibility.pdf) 解释中性面与弯区的层位置、裂纹/褶皱、错列导体及去粘合问题。可用作定制 RFQ 起点；未取得任何本项目叠层或样片。

本项目不直接采用供应商营销中的“铜延伸率 >20%”判断动态疲劳。单次断裂延伸率、实际铜应变幅、应力集中、循环次数和寿命分布不是同一个物理量。

`bend_axis_sensitivity.py` 精确重用 **q=0** 理想平面 U：W1.2 / t0.15 / R16.5 / L120 mm。最大截面纤维距离指数为 `(|cosθ| W + |sinθ| t)/(2R)`。

| 条件 | 本轮实算指数 | 意义 |
|---|---:|---|
| 宽轴朝半径，平面内弯曲 | 3.63636% | 截面宽向极纤维运动学指数 |
| 宽轴转 90°，厚向弯曲 | 0.454545% | 厚向极纤维指数，前者为它的 8 倍 |
| 假设 18 µm 铜恰好位于中性面 | 0.0545455% | 仅说明铜层站位敏感性，不是本项目实际铜应变 |
| 同 18 µm 铜中心偏离中性面 50 µm | 0.357576% | 仅说明缺中性面会改变结果，非层叠推荐 |

真实 FPC 的铜线宽向位置、各层 modulus / 厚度、粘接、屏蔽、残余应力及中性面未知，上表不能作为实际铜疲劳/FEM。易轴旋转也不能解决空间：前轮真实 OCC 代理 STOW OLED 交叠 2.0030464168 mm³，且超下侧 Z 0.350 mm，本轮保留该负例，无新 STEP 或改孔。

恒定材料站位从 A 端量取：圆弧入口材料坐标随滑动从 **6.5818606079 → 46.4568606079 mm**，移动 39.875 mm。距 A 端 10 mm 材料站位由弯变直，90 mm 站位由直变弯。每姿态只看最小 R 或重新取同一参数点不能建立铜材完整循环历史。q=8.2 的三维弯扭、真实夹具材料导向、摩擦和连续路径尚未计算；这里没有用 q=0 数学替代它们。

复算：`python -B bend_axis_sensitivity.py`；有意义的轴交换、同材料站位、长度守恒与非法输入测试：`python -B -m unittest -v test_bend_axis_sensitivity.py`。6 项通过，结果和原始进程日志随包保存；不冒充 FPC 工程资格测试。

## 下一道不可由软件补造的输入门槛

先取得**同一指定可交付型号及版次**的完整 OLED active area / module outline / touch / 封边 / DDIC / COF / 静态 FPC / 端接 / 禁弯区与支撑工艺，以及允许循环面的动态 R、张力/压紧、平储残余形变、展平力、温湿及失败判据。供应商必须确认本设计的 Y79.75 + Z8.2、约 67.32 mm 研究屏宽与真正壳体限界，不能仅确认“约7英寸”。

FPC 每条 SIGNAL / USB / A放电 / B放电 / A充电 / B充电必须单独有：可制造 artwork/netlist、指定铜型及晶粒方向、层叠/粘合/总厚、公差、材料导向、弯曲两轴/扭转边界、与 BM28 静态端接的局部柔顺颈及独立锚夹图、300k 循环后阻值/绝缘/断续/短路和物理裂纹判据。USB 还需全路径阻抗/回流、动态眼图/BER；电源还需峰值/温升/短路资格。目录半径不能共同替代这些约束。

收到供应商/OEM 同源图纸后才导入实际材料宽厚、端接/罩/夹/导轨/OLED 全包络及公差，执行材料站位连续弯扭和实体扫掠，并制造验证 coupon / 静态端接 / 动态样机。**本轮没有取得该输入，没有发送询价/联系供应商、下单或接受 NDA。** 这些是实物和供应商数据硬阻塞；软件无法把现在的 GHOST 图改名成可直接生产。
