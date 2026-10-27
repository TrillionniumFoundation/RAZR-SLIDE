# L5：完整同轴分层扫掠，原七例与当前完整 B_SHELL

状态：具名源码与原件绑定已准备，尚未执行 L5 native。`cylindrical_sweep_l5.py` 与 S4 / V2 / V3 / V4 分开，不改默认 factory、旧报告、原 predicate 或原阈值。当前对象为 K1 下未改变的完整 B_SHELL 和原伸缩材料；任何结论不自动覆盖 K3 的新 panel / stop、真实独立 5D 域或 SEATING。

## 问题定位

L1 原 `case-011/012/013/014/016/017/018` 分别是 B_SHELL 对 L_TELESCOPE_2、L_TELESCOPE_3、左下/上 cam 法兰、R_TELESCOPE_2、右下/上 cam 法兰。原 full-q specification 已把 q 与 s 放在同一斜向向量，B 相对伸缩件为 `(±1,319/48,0)*q`。不存在可以重新“补回”的共同 q，也不能把这两体当作相对静止。

L2 已消除原 evaluation error，但七原例仍是保守包络交叠。其完整圆柱面被 V2 的世界坐标区间 carrier 包围，可能丢掉斜线轨迹周围的圆形截面。这个机制解释了为什么应试分层 capsule；它不是七对不存在真实碰撞的证明。特别是 case-014 的原 L2 `1.2793811944413415e-7` 继续严格记失败，不调 1e-7。

首 V4 的保留独立 reader 实际报告 17 对中 10 clear / 7 unresolved、262 调用，但导出仅保住两个文件。不能只按数量认定其七个未决就是上述七个 telescope 对。V4a 保持原 17 对同算法，重新取得各自身份、时钟、完整材料和 regions。

## 完整材料与源律

`L5_ORIGINAL_SEVEN_BINDING.json` 绑定原 L1 run 40210275856 / E17 artifact 12605676028、原 raw JSON 与两侧完整 BREP/STEP 的 SHA/字节数，以及 S4 源文件。圆环表来自 SHA 锁定的 `captured_follower_assembly.py:source_geometry`，不是从碰撞后删材料拟合。

| 当前 whole role | 原分件表 | 层 (外半径, 内半径, 局部 z0, z1)，mm |
|---|---|---|
| L/R_TELESCOPE_2 | TUBE_2_OPEN_BOTTOM | (0.75,0.4,0,0.2)；(0.6,0.4,0.2,3.1)；(0.6,0.25,3.1,3.2) |
| L_TELESCOPE_3 | CORE_STEM | (0.2,0,0,3.15)；(0.4,0,3.15,4) |
| 左/右 CAM_LOWER_FLANGE | CAM_LOWER_FLANGE | (0.65,0.4,3.3,3.5) |
| 左/右 CAM_UPPER_FLANGE | CAM_UPPER_FLANGE | (0.65,0.4,3.8,4) |

这些角色和分件减材关系已获独立源码审阅：T2 仅剥离底盖；T3 剥离底肩和两法兰后保留全部 stem。七对合计 12 层。q0 绑定原 `verify_slide_native` 的显式 reference `j=float(Fraction(17,6))`，给出 j=2.8333333333333335；T2 origin Z=6.366666666666667，core / cam flange origin Z=9.2；XY=(sign·7.25,81.5)。`prototype(telescope_offsets=None)` 的默认 `.1+8.2/3` 是另一条调用分支，不能替代原 SLIDE / L1 / V4 的实际参数。反向固定完整 B_SHELL 后，L 的向量是 (−1,−319/48,0)，R 为 (+1,−319/48,0)。T2 独立 Z 增量为 [−1/15,2/15]；其他这些分件没有独立 Z 增量。

每次 native 均先重建所有原圆环层，再将真实完整伸缩件按同一 z 层切片。逐层双向差、全层 union 与整个真实输入双向差，以及逐方向层差总和都要满足原 1e-7。不能用近似体积相等代替。输入与实际切片、重建层、union、carrier 在检查前写 BREP，失败留对应签名和已得到的原件。

## 连续包含

对一个原层 `A={r≤|x|≤R}×[z0,z1]` 和完整平面线段 S，保守填孔扫掠是 `capsule_R(S)×[z0+eta_min,z1+eta_max]`。同一层的 q 与 Z 分配在原 nominal 合同内独立，所以包含整段 q、整段 eta 的全部材料；只检查端点不是此论证的依据。

可选保孔版本对 outer capsule 减去两端 inner disk 的交集。对任何点，沿线段的距离连续，其最小值决定是否落入外盘扫掠，最大值在两端取得；因此 inner-hole 共交只需两端圆盘。若线段长度至少 2r，inner disk 共交没有正体积，长行程扫掠本来就是实心 capsule。短段不得擅自丢弃；源码使用一个按完整 L1 位移界扩大半径的圆柱作保守盖。零长度和非零极小长度保持不同来源记录。

原 source Fraction q/向量/Z 区间全部保存，同时保留理想源向量与原spec已记录binary64系数作为精确数的两条完整仿射中心线。每条线与实际binary64端点线之间的误差，以端点误差的凸包给出整个连续段的有理L1界；取两者最大值增大外半径、缩小可切除内半径，Z 端点向外转换。还取真实切片原 native Z bounds 与 source Z 范围的并。直桥使用 `exact_xy_support_l5.py` 对最终 binary64 四个顶点作精确有理支撑校验，绕过归一化和顶点相加的精度假设。设段向量为 v、逆时针边向量为 e、边起点为 p，c 为两中心端点 cross(e,endpoint−p) 的最小值；完整宽 2R 矩形处于该边内侧的充要条件是 c≥0 且 c²·(v·v)≥R²·(e·v)²。四边均成立、面积为正、严格凸才接受。若首次舍入造成缩边，只扩大 XY 法向宽和沿线端部，再按实际舍入顶点复算；32 次 cap 仍失败则 unresolved。每次精确角点舍入误差、normal scale surplus、支撑余量都记录。Z 不参与此补偿，extrusion height 只作有向算术取整。native 还检查 8 顶点 / 12 边 / 6 平面、实际 XY 顶点等于获证四点、每条竖边覆盖完整 Z，及三组成体各自减 carrier 的数值差。此平面连续几何证书与 native Boolean 检查分开。圆柱 BREP、AddOptimal bounds 与 Common 仍是 native 数值操作，不是区间内核；`formal_interval_CAD_certificate=false` 保留。finite whole-material containment 检查负责发现实现错误，不升级成连续证明。

**不能用统一大 Z padding。** 两法兰分别贴着原 neck 的上下水平边界，任意向 neck 扩厚可能制造新的真实 carrier 交叠。另一方面也不能为消除交叠把材料或 carrier 厚度缩小。源面的实际 BREP、向外数值界和原 signed/valid/Common guard 必须同时保留；边界无法证实则 unresolved。

每层 carrier 只对当前完整 B_SHELL 运行原 `strict_common`；所有层的 Common 通过原 `translation_regions.sum_common_upper_bound` 求和。完整 actual−rebuild 的非负遗漏体积只计一次，capsule 原生并体的三组成体减最终 carrier 的损失也加到同一总和，最终只对整个实体对应用一次 1e-7。这个遗漏预算约束每个瞬时姿态的交体积，并不等于连续扫掠差集的并体积。只有完整 source 差集与所有 capsule 组成体差集均实际为空，才把 native 零差包含控制标为通过；任何非空遗漏即使最终体积上界≤1e-7，也记 `unresolved_source_containment`，不升为 clear。所有差集 BREP（包括空集）都保存。旧 `identical_relative_pose` postguard 只检查已经固定的 carrier 与障碍这一次静态 Common；新动态扫掠有独立 L5 schema，不用旧方法名冒充动态证据。

负对照将真实完整 moving input 有意作为位于自身扫掠内的障碍，须得到整体 Common >1e-7；它是实际材料的几何检查负对照，不是声称在真实 B_SHELL 中发现碰撞。另需普通/反向/零/极小 capsule 的有向体积和有效性控制，全部保留既有七项 L2 native 控制。原 L1 的生成 EXTRUSION 分支另外直接回放并单列 executed / failure / unresolved；新 capsule 绕过旧分支不能称旧分支已修复。

## 当前壳体不得替换成旧 STUDY

历史 `telescope_shell_envelopes.py` 的同类 carrier 对旧 STUDY 壳曾有数值记录，可作为算法结构参考。当前 `product_templates` 还加入 side rims、return guide plates、support bosses，EP5 又切除固定 channels。历史 pass 和其 body ID 都不能当作当前 pass。

当前阶段调用真实 K1 adapter、原完整 factory、原五 factory-law probes，并对当前 q0 B_SHELL / telescope 与原七例完整输入做双向材料核验。随后仍直接使用当前整个 B_SHELL 做 Common，所有 additions/removals 都在。若 carrier 为正，保存 Common、该 layer 及全部参数范围；优先从 Common 的位置投影出候选 q / 合法 joint 分配，再在真实完整 factory 构造并检查 actual whole body Common，验证原 BREP 与 STEP 后才能称真实碰撞。采样未碰撞仍是 unresolved，不能消除 carrier overlap。

## 先行容量依据

拟分两个明确范围：原七例的 exact input replay；当前 K1 的七个完整 q 域调用。每组只需 12 个 primary 分层 carrier Common，即两个范围共 24 个；另每组有 12 个负对照 Common、24 个 primary/负对照 native 再读 Common、36 个 capsule 组成体 Cut，以及逐层/完整源双向差、STEP对照和有限实现检查。这些成本不隐藏在 primary 计数内。V4a 的原262调用全保住后已实际核：七对各36调用，共252调用耗时999.066948 s；十个其他对各一次耗时34.573721 s，全部调用合1033.640670 s，controller1166.881252 s。L5 的操作结构减少是试算依据，不能据此预先承诺 native 秒数。每个案例仍有完整原 BREP/STEP 读回、source 重建、逐层和 union 双向差、负对照、写入 / 读回。操作计数减少是可审的算法依据；不能据此承诺具体秒数。

原七例阶段先测实际时间 / peak RSS / carrier 数 / Common 数 / 科学文件字节，再测当前 K1（其中包括 loader 和原五 probes）。每个新研究 worker 继续原 1,800 s / 1,536 MiB、6.8 GiB shared guard、200 MiB 启动和 100 MiB 运行盘保留、1,536 MiB 启动额外内存。hosted lifecycle 与 source closure 不减。若任意阶段超限，完整未测清单保留；不能改门槛继续绿。

独立读回将包括原 BREP/STEP 双向校验，所有新科学 BREP 的新导入、signed/valid 检查与 carrier/whole-shell Common 复核；另一个无 CAD 的记录 reader 重建完整层表、范围、总和、每文件 SHA 和未测项。必须分别说明同一内核的再次几何读取和独立记录核对，不能叫第二 CAD 内核。真实每层导出数量与两侧全对 / 全域标志应固定在 manifest，避免 V4 的导出漏项重现。

如果 L5 全 q clear，才将它作为新、明示的 family route 评估接入完整 11,781 对，并依据实际容量决定能否回到单 worker 1,800 s 或仍需分片。若 L5 仍有 overlap，先做真实中途 whole-body Common 定位，不靠九片名义全量将其自动消除。当前纯源码 / 算术阶段不能批准 G2、G3、制造或实物放行。

## 本次运行与导出边界

拟单工作流两个顺序 job：original 先执行原七例，current 依赖前一研究执行完整后使用真实 K1 loader 与原五 probes。每 job 内 producer 与独立 native reader 各有原 1800 s / 1536 MiB 限；整个 hosted job 仍 40 min、独立命令 deadline 2220 s，任一耗尽按真实 capacity stop 保留。没有开启全11781。

V4a 已保住完整262 call JSON / 1632 BREP；其932252 B顶层原报告被runtime-locator过滤拒收，原SHA与拒收事实保留。新L5的原报告在hosted上先由native和纯记录读者完整核验。public导出只在固定metadata字段 `construction.current_candidate_factory_metadata.research_relief.KEY_source.original_complete_KEY_source.archive` 验明原manifest指定archive的内容SHA、绝对位置后，将该container locator投影为repo相对路径。其余科学值保持，原完整报告SHA/bytes和该投影记录同时保存；任何其它未review名称或locator仍拒/exit2，其余合法科学原件和MANIFEST继续保留。

普通/反向/零/极小新capsule控制、既有七项L2控制、原case016保存的EXTRUSION temporary whole solid+face，都须实际执行。旧 `translation_regions.regions` 仍应真实重现原unsupported EXTRUSION rejection；V2对这个真实保存shape再直接生成全部carriers，并检查有向valid、实际材料读回和有限包含。新路线不改写旧方法或旧失败。所有这些native结果目前都未执行，只有纯source/support和export IO测试已执行。
