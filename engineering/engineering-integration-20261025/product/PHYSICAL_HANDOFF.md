# RAZR-SLIDE 现场实物采集交接单

**对应候选：C2 `bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb`；日期：2026-10-25。**

本单用于采集可追溯原始证据并准备 G3→G4→G5。**本轮没有新增真实尺寸、端子、制造、上电、运动或寿命结果；所有缺值继续留空/`null`。** 已有记录仅确认过软件型号 `XT2551-3`，关联 specimen 为 `XT2551-3-41ad305f`；这不能代替实物标签和硬件版本。若现场不是原来那一台设备，须建立新 specimen，不沿用其身份或拼接原记录。本单没有发布任何联系人消息，也不构成加工、通电或制造放行。[S1] [S2]

## 1. 现场先建立一个证据包

- [ ] 在完整原机状态拍摄 specimen 标签与整机；拆出部件后继续使用同一 specimen，并给部件稳定 `part_id`。保留每次拆装、换件、损伤和维修记录。
- [ ] 为每份照片、录像、仪器输出、原始 CSV、原厂文件保存原文件、SHA-256、实际 UTC 时间、采集人/仪器、方法、单位、测量不确定度及可定位的照片位置/文档页码。标注图另存，保留未经标注的原件。
- [ ] 所有运动、电气、视频数据使用明确的同一 `timebase_id`，记录同步方式及对齐误差；照片或“通过”备注不能替代连续原始数据。
- [ ] 保存 C2 commit、精确设计/生成器/原生输入及实际加工文件 hash；实物偏差按实填写。使用本交付 C2 绑定的 G3 EP5 v2、G4、G5 模板；旧 EP4/旧 commit 记录只能保留其历史结论。实物资料回写使受绑定输入变化时，工程侧须先冻结新 commit、重新生成计划并重新审查先决报告；不能把 C2 空模板直接标为已执行。设计改变后建立新绑定，不能直接改旧记录的 commit。[S3] [S10] [S11] [S14]

**回交数据格式**（列名照合同保留；附件用 observation ID 和 locator 关联）：

| 原始记录 | 必需列 |
| --- | --- |
| 端子 CSV | `net,source_connector,source_pin,sink_connector,sink_pin,observation_ids,locator` |
| 尺寸 CSV | `part_id,quantity,value,unit,uncertainty,observation_ids,locator` |
| 原机/装机功能 CSV | `time_s,phase,function,reported_outcome,metric,value,unit,observation_ids,locator` |

采集 manifest 要保留真实 `specimen_id`、采集时间、方法、人员/仪器、完整 `design_binding` 和每份原始附件 path/hash。只有真实观察发生后才能标记 `physical_execution_occurred=true`；未观察项不用零代替。导入器只核绑定和格式，不能认证照片真伪或自动放行整机。[S3]

## 2. 补齐同一 donor 的 10 个身份缺项

| 缺字段（原键） | 现场应交原始依据 |
| --- | --- |
| `region` | 本机区域/SKU 的设备或铭牌原始记录；说明字段来源 |
| `mainboard_revision` | 本机主板正反面、板号/修订丝印及位置 |
| `runtime_panel_id` | 本机当次实际可读的面板身份与原始命令日志；读不到保留未知 |
| `display_module_part` | 实际显示模组料号标签及对应原厂资料 |
| `display_module_revision` | 同一显示模组修订标识/受控文件 |
| `touch_revision` | 匹配触控部件的实物版本与依据 |
| `pack_A_label` | A 电池完整标签、料号/版本、保护组件关联 |
| `pack_B_label` | B 电池完整标签、料号/版本、保护组件关联 |
| `USB_roles` | 原机实际支持的角色、方向和协商/连接原始记录 |
| `USB_version_rate` | 原机协议/速率身份及实际链路日志；连接成功不等于某指定速率 |

软件驱动家族、同型号另一台机器、网页标题均不能替代实物身份。再次软件读取时保留完整命令输出、失败/超时、连接前后状态及序列号摘要；不把失败读取改写为完整通过。[S1] [S2] [S3]

## 3. 7 个实物角色：标签、三维外形及装拆方向

| 角色（原键） | 除标签外必须采集 |
| --- | --- |
| `mainboard` | 正反面 PCB 轮廓、分区最高元件、屏蔽罩、安装孔/基准、连接器与散热接触面 |
| `display` | 完整模组外形、可视/非可视区域、边缘与固定点、成品叠层；不能只量显示区 |
| `touch` | 是否集成在显示模组、独立厚度/外形（如存在）、控制器/连接器及原配关联 |
| `COF` | 芯片/封装最大包络、尾部总长/宽/厚、不可弯区、固定区、出线和最初弯曲方向 |
| `pack_A` | 完整封装、极耳、保护板、连接器外形；实测质量及有来源的膨胀预留 |
| `pack_B` | 与 A 同项，单独记录，不能借用 A 的规格/尺寸 |
| `USB_port_board` | 板体/插座/配套互连、外壳开口、紧固点、插合和退拔包络 |

集成在同一物件上的多个角色可共用 `part_id` 并列明 roles，不为凑齐清单假造独立零件。每件需有带比例尺的总览、标签特写、正反面和侧视，明确坐标原点/XYZ/基准面，记录轮廓与局部高度、质量/重心（能测则测）、紧固点、禁布区。**分别记录线尾出线方向、连接器插拔方向、零件装入/退出方向与工具操作空间**；附实际过程照片/视频及限制动作。尚不能拆出或测到的量明确保留未知。[S3]

电池还需实际 A/B 料号、容量、标称电压、保护/温度检测/身份线、原充电拓扑及膨胀依据。`4700 mAh` 只是现有系统目标，腔体容积与占位块不能证明容量；原有保护链不因机械重排而省略。[S1]

## 4. 12 个接口：逐端子映射，保留完整原机路径

以下位置是当前设计提案，现场记录实际情况。每个连接器须关联上述真实 `part_id`，记录完整 observed pins、板端身份、针号方向、屏蔽/地/参考、逐网两端和原始证据。未解释的 NC、分叉、混合接口或屏蔽触点继续列缺项；不能删掉实体引脚来制造完整覆盖。[S1] [S3]

| 接口 ID | 待核实功能/原路径 |
| --- | --- |
| `MAIN_DISPLAY` | 原配主板↔显示：显示链路、电源、复位；提案 B↔A |
| `MAIN_TOUCH` | 原配主板↔触控；软件家族名不作为实际针脚；提案 B↔A |
| `A_PROTECTED_PACK` | A 受保护电池↔原电源管理；供电/回路/温度/身份等实际存在的线 |
| `B_PROTECTED_PACK` | B 受保护电池↔原电源管理；提案 B 内部 |
| `A_CHARGE` | 原电源管理↔A 电池的原受保护充电路径；与原双向线束关系须确认 |
| `B_CHARGE` | 原电源管理↔B 电池的原受保护充电路径 |
| `USB_DATA_CROSS` | 原端口板↔原控制器：实际数据对、参考、屏蔽、角色控制；提案 A↔B 连续铜路 |
| `USB_POWER` | 原 VBUS、CC、GND/屏蔽及保护/角色控制；提案 A↔B |
| `CAMERAS` | 原主板↔全部相机模组，连接器/线束与高速链路；提案 B↔A |
| `RF_ANTENNA` | 原射频馈线、同轴、接地及天线位置；提案尽量留在 B |
| `AUDIO_SENSORS` | 原音频/传感器路径；任何移到 A 的部件都须新增明确跨舱记录 |
| `MOTION_STATE` | 新隔离状态传感器及台架读取；没有已识别的 OEM GPIO/软件桥接授权 |

**C01–C26 是独立导通研究网，不能分配成上述 OEM 显示、USB、充电或射频针脚。** 映射完成也不自动批准延长：真实电压/电流、阻抗与速率、屏蔽接地、压降/温升、动态半径与寿命仍须按实际路径闭合。[S1] [S6]

### 原机功能基线必须先留存

在保留匹配原件与原互连的状态下，建立同一 specimen 的开机/供电、A/B 电池读取与原充电、显示、触控网格、USB 数据与角色、相机、无线及音频/传感器基线。保存对应原始屏幕/触控录像、仪器波形、设备/USB/相机/通信日志及明确测试协议。记录 `observed_ok`、`observed_failure` 或 `not_observed`；保留掉线、异常和停止原因。后续改装沿用相同协议与时基映射，不能用零散端点录像证明全动作连续运行。[S3] [S11]

## 5. OLED / FPC：真实叠层与当前尺寸差口

| 对象 | C2 已有研究输入 | 现场/原厂还需给出的事实 |
| --- | --- | --- |
| OLED 几何带 | 宽 `67 mm`、假设厚 `0.2 mm`、总材料长 `187.9 mm`；当前路径最低材料长约 `187.768803 mm` | 实际选定料号/修订/批次、完整外形/总料长、可视区与非可视边、COF/触控/尾部、夹持和不可弯区、实际最大成品厚度与公差 |
| EP5 FPC | 总长 `188 mm`＝自由段 `164 mm`＋两端各 `12 mm`；中段宽 `10.8 mm`、端宽 `12 mm`、两端渐变各 `4 mm`；假设厚 `0.1 mm` | 确切生产料号、铜型/铜厚、PI、胶、覆盖膜、表面处理、补强及补强胶的逐层规格/公差、总厚上下限、走线与出线/夹持实物、供应商工艺能力 |

以上是研究尺寸，**不是供应商已承诺的成品规格或动态验收阈值**。当前 EP5 26 路研究图稿与 188 mm 几何对应，但原生 ECAD 通过也不能证明 OEM 接口、带电载流、信号完整性或动态寿命。[S4] [S5] [S6]

两项已知参考边界必须保留：

- Panox 页面标为 `TA067FM01`，其链接的 preliminary PDF 实际写 `TA067FVMK01-08 / Ver 1.0 / 2022-10-12`。文档外形 `71.940 × 165.680 mm`；相对当前固定路径族，长度至少短 **`22.088803 mm`**，宽度比 67 mm 研究带大 **`4.940 mm`**。文档 `0.408 mm` 是 substrate 厚度，不能冒充完整模组层叠；可靠性章节仍为 TBD。该件未被选用，比较也没有排除所有可能的新路径族。[S7]
- `TOQ667XHT-01C` 公开参考仅列出 POL/Panel/BP 部分厚度合计 `234 µm`，CG/OCA/Embo/Foam/PI/Copper 等仍未全定义，不能作完整成品厚度。FELIOS 条件组合的未加工名义 `51 µm` 同样不是成品 FPC 最大厚度；确切订货码/覆盖膜工艺尚未选定。[S8] [S9]

请取得真实模组/FPC的**受控层叠、材料方向、允许静态/动态弯曲半径、循环次数与温湿度/速度/载荷条件、允许拉力/应变及中性轴依据**；逐层材料参数须与该料号/工艺一致。用同一条带材的材料坐标标记连续记录 STOW→PREDOCK→OPEN 及返回，保存实际最小半径、尾部行程、拉力、平面储存/边缘翘曲和支撑转换录像。尺寸替身只证明自己的几何，不能替真实 OLED 获得弯折资格。[S3] [S4] [S8] [S9] [S10]

## 6. 结构与工艺输入先回交，禁止从 CAD 名义值补齐

- [ ] **单个 roof screw 的 9 项缺值**：预紧最小/最大值，螺钉刚度、夹持件刚度，单钉外部轴向载荷，螺钉拉伸、母螺纹、roof boss、承压各项许用。交采购件/材料/工艺与载荷分配的实际依据；合同明确不假定四钉均分载荷。[S12]
- [ ] **frame screw 啮合 7 项缺值**：头下长度、螺钉座到螺母座距离、螺母高度，公牙头下/尖端不完整段、母牙入口/出口不完整段。**预紧 7 项缺值**：分离载荷、载荷分配系数、总螺钉力许用、预紧离散、预紧损失/增益、所需残余夹紧力。目录名义尺寸不代替采购实物与螺纹有效啮合量。[S13]
- [ ] 记录 guide/槽销、KEY/PAWL、保持件、支撑、夹具、螺钉/螺母的实际件号/批次、材料、加工方法、关键薄壁/间隙/啮合与公差、工具入口和装拆顺序。交实际 BOM、图纸、材料与工艺依据；不同设计版本零件不能混装后当 C2 样件。[S3] [S10]

现场负责真实输入与原始观察，结构分析和工程验收另按这些输入闭合。以上输入没有依据时保持未知，不设任意预紧力、载荷、容差或安全系数来获得通过。

## 7. G3→G4→G5：执行前需补齐的合同

共同要求：试验前冻结样件、计划、阈值出处、测量通道/位置、校准/误差界限、采样及同步要求，并保留预登记批准与独立复核证据。阈值须能定位到选定实物的原厂受控文件、实际工艺/材料依据或经负责人批准的产品要求；不得用已有样本的结果倒填放宽限值。G4/G5 的每个 requirement/criterion 必须带 `source`（path/hash）与 `source_locator`。当前模板中的缺值仍全部待定。[S10] [S11] [S14]

| 阶段 | 必须先具备 | 尚缺来源/值的全部类别 | 现场交回什么 |
| --- | --- | --- | --- |
| **G3 无电运动** | 当前 EP5 v2 绑定；同一实物的 CAD、routing、BOM、图纸、材料、工艺、固件角色证据与实际装配偏差；预登记计划、校准与同步依据 | **采集 5 类**：最低循环数、每阶段最低样本数、最低松手保持时长、最大采样间隔、最大时基对齐误差。**验收 14 类**：操作力上限；左右 y/z 偏差上限；回位 y/z 偏差上限；y/z 行程上下限；松手 y/z 漂移上限；OLED 尾部行程上下限、拉力上限、最小半径下限；FPC 最小半径下限、26 路电阻上限 | 连续位移/力/半径/尾部/26 路电阻原始数据，完整动作窗口，实际保持件与支撑安装/拆卸、松手状态及左右操作偏差视频；每循环单独覆盖，保留卡滞/脱落/断路和提前停止 |
| **G4 带电全动作** | **同样件、同 commit/源字节、当前 EP5 的真实 G3 pass**；同 donor 的完整物理身份和 12 接口；原机基线；实际材料/工艺/固件/装配；9 个功能的有来源测试协议 | **采集 4 类**：每供电模式最低循环数、每阶段最低样本数、最大采样间隔、最大对齐误差。**验收 14 类**：电源轨电压范围、总电流范围、异常复位次数上限；A/B 各自电流与温度范围；USB 错误/掉线次数上限；显示错误、触控位置误差、相机错误、RF 错误、音频/传感器错误各自上限；每条真实电源轨/通道还需身份与测点依据 | 两种原系统供电模式（`original_battery`、`original_charging`）下，完整 17 阶段×9 功能（power、pack_A、pack_B、usb、display、touch、camera、rf、audio_sensors）的原始观测、通道日志与动作窗口；错误事件也必须保留 |
| **G5 寿命/工艺** | 每个样件均有**同 commit/源字节的真实 G3 与 G4 pass**；样件/批次清单、实际工艺及装配身份；预登记完整循环定义与检查点 | **采集/规模 5 类**：寿命循环目标、最少样件数、最大曝光采样间隔、每曝光阶段最低样本数、最大对齐误差；另需预定检查点（含 0 和最终循环）。**耐久 8 类**：操作力、解锁力、左右偏斜、复锁误差、保持漂移、FPC 电阻、显示错误、USB 错误的上限。**暴露 4 类**：温度、湿度、运动速度、施加载荷的范围。**工艺**：关键尺寸清单及每项上下限/测法/校准来源，当前清单为空 | 每样件逐采样的原始暴露/动作时间记录与 17 阶段窗口；从原始数据独立重算循环编号、顺序、极值及跨阶段/跨循环最大采样间隔，并与 cycle CSV 核对；各检查点 8 指标、每样件工艺尺寸、失效/停机及维修换件原件 |

**共同的 17 阶段顺序**：锁定基线 → 左解锁 → 右解锁 → 滑出 → 就位 → 左保持件装入 → 右保持件装入 → 支撑装入 → OPEN 松手保持 → 支撑拆除 → 右保持件拆除 → 左保持件拆除 → 退出就位 → 滑入 → 右复锁 → 左复锁 → 最终锁定。必须保留这些实际手动附件动作，不能把理想同步轨迹或全程手扶替代操作与保持证据。[S10] [S11]

**结果处理**：未覆盖、缺来源、缺校准或误差区间跨限，保持 `unknown`；明确观察到的失败保持 `fail`，即使同一记录还有缺项。G5 只交汇总极值/循环数仍属 `summary_only_not_qualifying`；修理/换件必须留记录，不能写成同一样件未经中断的寿命。任何阶段的 pass 仅限其声明且采样到的协议，不自动变成整机或制造放行。[S10] [S11]

## 8. 本次现场回交与签收

回交一个新建、不可覆盖旧记录的 evidence 目录：身份/7 角色清单、12 接口及缺项表、尺寸原始表、原机功能基线、OLED/FPC 受控资料、结构输入出处、批准的试验计划、校准/时基、原始数据/视频、实际偏差和失败/停机/维修记录、完整 manifest。没有采到的量明确列缺口与负责人，不能自动补齐。[S3] [S10] [S11]

现场负责人：________　样件编号：________　采集日期/时区：________　工程接收人：________

### C2 不可变来源

所有下列链接固定到同一 C2 commit；它们是合同/既有记录依据，不代表本次已发生实物试验。

[S1]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/design/product_interfaces.json
[S2]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity/record.json
[S3]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/product-integration-20261018/hardware/IMPORT_EVIDENCE.md
[S4]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/design/product_geometry.json
[S5]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/design/product_routing_ep5.json
[S6]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/integration/product_ep5_ecad.py
[S7]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/product/OLED_SOURCE_RECHECK.json
[S8]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/controlled-inputs-web-20261013-r6/candidate_facts.json
[S9]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/fpc-felios-primary-search-20261013-r6/source_facts.json
[S10]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/product-integration-20261018/physical-test-followon-20261019/qualification_contract.py
[S11]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/integration/product_qualification.py
[S12]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/integration/roof_joint_load_inputs.json
[S13]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/integration/frame_thread_actual_inputs.json
[S14]: https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb/engineering/engineering-integration-20261025/product/build_product_delivery.py

- [S1 接口与 donor 合同][S1]；[S2 已有软件身份原件][S2]；[S3 现场证据格式与导入约定][S3]。
- [S4 OLED/整机几何][S4]；[S5 当前 EP5 路由][S5]；[S6 同版 FPC 研究图稿生成器][S6]。
- [S7 OLED 尺寸差口复核][S7]；[S8 TOQ 参考叠层缺口][S8]；[S9 FELIOS 成品工艺缺口][S9]。
- [S10 G3 EP5 v2 资格合同][S10]；[S11 G4/G5 原始采集与来源合同][S11]；[S14 C2 交付模板生成器][S14]。
- [S12 roof screw 实际载荷输入][S12]；[S13 frame screw 啮合与预紧输入][S13]。
