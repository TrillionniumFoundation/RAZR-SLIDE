# 2026-10-19 第二阶段交付：分件装入、共同总装与真实证据接入

本轮功能与原生执行绑定提交 **F = `1c970e34a72f83ac1148ed3dee11e050ed5508dd`**。已实际完成捕获随动件的分件装入研究、包含完整 EP2/FPC 的三态共同总装导出与独立读回、旧端接与 EP2 的原生比较，以及 donor v2 和设计身份采集。F 的完整 1297 项执行最终出现 1 项测试失败，原始失败报告保留；后续 G 仅修正测试对原生拒绝结果的判定，限定复跑与覆盖核对另行记录，不改几何或将 F 写成全套通过。结果继续归入 [PR #36](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/36) 的产品研究增量，不将研究分支或 PR35 draft 的结果写成 main 已接受的整机能力。

**2026-10-20 已通过 Pocket4 的专用 ADB 5061 接通实际 XT2551-3 donor，并取得系统与双电池软件读数；原厂中国手册确认对应 moto razr 60 Ultra。拆机主板/屏幕/COF/电芯标签与几何尚未取得，滑盖样机尚未制造，也没有改造整机的上电验收。** EP2 消除了本轮检查到的端接组内冲突，但旧端接和 EP2 的三态整机记录共六条仍全部拒绝。4700 mAh 仍是目标，具体电芯与原保护/充电拓扑尚未给出支持该目标的证据。

所有 `candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 和 `physical_phone_verified` 均保持 false。完整记录入口为 [SUMMARY.json](SUMMARY.json)。下列采集时间均为 UTC。

## 1. 已实际执行的结果

| 范围 | 本轮实际结果 | 结果能支持的结论 |
|---|---|---|
| 原捕获件轴向装入负控 | 8 条原路径均发生阻塞 | 原封底、缩口和保持头不能按这八条声明路径直接装入 |
| 新分件局部装入 | 12 条完整连续直线装入路径均 clear | 所声明的局部分件顺序在有限材料模型中可复核；不是整机完整装配或开合实测 |
| 原材料重组 | 5 个原局部对象的重组体积差为零 | 新分件在该报告中的名义材料与原对象一致，没有靠删保持肩或扩大槽取得通过 |
| 原生来源比较 | 7 项通过：5 项等同、2 项包含关系 | 局部研究与实际原构造器的材料来源相符 |
| 捕获件 STEP 读回 | 14 个单件、含 11 个实体的局部总装通过 | 导出的局部实体可读回并与所记录身份对应 |
| 三态共同总装 | STOW / PREDOCK / OPEN 分别为 154 / 154 / 161 个参与体；独立读回全部通过 | 机构、原空间分配、OLED、完整 EP2 与有限 FPC 可在同一坐标系导出和复核 |
| EP2 组内原生检查 | A/B 两端各 190 对，内部拒绝均为 0 | 本候选的组内有限实体没有检出正交叠；仍不证明整机可放入或具备制造条件 |
| EP2 与有限 FPC 的 OPEN 检查 | 带体与 B 端 20 个对象中有 3 处真实正交叠；带体与 A 端 20 对及 A/B 端间 400 对均 clear | 端接组内自检通过不能推出带体对完整端接避让；三处反例继续保留 |
| 旧端接组内负控 | A/B 各 1 条拒绝，正交叠分别为 71.55 / 164.565 mm³ | 原下夹爪与静态 26 线转接预留冲突由原生实体重现 |
| 旧端接与 EP2 的整机比较 | 三姿态 × 两变体，共 6 条记录全部 rejected | 至少已有足以否定这两种当前装机候选的实体反例 |
| Donor v2 采集 | 04:54:32Z，ADB inventory 为空，返回码 2；提交和输入绑定一致 | 本次未取得可读取 donor；未知实物字段和功能状态继续保留 |
| 设计身份入口 | `--print-binding` 实际返回码 0 | 工具在真实 Git 检出中输出了可追溯设计身份；它不是实物采集通过 |

对应原始结果分别见 [captured report](mechanical/captured-report.json)、[captured readback](mechanical/captured-readback.json)、[common manifest](mechanical/common-manifest.json.gz)、[common readback](mechanical/common-readback.json)、[routing native report](routing/native-report.json.gz) 和 [donor v2](hardware/donor-v2.json)。数值比较与读回沿用报告中记录的 CAD 内核、容差和输入身份，不扩展为加工公差、接头强度或真实装配验收。

## 2. 分件装入解决了哪一段装配问题

原套筒同时具有封底和缩口，内级具有大于缩口的保持肩；CAM 与 KEY 的闭槽又不能让完整保持头沿槽板法向穿过。此前 CAD 中已经嵌套好的最终形状，尚缺可执行的装入顺序。

本轮把底盖、芯底肩和 CAM / KEY 保持环拆成独立件，先装裸芯和内层子总成，再逐层封底，最后将槽片放在尚未封闭的保持面之间并安装最后一片保持环。原八条失败路径继续作为负控保留，新十二条路径覆盖所声明直线装入的完整连续扫掠。

十二步包括套筒/CAM 子总成的十步，以及 KEY 槽/随动销界面的两步。它们尚未覆盖完整壳体、所有 cartridge、完整 KEY 和其他相邻机构的最终装入与工具通路。零材料差也只说明名义 CAD 的重组关系：真实焊料、胶层、过盈、焊接变形、连接强度和装配余量还没有实测输入，不能把接触面视为已完成接头。

局部单件和总装位于 [captured-parts.tar.gz](mechanical/captured-parts.tar.gz)。分件尺寸、十二步顺序及连接边界见 [捕获随动件说明](../physical-test-followon-20261019/README.md)。

## 3. 共同总装现在包含完整的研究参与体

新入口把每侧七个分件放回其实际母件所在的整机坐标中，共增加十四个机械分件。每个母件仍通过原生材料重组校验。三态实际导出组成如下：

| 状态 | 机械参与体 | 其他完整参与体 | 实际总数 |
|---|---:|---|---:|
| STOW | 108 | 4 个空间分配体 + OLED + 有限 FPC + 40 个 EP2 端接体 | 154 |
| PREDOCK | 108 | 同上 | 154 |
| OPEN | 115，包含原 OPEN 附件 | 同上 | 161 |

这套导出明确保留未通过的 EP2/FPC，名称带有 `REJECTED_EP2`，以便从同一总装中看见问题。它没有删去电芯/主板分配或端接板对来获得更小的参与体数量。四个空间分配体仍是项目占位，并未变成实物量测模型。

完整包为 [common-assembly.tar.gz](mechanical/common-assembly.tar.gz)，参与体、输入和输出身份见 [common-manifest.json.gz](mechanical/common-manifest.json.gz)，独立读回见 [common-readback.json](mechanical/common-readback.json)。**独立读回通过表明导出内容可复核；该导出器没有因此重新取得整机正间隙或连续开合通过。**

## 4. EP2 和 OLED 的具体空间结论

### EP2 的组内改进与空间代价

每个 EP2 端接仍保留一对 DP/DS 板，两端合计四块 PCB。板对、暴露焊盘和夹持区重新安排，并加入连接到下夹爪的有限承载架。每端 190 对内部检查已清零；旧结构的 71.55 / 164.565 mm³ 组内反例也在同一原生流程中重现。

端接组内检查与有限 FPC 对完整端接的检查具有不同范围。提交 F 的原生结果如下，每端包含 20 个有限对象：

| EP2 姿态 | 有限带体 → A 端 | 有限带体 → B 端 | A 端 → B 端 |
|---|---|---|---|
| STOW | 20 对均 clear | 20 对均 clear | 400 对均 clear |
| PREDOCK | 20 对均 clear | 20 对均 clear | 400 对均 clear |
| OPEN | 20 对均 clear | 20 对中恰有 3 对拒绝 | 400 对均 clear |

OPEN 的三处拒绝来自真实 `native_common` 体积，记录在同一份 [原生路由报告](routing/native-report.json.gz)：

| 与有限 FPC 带体交叠的 B 端对象 | 正交叠体积 / mm³ |
|---|---:|
| `B_M2_clamp_screw_1` | 0.314159265358978 |
| `B_M2_clamp_screw_2` | 0.314159265358978 |
| `B_lower_jaw` | 16.039734577831304 |

原生诊断原本已经正确拒绝这三处交叠。F 的失败测试错误地要求相关完整端接避让项全部 clear；G 的修正范围是让测试核对这些实际正交叠及相应拒绝结果。**这项测试修正没有消除 OPEN 的三处碰撞，也没有重新取得整机或完整运动路线通过。** 本节体积与 CAD 包始终保留 F 的原生执行身份，不标成 G 的新几何执行。

完整 EP2 的名义宽、长、高为 **14.6 × 35 × 4.65 mm**。对于原 B 侧 12 mm 分配，仅宽度就需要额外 2.6 mm。静态 26 线目前仍是预留空间，未完成每根引线、绝缘、焊接、实际端子和装入顺序；薄支承台也没有真实螺纹、锁固或受载依据。

三态两变体的整机检查均拒绝，因此 EP2 不能作为本轮已选定的完整内部路线。其文件包 [ep2-artifacts.tar.gz](routing/ep2-artifacts.tar.gz) 保留该研究候选的实体与输出，不是已批准加工或装机的生产包。

### OLED 平直尾端与 FPC 回弯必须联合改布局

[arithmetic.json](routing/arithmetic.json) 将现有 OLED 路径族的材料窗口和有限尾端要求写成可复算下界。该族原总材料窗口只有 **0.6 mm**；当前 187.9 mm 材料在 PREDOCK 的平直尾部约为 **0.131197 mm**。例如请求保留 3 mm 平直尾端时，当前材料至少需增加约 **2.868803 mm**，固定转弯位置下的 B 足端平储至少延伸 **2.4 mm**。3 mm 是研究参数，不是供应商规定的 COF 或夹持尺寸。

既有 G2 自由 FPC 路线在 OPEN 的层间距仍为 0.5 mm，其模型最小半径约 **0.2182854 mm**。单独改变自由总长只会改变直段，不会消除由层间距决定的回弯半径。真实 OLED/COF 禁弯区、柔性叠层、刚柔转换和动态条件均未取得，因此本轮没有动态材料资格结论。

必要布局条件、完整端接定义和公式边界见 [OLED 与端接后续研究](../routing-followup/README.md)。下一版需要把实际材料、COF、端夹、牵引、全程支撑、端接高度及内部通路一起输入同一模型。

## 5. 实际平台和测量接入

[donor-v2.json](hardware/donor-v2.json) 的实际采集时间为 **2026-10-19T04:54:32Z**，设备清单为空，返回码 **2**。该记录保留实际命令 stdout/stderr、采集源码、提交和设计输入身份；[product-input-binding.json](hardware/product-input-binding.json) 保留实际成功执行的设计身份输出。

该次 main 主机观察未读到 donor，仅适用于被检查主机和时刻。它不证明设备不存在、故障或不兼容，也不能推导出主板、显示/触控、COF、电芯和连接器的型号、尺寸或针脚。2026-10-20 已在 Pocket4 的 ADB 5061 接通 XT2551-3；真实保护/充电拓扑、改造整机的显示/触控、供电与 USB 运动运行链仍未验证。

本轮已实现原始标签、端子 CSV、尺寸 CSV 和手机功能日志的归档与版本绑定。导入器保留原始文件及明确缺项，输出建议配置更新，不自动修改接口表或把模板变成实测。手机日志与机械/OLED/FPC 时序需要共享实物编号、设计身份和有依据的时基；稀疏采样不构成任意短暂掉线均不存在的证明。

**当前自动设计兼容检查覆盖两份 JSON，不构成整仓 CAD 或加工文件一致性证明。** Donor/实测导入的 `files_sha256` 自动绑定 `design/product_geometry.json`、`design/product_interfaces.json`，并记录接口合同、原始 Git 身份及提交与工作区字节是否一致。导入器允许原提交早于当前 HEAD；若两份 JSON 和接口合同不变，即使 EP2 配置、CAD Python 或路径实现已经变化，旧记录仍可能通过兼容检查，但记录保留原样件和原 commit。Donor 身份与端子事实的兼容也不能证明新几何已实测。

手机观察记录始终保留 `phone_function_verified=false`、`motion_continuity_verified=false`，尺寸记录保留 `CAD_replaced_or_packing_verified=false`，不会由兼容检查自动发出整机或制造 go。修改 EP2、CAD 构造器、布线路径、STEP 或加工文件后，需要另行绑定相关源码、配置及实际加工文件的 SHA256，并取得对应实物记录；旧观察只适用于原样件与原提交。机械时序分析器可核对额外列入 `files_sha256` 的文件及其 Git 字节，但未列入的文件不会自动受到覆盖。导入约定中的“仅增加说明文字之后导入”属于操作要求，代码没有自动证明后续提交只改了说明文字。

采集与导入命令、原始附件和字段约定见 [IMPORT_EVIDENCE.md](../hardware/IMPORT_EVIDENCE.md)。本轮没有可供实体导入的真实部件/量测 manifest，也没有从软件测试夹具生成实物报告。

### 2026-10-20 的实际接入进展

上述 main 主机空清单是保留的历史观察。当前已找到 Pocket4 上既有的 RAZR ADB 5061 服务，并取得同一 USB 序列号哈希对应的授权设备。详细原始记录、软件值与规格口径见 [当前 donor 接入与未冻结项](hardware/pocket4-20261020/README.md)，[机器可读发现记录](hardware/pocket4-20261020/discovery-summary.json)，[原厂资料与区域候选接口表](hardware/pocket4-20261020/oem-source-map.md)。这解决了 donor 接入和 SKU 身份问题；没有将软件属性或不同区域的维修料号当作本机拆机量测。

## 6. 完整软件执行与托管执行

### 完整软件套件

提交 F 配置并实际完整执行了 **33 个套件、1297 项测试，整体结果为 FAILED**。其中 32 个套件的 1283 项通过；`routing-followup` 的 14 项中出现 1 failure，完整运行没有 error 或 skip。失败项错误地要求 EP2 的相关完整端接避让检查全部通过，而 OPEN 中有限带体与 B 端确有上节三处原生正交叠。原生诊断的拒绝结论正确，几何与材料路径没有因此修改。

该次完整执行从 **2026-10-19T04:52:52.913239Z** 到 **2026-10-19T05:16:48.757245Z**，回执耗时 **1435.843795 秒**。失败报告原始字节 SHA256 为 **`e300c8c2a15c6719d1b36a09f8b33a568b094155c3aa4ec740f6b53d3263f853`**，见 [F 完整失败报告](validation/full-unit-1c970e3-report.json.gz)。该报告继续保留失败身份，不以修复后的断言重新解释成 F 全套通过。

| 证据身份 | 执行范围与结果边界 |
|---|---|
| F：`1c970e34a72f83ac1148ed3dee11e050ed5508dd` | 本轮原生 CAD、donor 和该 head 的 CI 来源；33 套 / 1297 项完整运行有 1 项失败，另 32 套 / 1283 项通过 |
| G：修正测试判定的后续提交，实际 SHA 见下方修复回执 | 只修测试判定，限定复跑 `routing-followup` 的 14 项；不改几何，不将 F 的原生报告重新标成 G 执行 |
| 独立覆盖核对 | 取得 G 的实际限定运行回执后，核对 F 的 32 套 / 1283 项与 G 的 1 套 / 14 项是否完整、互不重叠地覆盖注册的 33 套 / 1297 项，并核对非测试功能源的一致性；实际结论以下方回执为准 |

G 的实际提交、限定复跑结果与独立覆盖校验如下。完整失败和限定通过分别保留，**不能称为单次全套 PASS**。

**G = `4fe96be97ee64d1f4f28ba6ea09d7775030b0c6c` 的 14 项限定复跑实际通过，0 failures、0 errors、0 skips，返回码 0。** 从 `2026-10-19T05:26:50.084165+00:00` 至 `2026-10-19T05:28:03.310887+00:00`，耗时 73.227 秒；运行前后源码字节一致。G 与 F 只有上述一个测试文件不同，几何构造、端接配置和诊断源码不变。见 [修正提交](validation/test-repair-commit.json)、[限定运行报告](validation/routing-repair-report.json.gz)与 [回执](validation/routing-repair-execution.json)。

独立核验器实际核对了两次运行的输入、源码、注册表、套件和逐测试身份，确认 F 中通过的 32 套 / 1283 项加 G 的 1 套 / 14 项，构成无重复、无遗漏的 33 套 / 1297 项选择覆盖。**这是两个提交下的分离执行覆盖通过，F 的完整运行仍为 FAILED；本轮没有单次全套 PASS。** 核对结果见 [canonical-selection.json](validation/canonical-selection.json)，核验器与实际执行回执也一并保留。该范围不包含新的一轮完整机械运动、KiCad 原生重跑或真实手机功能验收。

前一阶段 b6abcb6 的失败、3eae4e7 的局部修复和 1240 项分离选择验证继续保留各自身份，不能作为 F 完整失败或 G 限定复跑的替代结果；main 的历史 1187 与 PR35 draft 的历史 1216 也保持原范围。

### GitHub Actions

功能提交 `1c970e34a72f83ac1148ed3dee11e050ed5508dd` 对应的 [Actions run 39201906846](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39201906846) 已完成，结论为 **failure**。本轮实际采集到的 **12/12 个 job 均为 0 个执行步骤、`runner_id=0`**，均具有付款/预算限制 annotation；这些 job 没有继承前一次运行的旧结果。采集器实际返回码为 2，同时完成了原始响应留存，见 [1c970e3-run39201906846.json](actions/1c970e3-run39201906846.json)。

因此 **Actions 尚未恢复执行**。现有 annotation 指向近期账户付款失败或需提高支出上限；它没有判定究竟是哪一个账户设置，也没有产生任何托管软件/CAD 测试通过结果。账户侧条件恢复后，需要对明确 head 再取得真正启动并执行过步骤的工作流报告。增加本地通过记录或重新导出 CAD 不会改变这项托管结论。

## 7. 本轮证据索引

| 类别 | 文件 |
|---|---|
| 汇总与范围 | [SUMMARY.json](SUMMARY.json) |
| 捕获件装入与来源 | [captured-report.json](mechanical/captured-report.json) |
| 捕获件实际导出与读回 | [captured-parts.tar.gz](mechanical/captured-parts.tar.gz)、[captured-readback.json](mechanical/captured-readback.json) |
| 完整共同总装 | [common-assembly.tar.gz](mechanical/common-assembly.tar.gz)、[common-manifest.json.gz](mechanical/common-manifest.json.gz)、[common-readback.json](mechanical/common-readback.json) |
| OLED / FPC / EP2 | [arithmetic.json](routing/arithmetic.json)、[native-report.json.gz](routing/native-report.json.gz)、[ep2-artifacts.tar.gz](routing/ep2-artifacts.tar.gz) |
| 实际接入检查与设计身份 | [donor-v2.json](hardware/donor-v2.json)、[product-input-binding.json](hardware/product-input-binding.json) |
| F 完整软件运行：FAILED | [full-unit-1c970e3-report.json.gz](validation/full-unit-1c970e3-report.json.gz) |
| 该功能 head 的托管事实 | [1c970e3-run39201906846.json](actions/1c970e3-run39201906846.json) |

归档成员、压缩文件与未压缩报告的 hash 应以相应 manifest 和汇总中的实际记录为准。STEP 包存在、测试数量已注册、导入工具能运行分别有自己的范围，不合并成制造或整机完成状态。

## 8. 下一轮按六个顺序推进

| 顺序 / WP | 需要完成的具体工作 | 下一轮验收输出 |
|---|---|---|
| **1. 冻结实际平台 — WP1 / P0** | 沿已接通的 Pocket4 / XT2551-3 继续取得同一套主板、显示/触控、COF、A/B 电芯、USB 板及连接器原始标签与规格；记录元件高度、出线方向、板端和端子 | 关键未知项由实物或原始规格填入；每条真实链路都有对应部件、连接器、引脚和证据，不能从驱动家族名推断 |
| **2. 真件几何替换占位 — WP2 / P0** | 将实际部件外形、极耳、保护器件、膨胀依据和固定方式放入共同总装；重新解决 B 主板位置、12 mm 分配与 EP2 的额外宽度，加入 RF 和散热通路 | 全状态空间结论对应同一真实部件版本；4700 mAh 由具体电芯和拓扑支持，或明确修订布局/目标 |
| **3. OLED 与内部 FPC 联合重做 — WP3、WP4 / P0** | 以真实材料、COF 和动态条件设计端夹、牵引、全程支撑转换、完整端接与内部带体；解决已保留的整机碰撞和 OPEN 回弯限制 | 至少一条完整正反程候选清除实体冲突，并保留连续运动复核、材料来源和对应样片图稿 |
| **4. 首批无电装配件 — WP5、WP8 / P0–P1** | 明确薄壁、底盖、保持环与紧固位置的实际工艺及接头尺寸；先用无电尺寸/质量替身执行完整壳体和机构装入，再记录全开合 | 真正可按顺序装配的样机；操作力、左右偏差、松手保持、退出就位和复锁均有原始记录，局部几何装入不代替整机实物验收 |
| **5. 柔性样片与真实电气链 — WP4、WP6、WP8 / P1** | 先量测柔性通断样片和端接保持，再按已核对的 donor 端子复用原保护/充电链并逐级上电 | 同一版本的显示、触控、供电和 USB 结果；运动日志保留采样率、时基、缺数、掉线与失败，不用端点两次测量代替过程连续性 |
| **6. 真实载荷与结构研究 — WP7 / P1** | 取得真实材料、截面、未支撑跨度、接头及载荷传递；把对应新版几何纳入结构模型。若继续 PR35，先恢复完整且有身份的缓存 | 计算与实际改形对应；有限重算的输入、结果、失败或停止原因可追溯，不将外部操作力直接当成 KEY 内力 |

**并行 WP0：**恢复账户付款/支出上限条件后，对明确功能 head 重新执行 Actions，验收真正执行过步骤的托管报告。当前代码侧已取得未启动的原始证据，不能用更改完成标志代替平台恢复。

本轮没有新采购、加工、物理循环或容量测量，也没有为原 PR35 启动新的 FE/QP 求解。未取得的实物条件和账户条件应在下一轮原始记录中解决，不填入推定部件、虚构工期或预先通过结论。
