# 同一试件的无电运动资格契约

该入口把真实采集的观测转换为范围明确的 `pass / fail / unknown`。它不能把已有 donor 读回、有限 CAD 检查或测试夹具数据转成整机资格。

本实现只评价 **同一已识别样件、预声明程序、实际采样点** 的无电运动。任何结果中的 `manufacturing_go`、`fixture_fabrication_go`、`physical_phone_verified` 都保持 `false`。没有采到掉线也不能证明采样间隙内没有掉线，`absence_of_unsampled_dropout_proved` 固定为 `false`。

## 1. 输入与身份闭合

原有 `razr-unpowered-motion-acquisition-v1` manifest、校准和 CSV 继续兼容。新增：

- `qualification_plan`：相对采集目录的 `{path, sha256}`，内容采用 [qualification-plan.template.json](qualification-plan.template.json)。
- `as_built_specimen_record`：同样的文件引用，采用 [as-built-specimen.template.json](as-built-specimen.template.json)。
- `acquisition_started_at_utc`、`acquisition_ended_at_utc`：由原始同步记录支持的实际区间，显式 UTC；不能为了使方案显得提前而改写日期。新资格记录中的 `recorded_at_utc` 指该采集记录成稿时间，必须不早于实际结束时间；旧观察记录缺少起止字段时不追加这个条件。
- `design_binding.artifact_roles`：下面七种身份角色，每种包含非空、不重复的仓库相对文件路径；每个路径必须同时存在于 `files_sha256`。
- 可选 `qualification_plan_version`：`{git_commit, path, sha256}`，固定方案在 Git 中的精确内容。纸质原件可在试验后导入，因此该提交不要求早于采集。Git 提交时间本身不证明预登记时间。

`design_binding` 必须在采集 manifest、方案与 as-built 记录中完全一致。物理采集同时核验工作区字节和指定提交的真实 Git blob；仅修改 SHA256 列表以适配脏工作区不能通过。方案与 as-built 记录的每个原件都必须有精确 SHA256。分析结束统一复核全部已读引用，包括校准文件和原件、阶段、坐标系、同步、阈值、资格文件、CSV 与设计，不能在首读后替换附件仍获得有效结果。

| 角色 | 应冻结的内容 | 本项目现状与边界 |
|---|---|---|
| `cad` | 所用完整 CAD 构造器、全部有关参数/依赖、交付 STEP 或其受控清单 | 可从当前 `integration/product_scene.py` 及实际选择的分件入口追踪；只绑定 geometry/interfaces 两个 JSON 不完整 |
| `ep4` | `integration/product_routing_ep4.py`、`design/product_routing_ep4.json`、实际端接/线束版本 | 原生几何结果只适用于其绑定版本；新壳体不能继承旧版本结果 |
| `bom` | 真实加工/采购件、数量、版本、批号、替代批准 | 现有 `engineering/product-integration-20261018/electrical/research-BOM.csv` 是研究 BOM；文件存在不能证明实物装配与其相符 |
| `drawings` | 正在制造的有版本尺寸图、公差、装配和端接图 | 未确定的图纸必须继续为未知；不以 CAD 截图冒充制造图 |
| `material` | 材料牌号/状态、批次、厚度/弹性参数依据、适用原件 | 当前未定材料不能用占位值补齐 |
| `process` | 真实加工/连接工艺、作业版本、装配顺序、连接/保持原始记录 | 薄环、底盖、螺纹对端与焊胶变形未解决时，不能只因名义材料重合而写已完成 |
| `firmware` | 被测试设备实际固件/构建身份和试验配置，或确属无固件无电夹具的受控配置声明 | 无电方案不生成新的固件测试结论；所用仪器与设备仍应有实际身份记录 |

每个 as-built 角色观测要求 `part_or_lot_id`、`method`、`locator`、`observed_at_utc`、与分配文件完全一致的 `design_paths`，以及非空 `original_evidence`。照片、铭牌、实测图或作业原件由有资质的验收人员核对；程序验证字节与引用，不声称自动识别照片真伪或判定某材料/工艺适用。

本契约是采集分析入口的新 schema，不把它塞入 donor 的 `import_hardware_evidence.py` 分发器。后者保留原 donor / 端子 / 尺寸 / 功能证据的语义，不能因一个新的运动判定而改写其平台冻结状态。

## 2. 在实际采集前声明什么

方案 `schema` 为 `razr-unpowered-motion-qualification-plan-v1`，范围仅支持 `unpowered_motion`。三个模板均为 `is_template: true`；未完成模板不能 PASS。**模板不包含本项目虚构的数值限值**，所有 `null` 都需要由真实器件、试验目的、测量能力及责任工程师的依据确定。

方案冻结以下内容：

1. 完整 `design_binding`、`declared_at_utc`、`approved_by` 和审批原件。
2. 与采集一致的完整 `planned_phase_order`。不能试验后删去失败阶段。
3. 最少循环、每阶段最少采样点、每段松手持续时间、最大采样间隙和最大时钟对齐误差。共享硬件时钟允许声明并要求零额外对齐误差；其他这些采样数量和时长要求需为正。
4. 下面所有判定限值及固定单位/方向。

| 指标组 | 判定量与方向 |
|---|---|
| 操作与同步 | 操作力、左右 Y/Z 偏差、回程 Y/Z 偏移，分别使用上限 |
| 行程 | **每个循环**的 Y 全程、Z 就位程使用上下限，完整循环不能掩盖另一个短行程循环 |
| 松手保持 | 每段连续无手接触观察的 Y/Z 最大漂移使用上限；有缺口时不能拼成连续保持 |
| OLED | 每循环牵引端行程使用上下限、拉力用上限、最小半径用下限 |
| FPC | 最小半径用下限；26 根导体在全部采样点的最大阻值用上限 |

无电整套资格需要 5 路基本运动/力、4 路 OLED/FPC 几何/拉力以及 26 路导体，共 35 路。旧分析仍可只有基本路数；缺 OLED/FPC 数据时相应资格不能 PASS；有效已测点若已证明超限仍为 FAIL，其余为 `unknown`。没有采集的导体、空值或 `OVER_RANGE` 都不会被填成零或推定导通。

此处 26 路采样阻值判断不覆盖高速信号质量、USB 枚举、电池保护、发热、寿命或短于采样间隔的断续。外部操作力也不会变成内部 KEY 载荷或真实 FE 支承。

## 3. 两种预登记核验方式

本地 Git 提交时间、文件修改时间和自己填的日期均可以回填，因此单独出现不会自动证明预登记。这里保留两条已有工程工作可采用的核验路径，不要求签名服务或新增软件依赖：

- `observed_controlled_version_time`：独立验收人核对受控版本与其实际已观测时间的原始证据。审核记录的 `controlled_version` 必须等于采集所引 `qualification_plan_version`，程序核验提交中的精确方案字节。**仅贴一段本地 Git 时间输出不构成独立核验**。
- `independently_reviewed_preregistration_document`：独立验收人明确核验事先登记的文档及其原件。可使用已有签名纸质登记、审批系统或可追溯原始记录。核验可以发生在试验后，登记本身必须在采集前。

验收者从 [preregistration-review.template.json](preregistration-review.template.json) 建立记录，通过 CLI `--preregistration-review` **显式选取**；采集 manifest 中自带同名字段不会批准自己。审核记录应位于受控验收资料中，存储位置不代替权限管理。

记录绑定方案 SHA256、整份 acquisition manifest SHA256、样件 ID 与 `design_binding` 摘要；改阈值、换样件、替换日志/校准引用或回填采集时间，都需重新独立核验，旧审核不能复用。它还记录核验者、独立性、方法、原件、核验说明、已经核验的登记时间和审核时间。审核原件不能缺失。审核结论未确认时使用 `unverified`，输出保持未知。

设计摘要为 Python 等价表达式：

```python
hashlib.sha256(json.dumps(
    design_binding, sort_keys=True, separators=(',', ':'), allow_nan=False
).encode('utf-8')).hexdigest()
```

这个接口的信任边界是**调用者显式选取的人工核验声明**。通过引用与时间检查后，输出 `caller_supplied_review_attestation: true`，仅说明接收了该声明；`reviewer_identity_or_independence_authenticated_by_program` 固定为 false，不声称机器已验证审核者身份或独立性。程序不认证审核者身份、纸质签字或外部系统，报告因此保留 `attachment_authenticity_independently_proved: false`。没有审核原件时可照常分析数据，预登记资格仍为 `unknown`；不得通过放宽校验或虚构审核记录消除未知。

## 4. 判定语义

误差采用校准给出的保守绝对误差界。左右差相加；平均位置的两时刻差使用两侧误差合计；单通道全程使用两倍误差。接受区间边界包含等号。所有派生均值、差值、行程、误差和区间必须有限且有序；均值使用避免先相加溢出的计算。若物理读数的浮点表示/计算精度已经比所声明测量误差更粗，输入拒绝；这是数值一致性要求，没有增加任意物理量级上限。

- `pass`：测量区间完全处于预声明限值内，并且完整身份、采样/循环要求、as-built、审批与独立预登记核验均满足。
- `fail`：至少一个有效测量区间已经证明超限。另有缺测也不会抹掉失败，例如 8 Ω 已超过 5 Ω 时，另一根导体缺数仍保留 FAIL；已测 2 mm 小于 4 mm 半径下限时同样如此。
- `unknown`：缺数据、缺限值、误差跨界、未完成循环、缺松手连续时长、采样/对齐不足、样件角色缺项或未核验预登记等，前提是没有有效已知失败。部分采样的行程只能作为全程下界：已超过上限可 FAIL，低于所需下限时可能只是漏采，保持 UNKNOWN。每项输出保留 `observation_coverage` 与缺测数量。
- 拒绝输入：文件 hash 不符、设计/样件错配、非法单位、校准范围外/非有限计算、错误时间顺序、复用与当前方案不同的审核或提交等。CLI 返回 2，不能留下一个看似有效的新判定文件。

`synthetic_fixture` 即使数值指标全过，资格总状态仍为 `unknown`。单元测试为覆盖验证器正路径，会在临时目录内创建明确标注的合成物理 schema 夹具；它们会删除，不进入实物记录，也不代表现实中通过。

Y/Z 行程和 OLED 牵引端行程的覆盖还须逐循环核验完整阶段顺序、每阶段预声明最少采样数、以及计入两时刻对齐误差的最大采样间隔。只要其中任一项缺失或不满足，该循环的范围就按部分观察处理：已测范围的下界超过上限仍可 FAIL，低于要求的下限保持 UNKNOWN。存留下来的行中所有通道单元格都有数值，不能证明整个循环已经采全。输出分别保留 `channel_coverage_complete` 与 `cycle_protocol_coverage`，后者列出具体未满足的采样条件；`missing_observations` 只统计现有行中的通道缺测，不推算未采行数。

已绑定真实记录的 `pass` 也仅是上文限定的已采样无电程序。加载完整整机、长期循环、保持/拉脱、连续无掉线、电源/显示/触摸/USB 和制造资格仍需各自证据。

## 5. 运行与最小验证

取得真实采集和核验文件后，写入一个全新输出文件：

```bash
python -B engineering/product-integration-20261018/physical-test-followon-20261019/analyse_motion_log.py \
  --manifest /absolute/path/to/specimen/acquisition.json \
  --repository /absolute/path/to/RAZR-SLIDE \
  --preregistration-review /absolute/path/to/acceptance/preregistration-review.json \
  --output /absolute/path/to/specimen/motion-analysis-NEW.json
```

省略 `--preregistration-review` 可继续生成观察结果，资格预登记状态保持未知。所有结果先通过严格有限 JSON 序列化，再独占创建输出，拒绝输入不会留下截断 JSON；已有输出不能意外覆盖以前的测量结论。

本变更的最小回归为新资格契约测试，以及原 `test_physical_followon.py` 的 `MotionAcquisition` 组：

```bash
python -B -m unittest discover -s integration/product-study-tests -p test_qualification_contract.py -v
python -B integration/product-study-tests/test_physical_followon.py MotionAcquisition -v
```

本次没有重启 PR35 接触求解，没有把有限 CAD 几何测试计为实物测试，也没有重新运行不受这个采集改动影响的原生 CAD 装配测试。

## 6. 当前能合法继承的原始证据

基线 `e25cf001c1b714514d501de4c16d1592fde06b61` 的
`hardware/records/xt2551-3-20261020-f4db100-identity/`
保留真实 donor 的身份读回，模型为 XT2551-3。该记录只有模型身份项已知，十项平台/显示/电池/USB 身份仍未知，七种原始部件角色未完成，`platform_frozen` 与 `physical_phone_verified` 为 false。该目录没有能输入本分析器的真实运动、操作力、OLED 或 26 路 FPC 原始采样 CSV。

因此这份 donor 记录能保留为真实身份来源，**不能填入完整 as-built 或替代无电运动试验**。已有 OEM 容量资料也不能证明新壳体与实际 A/B 电芯安装、电气或热性能。

PR35 的 `numerics/restart-cache-preflight.json` 明确记载已扫描原主机 3292 个文件但没有识别到 bearing response restart；`current_bearing_cache_restore_verified` 为 false。这里没有新的恢复成功声明。

下一批最小原件是：所选同版完整设计和制造包；具体样件七类身份/原件；预登记方案及核验材料；35 路带校准和同步依据的原始采样与阶段/无手接触视频或等价证据；实际失败与返修记录。未知限值、材料或工艺需先由责任工程师在受控方案中确定，不能由分析器猜测。

