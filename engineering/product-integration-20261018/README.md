> 当前交付见 [2026-10-20 第四阶段](phase4-20261020/README.md)：EP4 三态原生与独立回读、物理证据修复、A/KEY 局部改形。此前[第三阶段](phase3-20261020/README.md)和[第二阶段](phase2-20261019/README.md)保留各自执行身份。本页正文与 DELIVERY_VERIFICATION.json 是第一阶段历史快照，其中“本轮”“最新”和空 donor 观测均限于原日期；当前状态以第四阶段和根目录生成入口为准。

# RAZR-SLIDE：WP0–WP8 产品集成实现与验证

实施起点：`a1b3cc1e0773446f2e36d0a607edf61211dd9919`。本目录记录 2026-10-18 开始的产品集成工作；2026-10-19 的修复与原生重建使用 `3eae4e7258814c7f5454937535d6c642dd51662f`，各类证据保留自己的执行身份。PR #35 draft 的求解结果仍属于独立研究分支，历史失败保持原结果。

本轮交付共同产品总装、恒材料长度 OLED 与完整端接 FPC 研究、明确的手动动作和装配顺序、原生 PCB/端子映射、受限数值诊断，以及供后续工艺评审、加工与量测的研究图稿。**当前内部 FPC 候选由原生实体交叠明确否定；OPEN 的 0.2183 mm 几何回弯半径尚无供应商动态资格支持。手机实物尚未制作、装配或上电。** 下文记录已完成的软件/几何工作和仍需实物或改形的条件。

最终执行身份、各项检查的源码和输入哈希见 [DELIVERY_VERIFICATION.json](DELIVERY_VERIFICATION.json)。[验证说明](validation/README.md) 保留初次 32 组、1220 项的失败运行，以及修复后的 7 组、182 项通过运行；不相交选择覆盖 32 组、1240 项，`single_full_run_passed=false`。当前入口由 [sync_current_design.py](../../tools/sync_current_design.py) 从 [current_product.json](../../design/current_product.json) 生成。

原本地临时目录在重置后丢失了一批 2026-10-18 的原生报告、旧否定配置和归档。现有机械与 FPC 文件是新执行生成、重新读回并以新哈希封存的结果；旧哈希没有被用来证明旧文件仍存在。原始单元测试失败报告与日志另行保留，文件存续和重建边界见 [artifact-preservation.json](validation/artifact-preservation.json)。

## GitHub 发布状态（2026-10-19）

本轮已发布为 [PR #36](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/36)，完整研究证据提交为 `1c7be2695ac55b94f38c9d8187d1f9440e6c926b`；此后状态文档有独立跟进提交。PR36 当前开放，尚未合入 main。main 仍为 `a1b3cc1e0773446f2e36d0a607edf61211dd9919`。

[PR #25](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/25) 已于 2026-10-19T02:13:29Z 关闭为由 PR36 替代，未合并旧全体积驱动；其八个历史全局失败算例仍保持失败结果。[PR #35](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/35) 继续开放为 draft，头部仍为 `176df31ceb35bb3737d68030e60ba377665de210`，其正文已关联本轮见证覆盖与缓存停止诊断。

PR36 的首轮 [Research validation 运行](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39188719769) 在12个 job 中均未执行任何 step 即失败；本次具体平台失败原因尚未核实，不沿用旧运行的计费解释，也不计为云端测试通过。主机实跑、云端结果和物理资格分别保留，观测头部与状态见 [publication-status.json](publication-status.json)。

## 1. 工作包的实际交付边界

| 工作包 | 本轮实现 | 尚未满足的完成条件 |
|---|---|---|
| WP0 当前状态收敛 | README / CURRENT_DESIGN / status 同源生成；原八算例闭合、L2 4–7 算例完成和 PR35 draft 分开；旧 slack 语义以独立薄适配器对接当前求解器 | PR 元数据处理以真实发布记录为准，不能因本地函数通过而宣称 PR35 全局闭合 |
| WP1 平台与接口 | 已记录优先复用配对 donor 主板、屏幕/触控及原充电保护链的设计决策；12 类接口有 A/B 放置与跨舱去向；只读 ADB 采集已执行 | 采集未识别到连接 donor；准确型号、主板/屏幕/触控版本、电芯标签和实物 pin map 仍未知 |
| WP2 共同整机总装 | 同一坐标、83 件原机构来源、产品壳体改形、OLED、端接、相机和电池/电子件占位；输出多状态整机和单件 STEP/STL/BOM | 占位不能替代真实主板/电芯；B 舱 12 mm 宽电子空间未证明能容纳 donor；RF、散热、COF 与电芯膨胀未定 |
| WP3 OLED 材料与支撑 | 187.9 mm 恒材料模型，平面储存与回弯几何，全滑动/就位/反程路径检查；OPEN 可拆支撑板 | 当前参考屏材料长度不足；材料动态弯曲资格未知；全运动支撑/牵引未完成；支撑板没有机内收纳 |
| WP4 完整端接与 FPC | 两种 12×12 mm 板型，每端 DP/DS 各一块、双端共四块 PCB 模型；完整端接与 140 mm 自由带体完成 49 个运动状态及 15 个手动状态的原生检查；26 通道图稿对应的 KiCad v4 结果已保留 | 49+15 状态全部拒绝；实际叠层和动态弯折资格未知；台架样片不承担 OEM 显示、USB 或电池功率 |
| WP5 完整手动操作与装配 | 显式解锁、上滑、就位、手动 OPEN 螺钉保持、支撑板安装、拆除和反程复锁；新增件的插拔路径与运动包络 | 实际操作力、松手保持、螺纹承载、误操作和非名义伸缩分配仍需验证；不是已装出的机构 |
| WP6 电气与手机运行链 | 168 个独立既有 A-chain PCB/XML 端子核对；BM28 自有研究接点与 C01–C26 逐端关联；双包/USB/屏幕/触控拟复用原链路的边界明确 | 实际产品接口物理绑定数为 0；真正 donor 端子、原充电合流和保护拓扑未读取；未完成上电、显示触控或运动中供电/USB 实测 |
| WP7 尺寸与受限数值研究 | KEY 薄截面敏感性；1112 个原失败见证与1196域逐面绑定；预算128点的两种补点诊断；实际缓存预检和停止理由 | 没有启动新的 FE 求解；缺失当前 bearing 响应的可恢复缓存，实际材料/载荷未知；新改壳体未获结构验证 |
| WP8 研究样件与实测 | 研究件原生图稿、柔性铜图/切割补强图、台架夹具、接线表、逐步装配及空白测量记录 | 没有加工、采购、装配或实测结果；第一批完整物理开合样机仍未出现 |

## 2. 共同总装的空间结论

坐标采用 X 为宽度、Y 为上滑方向，正面朝 −Z；B 的位移为 `[0, slide, 8.2 − descent]`。79.75 mm 上滑和 8.2 mm 就位不能任意混合：只有上滑到位后才允许法向就位。

新产品场景保持原生零件来源，另行记录切除与新增材料。默认 `product_assembly.py` 命令导出当前候选；`--baseline` 才导出 83 件旧机构。外形比较计入新增前缘和背面材料；几何说明中的 8 mm 是基础壳体厚度。当前 A/B 刚性单舱外包围各约 **73.99×94.25×9.15 mm**。计入试验 OLED 后，**OPEN 整机约 73.99×174.00×9.35 mm；STOW 整机约 73.99×94.25×17.55 mm**，后者包含仍叠在后层的 B。9.35 mm 指 OPEN 整机厚度，不表示两个单舱都已分别装上真实屏幕。OPEN 附件按当时状态单独计入。

新机械归档 [native-STOW.tar.gz](mechanical/native-STOW.tar.gz)、[native-PREDOCK.tar.gz](mechanical/native-PREDOCK.tar.gz)、[native-OPEN.tar.gz](mechanical/native-OPEN.tar.gz) 已完成封存和独立读回，分别包含 **99、99、106 个单体**。这包含当前 94/101 件机械实体、四个空间分配体和一个试验 OLED；FPC 端接研究的 41 体 STEP 使用独立计数。31 个新增材料区域对 98 个场景参与者排除所属实体后，完成 `31×97×3=9021` 次非自身比较，未出现拒绝；检查范围和名义动作边界见 [机械证据](mechanical/README.md) 及 [final-delivery.json](mechanical/final-delivery.json)。

最终候选的电池占位如下。它们都是**外包络分配空间**，并非已选电芯。

| 占位 | 尺寸 | 体积 | 解释 |
|---|---:|---:|---|
| A 电池 | 64×40×2.75 mm | 7.0400 cm³ | 比 B 的体积分配更大；尚无额定容量或膨胀保证 |
| B 电池 | 12×68×4.4 mm | 3.5904 cm³ | 位于 B 一侧，避开伸缩机构完整名义扫掠 |
| B 电子件 | 12×68×4.4 mm | 3.5904 cm³ | 对侧空间；不能当作已经放入真实手机主板 |

早期探索曾报告 A 中央电池与 KEY 相交，以及 B 的整宽/22 mm 侧占位与伸缩件相交，但旧 `geometry-trial-r0/r1/r2` 和对应否定报告已丢失，不能作为本次仍可重验的原始文件。新的 [22 mm 宽 B 电池反例](mechanical/geometry-wide-B-negative-control.json) 从当前配置派生，只将 B 电池的 X 下界从 21 改为 11 mm，上界仍为 33 mm，其他参数保持原值。在新的 14 项几何测试中，滑动 40 mm 时它对真实伸缩件的正交集断言通过；同一阈值也检查当前 12 mm 分配。它有独立来源，未被标记为旧 r1 的复原件。

两电池总外包络仅 **10.6304 cm³**。4700 mAh 目标需要至少 **442.128236 mAh/cm³** 的完整电池外包络等效容量密度，而且这还没有扣除未定义的引出片、保护、制造与膨胀余量。本数字是约束算术，不是供应商能达到的性能承诺。详见 [capacity-budget.json](capacity-budget.json)。容量口径采用共同参考电压下的标签容量之和；在串并联拓扑未确定前，不宣称实际端口 Ah。

对应实现：[product_assembly.py](../../integration/product_assembly.py)、[product_geometry.json](../../design/product_geometry.json)、[机械证据](mechanical/README.md)。

## 3. OLED：材料守恒通过的范围

候选试验带宽 67 mm、厚 0.2 mm、恒材料长 187.9 mm，固定端在 A 前侧。弯曲路径在 STOW、PREDOCK、OPEN 之间保留同一材料身份，并检查前段、回弯和 B 中平铺尾段；没有将可视区长度或 FPC 尾部误计为可弯 OLED 材料。

| 状态 | 前段 | 半圆弯曲段 | 平铺尾段 | 回弯半径 |
|---|---:|---:|---:|---:|
| STOW | 83.7500 mm | 24.2688 mm | 79.8812 mm | 7.725 mm |
| PREDOCK | 163.5000 mm | 24.2688 mm | 0.1312 mm | 7.725 mm |
| OPEN | 163.5000 mm | 11.3883 mm | 13.0117 mm | 3.625 mm |

此特定路径族的可用材料长度区间约 **187.7688–188.3688 mm**。仓库已有两款参考模块的材料长度不足以覆盖该族：TOQ667XHT-01C 比下界短约22.61 mm；TA066FHV01-V2049A 短约31.13 mm。它们的料号和原始证据以 [OLED 报告](mechanical/oled-motion-report.json) 为准，不能据此泛化到所有柔性屏。

路径实体不穿透并不证明供应商允许相应曲率、循环或局部应力。OPEN 支撑采用手动侧向安装的独立可拆板，没有证明从储存到展开每个时刻的托底、夹持和牵引，也没有解决该支撑件在手机中的收纳。因此 WP3 保持部分完成。

## 4. 电气、完整端接与台架研究图稿

设计上将拟复用的主板和原供电管理分配在 B；主 OLED 固定材料端、较大电池、USB 端口板与相机分配在 A。显示、触控、大电池保护后回路、USB 数据/电源及相机形成跨舱需求；小电池、优先保留的 RF/音频/传感器默认在 B 本地。实际 COF 和 OEM 端子仍未知，B 平面储存的自由尾段没有被定义为固定屏幕接插件。真实拆机若改变这些位置，必须更新同一接口表。

最新只读 donor 采集于 **2026-10-19T01:19:54Z** 执行，返回码 **2**、`selected_donor_connected=false`，未识别到连接 donor。该结果证明采集程序执行并进入无设备分支，未取得实体主板、屏幕、电芯标签或实际针序，也未完成手机功能试验。采集执行身份见 [DELIVERY_VERIFICATION.json](DELIVERY_VERIFICATION.json)；后续必须连接可识别 donor 并补做实体测绘。

既有 A1/A2/B1/B2 命名属于 **A-chain 的四块研究板角色**，其中 B1/B2 不代表 B 舱电池。原生 PCB 与 XML 核对168个独立端子。自有 BM28 研究接点、mini 小板探针号、冻结旧板探针号分别列出，避免 DS 新 TP01=C01 被误接成旧板的 TP13=C01。详见 [electrical/README.md](electrical/README.md) 和 [coupon-static-terminal-schedule.csv](electrical/coupon-static-terminal-schedule.csv)。

FPC 候选固定 X 向带宽12 mm、名义成品厚0.1 mm、自由带长140 mm、两端各12 mm补强段，总材料长164 mm。每端包含相配研究连接器、DP/DS 各一块 PCB、静态引线预留空间、补强、夹爪与紧固件，双端合计四个 PCB 实体模型。共享场景在运动时显式使用左右解锁片各 3 mm 的模型输入，并补查手动程序中的螺钉逐颗安装/拆除及支撑装拆状态。

本次重建完成 **49 个运动状态和 15 个手动操作状态，共 64 条状态记录**；运动部分包含 25 个唯一材料几何姿态。**49 个运动状态与 15 个手动状态全部拒绝，原生 Boolean 计算异常为 0。** 否定见证来自材料/端接与 A_FRAME、A_BACK_PANEL、B_SHELL 的正体交叠。OPEN 最小几何回弯半径约0.2183 mm；供应商成品叠层、允许动态半径和循环条件仍未知，未被写成已经执行的动态资格试验。三个关键姿态的完整 FPC 材料与双端端接 STEP 各包含 **41 个有效正体**并已重新读回。状态、见证和执行输入哈希见 [motion-report.json](electrical/motion/motion-report.json)。

三份 ECAD 源图稿为 mini_DP、mini_DS 和 continuity26。小板名义总厚0.8 mm；单铜样片名义总厚0.1 mm。保留的原生 KiCad v4 回执记录三份输入均为 **零 DRC、零未连接、零封装库错误**，并保留项目规则、Gerber/钻孔和 STEP 独立厚度读回证据。本次重建生成的三份 PCB 源与 retained v4 输入字节完全一致，未重新运行 KiCad；原生验证继续引用 v4 自己的版本、执行身份和原始回执。早期未显式叠层、默认净距及封装库坐标问题保持其历史失败身份。

独立台架夹具只夹补强区，焊盘保持外露；单个夹持点包含尾带、补强、两爪、两颗名义螺钉和两颗螺母，共 **8 个有效正体**，其中不包含 PCB。DP/DS 配对端接置于夹具外，双端研究配置使用两组配对端接和静态绝缘跳线。C01–C26 是独立的低电压、小电流通断样片通道，**不是 OEM pin map，也不是高速或电池功率载流设计**。实际材料叠层、连接器库存、板厂工艺与夹紧力仍需确认。

电气新输出的 [artifact-index.json](electrical/artifact-index.json) 包含 **90 个文件条目，加索引文件自身共 91 个文件**。新运行及输入核对见 [rebuild-receipt.json](electrical/rebuild-receipt.json)。该集合不使用丢失的旧 89 件原字节身份；测试结果按 [验证说明](validation/README.md) 中的实际执行报告引用，未把旧测试日志冒充本次新输出。

## 5. 手动动作与第一次装配

手动程序明写解锁至复锁，包括需要人持续按住的阶段、先滑动再就位、安装两颗 OPEN 保持螺钉、插入支撑板、拆支撑/螺钉、抬升和反程。左右解锁输入独立保留，不能由几何动画推定用户总是同步操作。

首轮无电样件计划先制作尺寸和质量替身，目前尚未制作出样机。KEY 的薄片、名义 M0.6/M1 紧固部位与孔槽不能默认用普通 FDM 一次打印成品；STEP 输出并未确认对应制造方法、螺纹和强度。装配顺序、接线前检查和应记录的尺寸/操作力/保持状态见 [BUILD_AND_MEASURE.md](hardware/BUILD_AND_MEASURE.md)。[measurement-record.template.json](hardware/measurement-record.template.json) 是空白模板，所有未知值保留为 null，不计为实测。

## 6. 数值工作与受限停止

新 `slack_spring_contact` 只是复用当前主求解器的独立适配器。验证包括 slack/taut/mixed、独立枚举的小型 KKT 对照、不可行拉力、负柔度与零响应边界；没有覆写 `spatial_contact.py`，也没有吸收 PR25 旧全体积驱动。8个历史失败结果仍保留失败身份。

原 PR35 的1196个 bearing 域逐一核对投影字段、自由度、三角形、法向及顶点，1112个失败见证可绑定。原锁定环境重放初始77点；每种方案只加128点，得到205点。中心补点和失败见证补点分别量化覆盖改善；**205点是初始种子研究，不是用来替换失败末轮的1491点**。本轮没有新增 FE/QP 求解。

实际主机缓存预检扫描3292个文件，完整结束、无读取错误。发现的7份响应文件属于旧算例或缺少所需身份；`bearing-field-016.npz` 只保留场/力等结果，没有当前响应矩阵与点集。因而按预算规则在求解前停止。后续若恢复研究，先保存并验证响应/点集/原域/86体258自由度 trace 等完整身份，保留旧约束，才考虑每方案新增最多128点、最多2轮 QP+全局间隙审计、单线程、900秒的有限试验。当前预算没有被解释为已经执行。

KEY 新增长片的名义截面只有0.25×0.30 mm，名义长度23.8 mm；材料、真实无支撑跨度和载荷未定。截面惯性矩、Euler 阈值与小载荷柔度仅作显式参数敏感性。把假设跨度从23.8缩至8 mm，在相同材料/截面/支承型下可使 Euler 量级增加8.8506倍、端部小位移刚度增加26.3306倍；这说明应优先实测载荷并设计中间导向，不构成强度合格结论。

详见 [numerics/README.md](numerics/README.md)。**原 PR34/35 的 FE 证据属于旧安装几何，不能结构性验证本轮切改后的壳体、OLED 通道与新增支撑。**

## 7. 验证结果与复现入口

初次 `b6abcb6` 的 32 组运行实际执行1220项，结果为 FAILED；修复后 `3eae4e7` 的7组182项全部通过。正式选择初次运行已通过的25组1058项，加上修复运行的7组182项，两个套件集合不相交，合计覆盖32组1240项。**这不是一次整仓运行全部通过，`single_full_run_passed=false`。** 新机械 CAD 的14项针对性测试保留独立执行身份，不再累加到1240项。报告、日志、选择关系和依赖校验见 [validation/README.md](validation/README.md)。

复现时在仓库根目录使用对应执行回执列出的 Python 和依赖环境；修复运行的隔离依赖副本记录见 [runtime-copy-recheck-20261019.json](validation/runtime-copy-recheck-20261019.json)。每个输出目录必须新建，保留先前证据。

```bash
python3 tools/sync_current_design.py --check
python -B tools/verify.py --output /tmp/razr-product-unit-new
python -B integration/product_contract.py
python -B integration/product_capacity.py --output /tmp/razr-capacity-new.json
python -B engineering/product-integration-20261018/mechanical/run_product_study.py --output /tmp/razr-mechanical-new
python -B integration/product_fpc.py --coupon --motion --native --phone-scene --output /tmp/razr-fpc-new
```

本次保留已完成的 KiCad v4 结果。后续确需独立复核时，使用含 `pcbnew` 的实际 KiCad Python 和 [verify_native_mini.py](electrical/verify_native_mini.py)，先将输入工程复制至新的检查目录，再生成项目封装库、读取端子并输出 DRC；记录当次版本、参数和输出，保持 v4 原件不变。

## 8. 下一步执行顺序

1. **补齐真实 donor 输入。** 接入允许 ADB 的 donor，执行只读采集，记录机身、主板、屏幕/触控及双电池标签；量测 PCB、COF、尾排、连接器与电池膨胀后的边界。保留原机显示/触控/充电/USB 基线。
2. **先解决架构尺寸矛盾。** 将真实主板和电芯放入当前共同场景，重新判断 B 两侧12 mm空间及4700 mAh目标。必要时明确调整壳体、运动机构或容量目标，并在同一配置中生成新候选。
3. **重做 OLED 支撑与内部 FPC。** 获得满足材料长度的真实屏幕，设计整个动作中的托底、夹持和牵引；改变端接位置及完整带体路径，消除当前真实穿透并满足供应商动态半径。
4. **做无电可装配样件和柔性台架样片。** 先确认薄截面加工、槽销和伸缩件装入顺序，再量测操作力、松手保持、左右误差、完整反程及26通道通断。
5. **回写量测后再受控上电。** 按准确 donor 端子复用原保护/充电链；逐级核对显示、触控、供电与 USB，并对运动全程记录连续性。真实载荷和新几何确定后，才重新建立对应结构模型。

这些是本轮数值、几何和原生验证留下的具体后续条件；未加工或未上电的项目不会因代码测试通过而被改成完成。
