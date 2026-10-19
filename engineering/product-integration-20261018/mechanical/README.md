# WP2 / WP3 / WP5：共同整机、平面储屏和完整手动操作研究件

本目录交付一个可执行、可拆分的同版原生 CAD 研究件。它复用了主干的 83 件机构，在实际前方 OLED 遮挡旧滑钮、屏幕回弯撞壳、原电池分配撞传动等问题上做了具体修改。当前研究件有 94 件常装机械实体；在 OPEN 装入独立支撑板、四颗支撑螺钉和两颗保持螺钉后为 101 件。四个器件空间分配和一个有限厚度的试验屏体另列为参与者。

**这尚不是已经装下 Donor、4700 mAh 电池和约 7 英寸真实 OLED 的手机。** 当前可复现的是明确参数下的原生几何、材料长度、名义运动和新增件装入路径。真实 OLED/COF、Donor PCB、电芯、全程受力支撑和螺纹保持仍有具体未完成项，见文末。跨舱 FPC 是电气目录的独立有限材料对象，不是 OLED 本体的延长段。

## 1. 当前入口与来源

| 入口 | 用途 |
|---|---|
| `design/product_geometry.json` | 世界坐标、约束、四个研究空间、OLED 参数、材料改动登记 |
| `integration/product_assembly.py::product_scene` | 当前共同机械场景；94 / 101 件 |
| `integration/product_assembly.py::registered_components` | 四个独立命名的器件空间体 |
| `integration/oled_storage.py::geometry` | 一条 187.9 mm 恒材料长度、67 mm 宽、0.20 mm 厚的几何试验屏 |
| `integration/product_motion.py::manual_program` | 解锁、滑出、就位、固定、支撑、拆除和复位的 14 个独立手动动作 |
| `run_product_study.py` | 同一进程运行 14 项针对性测试、主报告和三个状态的 STEP / STL / BOM 导出 |
| `verify_added_material_motion.py` | 对全部新增材料做连续相对运动包络检查 |
| `verify_product_exports.py` | 不导入产品构造器的完整 STEP 读回，以及新增 M1 螺钉的有限工具入口检查 |

主干基线固定为 `a1b3cc1e0773446f2e36d0a607edf61211dd9919`。当前结构从 `engineering/panel-bearing-web-20261015/native-templates.tar.gz` 的 34 个模板及其固定父级来源重建；该归档 SHA256 为 `f8e610824c9a3603e12579c43c2169228f3729e4d07d4838c46c3cae0b2673b7`。当前构造器核验归档及源输入的 SHA256，导出 manifest 保留实际使用的来源。不改写原模板，`native_scene` 保留原 83 件场景作为对照。最初下载时的 `source-downloads.json` 回执已随本地临时材料丢失，不能声称该旧回执仍在本目录。

### 2026-10-19 证据重建说明

2026-10-18 的完整报告、旧否定配置和三个原生归档在本地临时环境重置后丢失；保留下来的旧哈希不是文件仍然存在的证据。功能源码已恢复，并修正当前 `product_scene` 曾继承原生基线 83 / false 的元数据问题：当前返回实际 94 / 101 件及材料已修改，基线来源仍单列 83 / false。此次在持久执行目录重新运行研究、完整 STEP 读回和封包，使用新执行记录及新文件哈希；以下几何设计数值不冒充已复原的旧输出字节。2026-10-19 已在 `3eae4e7258814c7f5454937535d6c642dd51662f` 完成新的 14 项测试、三状态导出、31 个新增材料区域的 9021 次非自身比较，以及三份独立 STEP 读回；检查均通过。实际归档身份以新 `final-delivery.json`、`execution-record.json` 及其绑定报告为准，单元修复的 7 组 / 182 项另见上级 validation 目录。

现有尺寸来自项目自有设计假设，未冒充 OEM 实测。器件注册的来源类别区分 `design_space_allocation`、`supplier_nominal_envelope`、`measured_component`；实测类别必须带测量记录，未选型电池空间不能获得容量字段。

## 2. 坐标与相等外包围

X 为宽度，Y 为纵向，Z 为厚度。A 固定；B 的世界位移是 `[0, s, 8.2-d]`。B 先在 A 后方的正 Z 一侧，随后沿正 Y 滑出 79.75 mm，最后沿负 Z 就位 8.2 mm，成为上半部。产品正面为负 Z；保留历史零件名 `A_BACK_PANEL`，没有用改名掩盖原滑钮被屏挡住的问题。

| 由实体计算的对象 | 宽 × 长 × 厚，mm | 说明 |
|---|---:|---|
| A 的常装刚性零件 | 73.99 × 94.25 × 9.15 | 包括侧向拉片、侧导向、A 屏支撑及其固定件 |
| B 的刚性主体 | 73.99 × 94.25 × 9.15 | 包括真实前缘、回程导向和支撑固定座 |
| OPEN，101 件机械实体 | 73.99 × 174.00 × 9.15 | 包括全部七个独立 OPEN 附件 |
| OPEN，加试验 OLED | 73.99 × 174.00 × 9.35 | OLED 最外面为 Z = -1.35 mm |
| STOW，94 件机械实体加试验 OLED | 73.99 × 94.25 × 17.55 | B 仍位于正 Z 后层 |

两舱原始壳体厚度为 8.0 mm；本版增加的前方结构使刚性外包围增加 1.15 mm，试验屏的最外层再增加 0.20 mm。不是把 8.0 mm 标签保留下来声称外形没变。六级左右伸缩件是跨舱运动参与者，不计入单个固定舱的内部电池空间；它们仍在整机碰撞集合中。

这里的相等是当前刚性研究件外包围相等。真实 OLED 的完整叠层、COF、保护层、端接、天线、开孔和供选型器件仍可能改变成品尺寸，不能把本表当作已合格的实物手机外形。

## 3. 实际材料修改和固定结构

原 83 件中，78 件几何保持原样。改变五件：`A_FRAME`、`A_BACK_PANEL`、`B_SHELL` 和左右 `THUMB_PAD`。每一件都有原体积、移除量、新增量和新体积的守恒账，记录在导出 manifest 的 `mechanical.product_changes.material_accounting`。

| 修改件 | 原体积，mm³ | 移除，mm³ | 新增，mm³ | 新体积，mm³ |
|---|---:|---:|---:|---:|
| A_BACK_PANEL | 4,700.6433 | 216.5626 | 38.0761 | 4,522.1568 |
| A_FRAME | 8,030.7425 | 1,209.9167 | 1.4954 | 6,822.3212 |
| B_SHELL | 13,101.9274 | 457.8280 | 2,042.2062 | 14,686.3056 |
| 每侧 THUMB_PAD | 3.5231 | 0 | 37.9680 | 41.4911 |

A_FRAME 移除了约 15.1% 的原材料体积。连通正体和运动不穿透不代表这种切槽后的承载能力已经成立；新增到其他部位的材料也不能抵消关键截面的削弱。

- **侧向操作。** 两个旧 M0.6 可拆滑钮保留原连接和 PAWL 传动；增加厚 0.60 mm 的横向操作臂，侧边到达 X = ±36.995 mm，仍各自沿 Y 移动 3 mm。每侧增加一件独立导向桥和两颗名义 M1 螺钉，桥通过与 A 原材料相连的座固定。原屏前方操作入口的穿透负例保留，新侧向有限探针在锁定和释放端均可触到拉片且不穿过其他实体。
- **B 平面回程槽。** 从 B 原实心搭接部切出 X = ±33.7、Y = 5.4…15.5、Z = 5.7…6.3 mm 的通道。不是把这一段实心材料当成已有空腔。两片实际导向材料的 Z 范围为 5.65…5.85 和 6.15…6.35 mm，它们与 B 原搭接部相连；对 0.20 mm 试验屏各有 0.05 mm 名义法向间隙。
- **转向窗口。** B 上部窗口为 X = ±33.7、Y = 88.1…93.59、Z = -0.05…0.8 mm；A 上端的窗口同时切入 frame 和 panel，范围为 X = ±33.7、Y = 89.4…94.5、Z = -0.05…4.2 mm。修整后的各壳仍是一个有效正体；这不证明窗口削弱后的弯曲、扭转、跌落或疲劳强度。
- **前支撑。** A 有可拆 0.20 mm 支撑片，四颗名义 M1 固定点在 X = ±34.5、Y = 42 / 76 mm。B 的 OPEN 支撑是一件独立 1.0 mm 厚的侧插附件，四个固定点在 B 局部 X = ±34.5、Y = 40 / 70 mm。为真正允许侧插，在 B 的正 X 前缘切出入口；全 80 mm 侧插及逆向取出都进入几何检查。
- **OPEN 保持。** 世界 X = ±34.5、Y = 87 mm 处各有一颗从后方装入的名义 M1 保持螺钉。A 增加实际环形肩部，B 有通孔和头部沉孔；没有把一个布尔姿态标志充当锁扣。两颗螺钉依赖尚未验证的真实螺纹连接和预紧，当前平滑名义孔本身不提供轴向固持。

B 前缘 X = ±35.8…36.995、局部 Z = -1.15…0.10 mm 与 A 后缘实际切除的套叠槽配合，使两个固定舱的前深度相等。右侧入口也计入 B 的实体修改；没有用不可拆的完整侧墙掩盖 OPEN 支撑插不进去的问题。

## 4. 真实被排除的旧布局与当前空间

| 当前研究空间 | 舱内范围 / 尺寸 | 外包围体积 |
|---|---|---:|
| A 电池 | X = -32…32，Y = 38…78，Z = 4.5…7.25；64 × 40 × 2.75 mm | 7,040.0 mm³ |
| B 电池 | X = 21…33，Y = 16…84，Z = 0.9…5.3；12 × 68 × 4.4 mm | 3,590.4 mm³ |
| B 电子分配 | X = -33…-21，Y = 16…84，Z = 0.9…5.3；12 × 68 × 4.4 mm | 3,590.4 mm³ |
| A 相机分配 | X = -5…5，Y = 2…12，Z = 0.9…7；10 × 10 × 6.1 mm | 610.0 mm³ |

A 优先较大电池分配在体积层面成立。A+B 总电池外包围只有 **10.6304 cm³**，未计入实物膨胀、极耳、保护和装配公差；没有从体积虚算出容量。B 的 12 mm 宽电子条带也绝不是已经安入原 Donor 主板的证据。摄像头只占位，光学出口和遮挡关系尚未建立。

旧 `geometry-trial-r0.json` / `r1.json` / `r2.json` 及对应否定报告目前不可恢复为原始字节。新的 `geometry-wide-B-negative-control.json` 明确从当前配置派生：只把 B 电池的 X 下界从 21 改为 11 mm，上界仍为 33 mm，构成 22 mm 宽反例；其他几何不变。它不是旧 r1 的复原件。保留的原生交集断言要求此新反例在滑动 40 mm 时与真实伸缩件有大于 1e-7 mm³ 的正交集，同时要求当前 12 mm 分配对同组伸缩件没有超过该阈值的交集。实际见证由新测试和 `product-motion-report.json` 回写。当前电子 / 电池空间只有上表所列数值。

伸缩件的正确名义轨迹是世界 Y 约为 81.5 mm，`|X| = 7.25 + (12 / 79.75) s`；不能错误地把它们当作不变 X 的固定柱，也不能把 X / Y 的独立最大包围相交直接认作同一时刻的真实碰撞。

## 5. OLED 材料账：几何可行区间与供应商失败

模型只有一条固定材料坐标：A 的固定端在 Y = 2、Z = -1.25 mm；前直段、一个半圆转向段、B 内的平面回程段按同一材料坐标连接。每一状态的宽、厚、长度相同，总体积为 **2,517.86 mm³**，且原生屏体为一个相连正体。B 的储屏自由端随着开合移动，不能一面用这一材料账，一面宣称实际 OLED 的 COF 已固定在 B 主板旁。

| 状态 | 前段，mm | 半圆中心线半径，mm | 回弯段，mm | B 平面回程，mm |
|---|---:|---:|---:|---:|
| STOW | 83.7500 | 7.725 | 24.2688 | 79.8812 |
| PREDOCK：滑完但未就位 | 163.5000 | 7.725 | 24.2688 | 0.1312 |
| OPEN：已就位 | 163.5000 | 3.625 | 11.3883 | 13.0117 |

在这个特定单回弯、固定端和运动顺序下，全过程材料长度必须满足 **187.768803 < L ≤ 188.368803 mm**。采用 187.9 mm 只是使几何账成立的研究值。原始全深内腔从 B 局部 Y = 15.35 mm 开始，最多支持的上界为 178.418803 mm，小于所需下界；因此至少需要再向原实心搭接部延伸 9.35 mm 的平面储存。这是上述实际通槽修改的原因。

| 已有源记录中的屏 | 记录的面板名义长度 | 相对本拓扑下界的不足 | 不能冒充完整叠层的厚度记录 |
|---|---:|---:|---|
| TOQ667XHT-01C | 165.16 mm | 22.6088 mm | 0.234 mm 只是已给出的若干层之和 |
| TA066FHV01-V2049A | 156.64 mm | 31.1288 mm | 0.231 mm 表格值与 0.291 mm 目录值存在未闭合冲突 |

来源是主干的 `controlled-inputs-web-20261013-r6/candidate_facts.json` 和 `oled-orderable-module-search-20261013-r5/extracted-tdo-inputs.json`；原始 SHA 在 `oled-motion-report.json` 的 `supplier_comparison` 中。TOQ 的 attached-FPC 200.587 mm 高度、TDO 的 112.39 mm FPC 长度没有加到 OLED 面板长度里。实际 AA 长宽、最大成品叠层、COF、触控、材料中性层和动态半径均未落实。

因此两块已有候选屏都不能支持本版储屏拓扑。187.9 × 67 mm 的试验条没有被称为已经购得的约 7 英寸屏。上述结论也不是对所有 OLED 收纳拓扑的全局不可能性证明。

还有两个直接的装配问题：PREDOCK 只剩 0.1312 mm 平面回程，未给真实 COF / 端夹留出已经证明的空间；半圆随就位从 R7.725 变成 R3.625，当前没有实际变半径成形机构强制它沿该理想曲线走。平面上下导向已建模，全程延展前段仍需要临时成形支撑 / 手动托持，连续随动支撑尚未实现。

## 6. 完整手动路径和保持的边界

程序顺序是：左解锁 → 右解锁 → 向上滑完 → 法向就位 → 左右两颗保持螺钉逐一装入 → 装入 B 支撑；关闭时完整逆向拆除支撑与两颗保持螺钉，再退出就位、滑回，最后分别复位两侧 PAWL。共 15 个姿态、14 个独立动作，回到完全相同的锁定 STOW。所有 B 运动阶段要求左右滑钮都为 3 mm 释放位，不能沿用 factory 的默认零滑钮值做全程运动。

七个 OPEN 附件目前是独立取用件，没有设计机内收纳。当前程序可以表达完整手动开合，不表示已经得到单手操作或无需附件的日常手机。新滑钮 / 导向桥 / A 支撑是在原机构已装好的基础上从前方装入；原 cartridge、伸缩副和全部 OEM 器件的装配顺序没有在本包重新验证。

保持的实际材料见证不是 `open_hold=True` 本身。每侧固定螺钉相对于 B 抬起 0.01 mm 有约 0.0159436 mm³ 正交集，对 B 沿 Y 再移动 0.1 mm 有约 0.151748 mm³ 正交集；B 下移 0.01 mm 与 A 肩部有约 0.0714712 mm³ 正交集。与此同时，螺钉在 A 的平滑名义孔内抬起 0.01 mm 的交集为 **0**，这保留了“没有真实螺纹就不能证明轴向固定”的否定控制。未指定材料、螺纹加工、有效啮合、预紧和负载前，不声称保持力已证明。

## 7. 验证范围与证据解释

主报告的四个状态包含 99 / 99 / 99 / 106 个实体。检查所有涉及修改件、新增件、四个分配体和试验 OLED 的配对；每个前三级状态为 1,848 对，OPEN 为 2,562 对。未把“场景里有 99 件”偷换成“所有旧件之间又做了一轮新验证”。未改动的旧件关系仍受原主干证据的边界约束。

连续检查包括新增侧臂的完整 3 mm 行程、新件和支撑插拔、B 新前缘完整滑出 / 就位、四个分配体对三阶段机构包络、试验 OLED 对 484 个有限完整路径包络组合，以及全部 31 个新增正体材料区域对 98 个机械 / 分配参与者的三阶段相对运动。反向通过相同几何集合。

STOP 采用原 `ContactProfile` 的单调四段位置，弹簧是随其变化的占位体，它们并非恒速刚体。两份主报告中将全部内部件概括为 `affine` 的文字应按这一点限定：这八个对象的端点包围成立是因为有单调全行程界；补充报告明确采用完整 profile 的包围，不将它们套入刚体相对平移。其余相对刚体在补充报告中核验了原生端点平移一致性。

有限直线包络的非轴向圆柱载体可能保守增加材料，正交集先作为拒绝，只有原始材料在具体姿态的正交集才称真实碰撞。零交集也不自动意味着正间隙；输出保留具体的正轴向间隔证据和 native-common 方法。当前路径覆盖名义槽中心线和均分伸缩位移，没有扩张成任意间隙、任意伸缩分配、受力接触、摩擦、疲劳或跌落结论。

独立读回使用与构造器相同的 OCCT 内核，但不导入产品构造器；它检查所有 STEP 根和完整拓扑，不只抓取第一个 Solid；单件必须一体、正体积且有效，整机计数、体积和边界必须与清单相符。STL 只作可视化 / 后续加工评估，字节哈希核验不等于打印制造合格。

初次独立读回曾发现并修复一个边界证书错误：默认 OCCT 边界使用 STL 三角网格缓存，使同一 A_PANEL 的记录 Zmin 从 0 扩成约 -0.000295377 mm，尽管独立 STEP 体积只差 7.3e-12 mm³。这些是当时观察到的数值；旧 `export-cache-drift-negative.json` 文件已丢失，不是本次可供重验的原始报告。当前构造器和独立读者都使用 `AddOptimal(useTriangulation=False)`，14 项测试中的外包围测试直接断言 STL 网格化前后边界不变；新读回仍使用原 1e-7 容差。

## 8. 复现与拆件交付

从仓库根目录运行（需要仓库锁定的 CadQuery / OCCT 环境）：

```bash
python engineering/product-integration-20261018/mechanical/run_product_study.py --output /tmp/razr-product-study-run
mkdir -p /tmp/razr-product-study-evidence
python engineering/product-integration-20261018/mechanical/verify_added_material_motion.py --output /tmp/razr-product-study-evidence/added-material-motion-report.json
python engineering/product-integration-20261018/mechanical/verify_product_exports.py --manifest /tmp/razr-product-study-run/STOW/manifest.json --output /tmp/razr-product-study-evidence/readback-STOW.json
python engineering/product-integration-20261018/mechanical/verify_product_exports.py --manifest /tmp/razr-product-study-run/PREDOCK/manifest.json --output /tmp/razr-product-study-evidence/readback-PREDOCK.json
python engineering/product-integration-20261018/mechanical/verify_product_exports.py --manifest /tmp/razr-product-study-run/OPEN/manifest.json --output /tmp/razr-product-study-evidence/readback-OPEN.json
python engineering/product-integration-20261018/mechanical/seal_product_study.py --input /tmp/razr-product-study-run --evidence-dir /tmp/razr-product-study-evidence --reconstruction
```

主研究的输出目录必须不存在且在源码树之外；独立读回和补充报告的父目录需要先创建。上面 `/tmp` 是短期复现示例，正式重建使用持久目录。每个状态包含完整 STEP 总装、逐个可拆单件 STEP、对应 STL、BOM CSV 和 manifest；STOW / PREDOCK 各 99 个单体，OPEN 为 106 个单体。封包器将 `native-STOW.tar.gz`、`native-PREDOCK.tar.gz`、`native-OPEN.tar.gz` 和 `final-delivery.json` 写入 `--evidence-dir`，逐成员重查归档字节，并拒绝错误的当前件数 / 基线元数据。缺失的历史文件单独列为不可用。封包时观察到的 Python / 依赖版本仅描述封包进程；生产各报告的真实执行环境应同时附在 `--execution-record` 指定的外部执行回执中。

单独从当前 CLI 导出：

```bash
python integration/product_assembly.py --output /tmp/razr-current-STOW
python integration/product_assembly.py --output /tmp/razr-current-OPEN --slide 79.75 --descent 8.2 --open-hold --open-support
python integration/product_assembly.py --output /tmp/razr-original-baseline --baseline
```

默认 CLI 使用当前 `product_scene`；只有显式 `--baseline` 才导出原 83 件机械场景（另有四个分配体）。非 STOW 的默认左右滑钮为 3 mm，OPEN 支撑和保持附件必须显式选入。

## 9. 下一件能实际制作什么，缺什么

可以据此准备不通电的机构尺寸替身与可拆检查件，并按照 `assembly-BOM.csv` 逐件选择加工法。**不能把所有 STL 默认交给普通 FDM 一体打印。** A 前支撑和 B 储屏导向只有 0.20 mm，侧臂 0.60 mm；继承机构还包含约 0.25 × 0.30 mm KEY 臂、约 0.17 mm 盖壁和约 0.15 mm 轴承壁。这些尺寸需要板材 / 薄片 / 微加工方案或放大验证件，材料、精度、连接和装配处理尚待确定。名义 M1 / M0.6 螺钉并未选到具体可采购长度，也没有建模螺旋螺纹。

最有决定性的后续工作是把实际 Donor 主板与连接器外包围、电芯含膨胀与极耳包络，以及一块实际 OLED 的完整材料 / COF 数据放进这个同一工厂。当前 12 mm B 电子条带和 187.9 mm 屏材料账已经指出产品布局必须调整的位置。应先解决这些具体空间和端接问题，再决定保留当前单回弯拓扑还是调整屏幕锚点 / 储存路线。

随后用尺寸与质量替身检查完整机构与工具操作，用连续柔性样片验证供料 / 支撑 / 回程，再进入真实 OLED 和跨舱电气连接。跨舱 FPC 的有限材料和端接碰撞结果在同日期 electrical 目录；它必须通过 `product_scene + registered_components + OLED_GEOMETRIC_TRIAL` 的同一障碍集，不能用另一套空舱障碍场取得“已装入”结论。

本包不覆盖真实散热路径、天线调谐、相机视场、USB 壳口、重心和跌落质量分配。它们需要实际组件、材料、固定点和开口后才能进入同版模型，不以空白分配体替代验证。
