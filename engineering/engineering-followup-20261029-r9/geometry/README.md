# R9：S4 完整 factory 的原十态有限几何结算

原十态执行完整：**True**；十态有限姿态全部通过：**True**。
十态的 producer 与独立 reader 各覆盖 **118,909 个无序体对**。其中 R9 新执行八态、各 **95,347 对**；R7 两个中途姿态的原完整结果保留，另有本轮原封存逐行复核。完整连续 G2、真实机构允许域、当前几何强度与 G3–G5 资格仍为未决。

机器可读总账：[R9_GEOMETRY_SCOPE.json](R9_GEOMETRY_SCOPE.json)。R9 八个新态的原 BREP、STEP、全对 JSONL、材料与端部控制、独立读回和全部失败/中止记录在 [R9_GEOMETRY_ORIGINALS.tar.gz](R9_GEOMETRY_ORIGINALS.tar.gz)；其逐成员 SHA256 清单与完整读回见 [RAW_EVIDENCE_MANIFEST.json](RAW_EVIDENCE_MANIFEST.json) 和 [ARCHIVE_READBACK.json](ARCHIVE_READBACK.json)。R7 近/远两态的完整原件保留在各自原封存 ZIP，总账另列两包的原 SHA256、保存身份与本轮逐行读回引用，没有混入新执行计数。

## 十个原注册输入与实际矩阵

| 原状态 | 证据批次 | 体数 | producer / reader 全对 | native Common / 正轴隙（producer） | 原早期门 | qL / qR (mm) | 有限姿态通过 |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `stow_tabs_0` | R9 新执行 | 154 | 11,781 / 11,781 | 796 / 10,985 | 18 | 0.0 / 0.0 | True |
| `stow_tabs_3` | R9 新执行 | 154 | 11,781 / 11,781 | 794 / 10,987 | 18 | 0.0 / 0.0 | True |
| `near` | R7 原完整结果 | 154 | 11,781 / 11,781 | 777 / 11,004 | 12 | 3.482188470506243 / 3.482188470506243 | True |
| `far` | R7 原完整结果 | 154 | 11,781 / 11,781 | 747 / 11,034 | 12 | 9.160729490168748 / 9.160729490168748 | True |
| `predock` | R9 新执行 | 154 | 11,781 / 11,781 | 740 / 11,041 | 18 | 12.0 / 12.0 | True |
| `open_installed` | R9 新执行 | 161 | 12,880 / 12,880 | 813 / 12,067 | 18 | 12.0 / 12.0 | True |
| `lower_L_contact_R_free` | R9 新执行 | 154 | 11,781 / 11,781 | 794 / 10,987 | 15 | 0.0 / 0.03009404388714734 | True |
| `lower_R_contact_L_free` | R9 新执行 | 154 | 11,781 / 11,781 | 794 / 10,987 | 15 | 0.03009404388714734 / 0.0 | True |
| `upper_L_contact_R_free` | R9 新执行 | 154 | 11,781 / 11,781 | 740 / 11,041 | 15 | 12.0 / 11.969905956112857 | True |
| `upper_R_contact_L_free` | R9 新执行 | 154 | 11,781 / 11,781 | 740 / 11,041 | 15 | 11.969905956112857 / 12.0 | True |

全对数包含原 `strict_common` 允许的正轴隙证书，不能当成直接 Common 调用次数。OPEN 使用真实 161 体、12,880 对；其余各 154 体、11,781 对。八个新态的 producer 与 reader 两份实际行序列均逐项等于完整 `combinations(sorted(participants), 2)`，不是只对计数。这八个新态的 reader 先独立读入全部 STEP 与 BREP、执行完整材料双向差及原签名门，再运行原功能接触门和全对矩阵。

OPEN 的方法计数分别为 producer 813 native Common / 12,067 正轴隙，reader 817 / 12,063。两侧各有 `TELESCOPE_2_BOTTOM_CAP` 对 `TELESCOPE_3`、对 `TELESCOPE_3_CORE_BOTTOM_SHOULDER` 的冻结轴隙从 1.1102230246251565e-16 mm 变为 STEP 读回的 0，因此 reader 多走四次原 native Common；这四次体积均为零。完整 12,880 对的 Common 和原分类一致，方法分支并非全相同。全部行、冻结边界与界差保留在 [OPEN_STEP_METHOD_BRANCH_DIFFERENCES.json](OPEN_STEP_METHOD_BRANCH_DIFFERENCES.json)，原阈值没有改变。

证据分为三层：K1 `key_forward_loop_v1` 的近/远完整 11,781 对；K3 `panel_key_travel_stops_v1` 的早期 STOW/PREDOCK 153 个 panel-only 对；最终 K1+K3 完整 factory 的十态全对。早期 153 对没有计入最终全对总数。

## 原中途失败与材料身份

功能源码锁定 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`，Git tree 为 `cdd9e2c41216201b6cd04dd610d45fde80499045`。原归档源码/输入闭包的 973 个文件与实际 fetched S4 Git blob 逐个相同，缺失和不符均为零；这项比对不声称已重放原 43 包运行环境。原 helper、输入合同和每份实际报告均由 SHA256 绑定。

近姿态 slide=23.142044210239405 mm；远姿态 slide=60.880681403413135 mm。K1 原报告明确保留了修复前 S4 whole-factory 与原 F1a 材料映射：154 参与体的双向材料差为零，包含两侧 KEY 与整个 panel。修复前 panel/KEY 的直接 Common 保持如下真实失败：

| 原见证 | L Common (mm³) | R Common (mm³) | 相对原 F1a 差值 |
| --- | ---: | ---: | ---: |
| near | 0.24558784938224815 | 0.2455878493822482 | L=0.0, R=0.0 |
| far | 0.23013738353925134 | 0.23013738353925126 | L=0.0, R=0.0 |

这些失败未被候选修复的通过结果覆盖。上表是 factory 的原碰撞数值与其 F1a 对应差；历史独立 reader 仍保留约 1e-13 mm³ 的真实差值，满足原 1e-7 判据，没有改写成逐 bit 相同。当前 factory 还把 freshly constructed 原 KEY 逆平移到 q0，与 retained whole 原 KEY 比较；命名 K1 KEY 与 K3 panel 的完整材料也分别与原候选比较，独立 reader 再检查 STEP/BREP 和 q0 KEY 对应。

## 命名修复、切除材料与功能接触

K1 `key_forward_loop_v1` 每侧真实切除约 0.594 mm³、增加约 2.623824 mm³。原名义桥局部 YZ 截面为 1.5×0.36=0.54 mm²；新增 U 腿局部 XZ 截面为 0.38×0.36=0.1368 mm²，所声明两个不同位置/方向局部截面之比约 25.333%。原 yoke tab 还保留 0.25×0.30=0.075 mm² 的源名义截面，该数也不是全 KEY 最小截面测量。cutter 外包 1.10×1.52×0.38 mm 与实际原 web 的名义切除 1.10×1.50×0.36 mm 不同；本轮没有全 KEY 最小壁厚、最小截面或强度资格。原 protected pawl end、cam/stop 与 coupling-yoke 区域的定向材料差仍逐项保留。

K3 `panel_key_travel_stops_v1` 为 panel 增加 4.624559999999989 mm³，切除量为零；完整新旧 panel 材料账、四个实际正体积连接和原 cover 功能面双向面积差均保留。新增 Y 向 lower stop 对应 q=0、upper stop 对应 q=12，原声明接触面积 0.3239999999999998 mm²。每个适用端点执行相反法向、同平面接触面积、whole KEY/panel Common、0.001/0.01 mm 越程相交及内向释放。越程控制是单独 whole KEY 与 panel 的几何检查，未构造越过原 profile 域的完整 factory，也不证明实物行程、力、预紧或疲劳。

## 正 q 的 cam STOP/SPRING 与独立域

cam `STOP_i` 由 profile 的 height 驱动 X 向平移；K3 panel 的行程接触是 Y 向，两者不同。四个原 profile 的精确 binary64 断点及全部十态源输入保留在 [SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json](SOURCE_ALLOWED_DOMAIN_TEN_STATE_READBACK_V2.json)。

| cam 分段 | q 区间 | 含义 |
| --- | --- | --- |
| plateau | q=0 与 (0,a]，a=0.0011145618000001356 | 初始高度段 |
| rounded_corner | (a,b)，b=0.09055728089999172 | 圆角高度段 |
| ramp | [b,c) | 斜坡高度段 |
| lower_stop | [c,12]，contact0 c=0.6429179606749895；contact1 c=0.64291796067499 | cam 的低高度段；不是 KEY 的 Y 行程下限 |

异步低端 q=0 与 0.03009404388714734 分别落在 plateau 与 rounded_corner；异步高端 q=12 与 11.969905956112857 都落在 cam lower_stop，仅一侧处于 K3 Y 向 upper 接触。STOP 平移为左右符号乘 `height(q)-height(0)`；SPRING 的 X 包络端点随该平移取 min/max。八个新态的 64 个原 STOP/SPRING native 边界与原 q0 材料及源预测逐项比较，见 [NATIVE_PROFILE_EIGHT_STATES.json](NATIVE_PROFILE_EIGHT_STATES.json)。SPRING 是半径 0.43 mm 的 OD 容差包络，未取得真实弹簧自由长、刚度、预紧或力学接触维持证据。

软件域共享 slide∈[0,79.75]、descent∈[0,8.2]，正 descent 要求 full slide。两侧各自 tab∈[0,3]、flank∈[−1,1]，dq/dx 受各侧槽约束；q=K·slide+dq，K=12/79.75，必须在原 profile 的 [0,12] 中且不钳位。各侧 telescope 的三个关节独立受端点与总长约束，默认等分分配不是实物强制约束。OPEN hold/support 只在 full slide/full descent 安装条件下定义。有限十态覆盖不能把这些软件条件升级为真实可达域、所有容差支路或连续碰撞证明。

## 原判据下的执行提速与失败保留

原 v1 的首态完整 factory 与 11,781 对确实执行；随后受控中止四态 campaign，第二态的 352 个部分文件原样保留。初次同命名空间以外的停止尝试出现 ESRCH，原错误、成功的 owned-stop 记录和结束状态分别保存，原 campaign 的 completed=false 没有改写。

另命名 frozen v2 先对每个实际参与体执行原完整拓扑、正有向体积与 AddOptimal 边界检查，并冻结 BREP 指纹。严格正轴隙使用这些冻结的界；潜在相交仍在几何深拷贝上调用原 `strict_common`。全矩阵结束后要求原参与体 BREP 指纹不变。独立 reader 自行实现该冻结过程，显式调用 OCP copyGeom=True、copyMesh=False，并保留原 1e-7 mm³ 判据。

首态 v2 pilot 使用 v1 已保存材料做完整 11,781 行对照；逐行 method、符号、Common 体积、分类与失败集合一致，最大 Common 差为零；边界 readback 的最大轴隙差为 2.842170943040401e-14 mm，二者分别记录。pilot 不是第二次 factory，也不是独立 reader。独立 STEP/BREP reader 另有完整执行记录。

v3 剩余四态沿用同一冻结判据与全部原输入，开跑前冻结四个 producer 与已完成前三个 reader 的实测容量；当时最后一个异步 reader 明确记录 pending。调度上限为一个 producer 加一个 reader，3600 s producer 预算；计划值不是实际完成声明。
共享 cgroup 在 v3 启动前已记录 OOM 事件，其后又观察到计数增量；每个观测点记录当时仍在运行的本任务 worker，已结束 worker 则另有实际退出记录。事件原因和受害者未被识别。容量原快照、后续资源观测、每个实际 worker 的完成/退出状态分别保留，资源事件不改写科学结果。

## 本轮结论边界

这里完成的是命名当前几何的原十态有限覆盖与材料/来源审查。全连续独立控制与浮点容差壳、profile 外真实槽状态、实际弹簧/接触力、完整工艺和公差、当前几何 FE、实物装配与维修路径、真实 OEM 电气身份及 G3→G4→G5 逐级实测仍需各自原件。本报告保持 `full_continuous_G2=false`、`physical_allowed_domain_proved=false`、`G3_G4_G5_qualified=false` 和 `manufacturing_go=false`。

## 独立交叉复核原件

- [R9_GEOMETRY_TEN_STATE_INDEPENDENT_FINAL_LEDGER.json](../independent-review/R9_GEOMETRY_TEN_STATE_INDEPENDENT_FINAL_LEDGER.json)，SHA256 `e8ccabda20dfa2754c1f70772148c061edc9604c8cd68b3c2a4a825515ca72f9`。各文件只证明其明列实际读回范围。
- [R9_GEOMETRY_ORIGINAL_ROSTER_AUDIT_V2.json](../independent-review/R9_GEOMETRY_ORIGINAL_ROSTER_AUDIT_V2.json)，SHA256 `57a821c48789c38e2a48e52030a4b476e8c1ff68a674b92fcbac181acce8389e`。各文件只证明其明列实际读回范围。
- [R9_ORIGINAL_NEAR_FAR_FULL_MATRIX_READBACK_V2.json](../independent-review/R9_ORIGINAL_NEAR_FAR_FULL_MATRIX_READBACK_V2.json)，SHA256 `c38776907bef0515bcf81a1bdd59a7db139929ef0118c34adc9537de9936a65b`。各文件只证明其明列实际读回范围。
- [R9_K1_K3_MATERIAL_AND_DOMAIN_CROSSREVIEW.json](../independent-review/R9_K1_K3_MATERIAL_AND_DOMAIN_CROSSREVIEW.json)，SHA256 `fa6b60718098e5791ec2d7264f6a28cce5788ed8d43145be9b5ffc8d437fa1f3`。各文件只证明其明列实际读回范围。
- [R9_FROZEN_PREDICATE_SOURCE_REVIEW.md](../independent-review/R9_FROZEN_PREDICATE_SOURCE_REVIEW.md)，SHA256 `8a39d2dee405a306d8575c1b81d98ac3029a8c7291fb4ac2d3dc36d953eac7d4`。各文件只证明其明列实际读回范围。
