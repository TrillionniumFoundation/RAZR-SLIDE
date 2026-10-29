# R7 edge189：一个原失败子叶、一个完整 Line、一个固定通道

## 1. 问题、证据与本次范围

本诊断针对已实际保存的一次切分成本探针，不挑选新的叶，不重新排序源，不增加第二次切分。
原 V6 case-028 / frame 1 的 retained leaf locator 为 `[78,375]`，原路径深度为24。
先前已执行的一次原规则切分产生低子叶和高子叶，累计深度均为25。
这超过原 V6 累计深度24；它只是另行命名的成本诊断，不能宣告原 V6 深度门通过。
该探针两个子叶都未排除，排除体积为0；原体积被完整保留。

低子叶固定 `material_side=0, axis=1, end=0` 通道（原顺序中的第3条）的首个未解决对象是
piece332，映射到 case-028 / material3 的原 edge189。
该 piece 是一个完整 Line 的原 AABB，原 additional_slabs 为空。
本次更强的保守关系是给这个 AABB 增加一个来源明确的斜向闭 slab，以保留该 Line 的坐标相关性。
它不是增加空间深度，也不是为了得到某个贡献代码而改变证明优先级。

本次只允许三个单 piece 比较：原 AABB、原 AABB 加 exact Line slab、原 AABB 加 τ-expanded slab。
只有严格源域/AABB等式成立且第三个比较实际提供分离时，才允许对**同一个固定通道**顺序测试完整 material3。
完整通道最多执行一次，按523个原 piece 的顺序前进，到首个失败停止。
不搜索其余11个通道，不更换法向，不替换目标，不运行全帧，不运行新的UV阶段。
两侧完整523/179个载体的顺序、数量、whole box和原约束保持不变。
唯一拟加的约束是 piece332 的一个 closed nonaxis slab，原 AABB 保留。

## 2. 原始源身份

原 R3E native producer 与独立 reader 的完整报告按字节数及SHA256绑定。
两者实际执行完成，各含53个原材料记录。
本诊断重新读取完整 case-028 / material3 记录，要求 producer/reader 整记录相等，
原 boundary inventory 无缺项，且 counts 恰为1 solid、1 shell、80 faces、228 edges、152 vertices。
完整原 material BREP 也按原 report 中的70886字节和SHA256绑定。
这仅建立本次旧源的一致性，不补造它与当前完整S4 factory的任何尚未闭合对应关系。

edge189 的完整记录、所有字段、原方向和参数记录均保留。
原 placement 必须为 identity，原 local_curve 与 native_global_curve 必须一致，原类型必须为 Line。
原 reversed orientation 是拓扑方向元数据；本诊断不会因此改变完整参数集合。
原非零 z 方向分数不得取零；周期字段的原 sentinel 不被解释成有效参数域。
源元数据的完整原件和固定旧 AABB 已保存在 `SOURCE_METADATA_READBACK_V1.json`。
该文件本身只读回元数据，没有执行本次新支撑计算。

本次原参数域是完整闭区间 I=[a,b]，来自两个原参数的 `exact` 字段。
原三维 Line 是 L(t)=O+tV。所有十进制 float/hex/exact 记录原样保留；计算只用原二进制浮点数
所对应的 Fraction，不使用十进制近似替代，也不重新归一化 V。
完整原位移盒始终为

```text
D = [0,0] × [0,1/2251799813685248] × [0,0].
```

它同时与原 V6 frame 和实际成本探针逐项绑定。
不得用零位移、端点位移或较小盒替代这个 D。

## 3. 精确源集合与固定法向

本次数学对象是序列化源的集合

\[
C=\{O+tV+d : t\in I,\ d\in D\}.
\]

预注册的唯一法向为 n=(1,2,0)，不搜索法向、不做单位化。
原字段给出 Vx=-2Vy 的确切分数关系；运行中仍须再次验证 n·V=0。
Vz 非零的事实须由完整原源和三维 forward bbox 检查独立保留。
nz=0 只说明这个投影不依赖 z，不说明源曲线的 Vz 为零。

生产端用原 interval add/scale/project 公式构造完整三维包围盒

\[
G_k = O_k + V_k I + D_k,\qquad k=0,1,2.
\]

I 和 D 的每一维完整闭区间都参与计算。
本次严格资格条件为 G 与原 piece332 的 B **六个端点全部相等**。
不以仅包含替代等式，不删掉极小 z 变化，不借 tolerance 调平不等。
若等式不成立，保留实际差异，本次完整材料通道不执行。
公式读回仍可得到有效的局部源诊断；它不自动成为旧载体的合格细化。

设 β=n·O。完整 exact Line+D 的支撑区间为

\[
J_0=\beta+(n\cdot V)I+\sum_{k=0}^{2}n_kD_k.
\]

当且仅当注册的正交条件实际成立时，中间参数项为零。
生产实现仍用完整参数项的通式计算，保留计算得到的 n·V。
这是新保守约束的代数依据，而不是从已知通道结果反推出来的法向。
对所有 x∈C，有 n·x∈J0。若 G=B，则 C⊆B且 C⊆{x:n·x∈J0}。
加入闭 slab 不删除原 B，也不删除任何边、顶点、端点或闭边界。

## 4. tolerance 的两个层次

原 edge tolerance 是旧 BREP 抽取器报告的 API 返回值，显示为1e−7，精确二进制分数为

```text
944473296573929 / 9444732965739290427392.
```

独立审查已定位对应OCCT V7_8_1的 `BRep_Tool::Tolerance(edge)`：它返回
`max(raw edge tolerance, Precision::Confusion())`，对应 `Precision::Confusion()` 为1.e−7。
因此本记录可能是 API floor，不能直接称为底层raw edge tolerance。
该官方源码语义、旧报告版本及抽取器调用链的完整原件由独立审查归档，最终合同按hash绑定。
本次不把该返回值直接认作 native 求值误差、制造误差或完整误差球的认证，
也不把版本、API定义或原native reader一致性补成逐次浮点求值的有向误差证书。
原科学 `TOL` 与这个 edge 字段的数值相同也不使两者的语义相同。
原科学阈值、tiny阈值、严判据和原任务失败状态均不改变。

为了给本次 slab 做明确的保守加宽，另行定义一个**假设**的坐标误差盒

\[
E_\tau=[-\tau,\tau]^3,\qquad T_\tau=C+E_\tau.
\]

若 e∈Eτ，则

\[
|n\cdot e|\le\sum_k |n_k|\,|e_k|\le\tau\|n\|_1.
\]

任何满足欧氏长度不超过τ的误差也满足这个坐标假设，但本次没有证明 native 误差满足它。
因此

\[
J_\tau=[J_{0,lo}-\tau\|n\|_1,\ J_{0,hi}+\tau\|n\|_1]
\]

覆盖假设 tube 在该法向的全部投影。
τ是精确原分数，法向整数，L1加宽不需要开平方或浮点近似。

必须区分以下两句：

1. slab `{x:n·x∈Jτ}` 本身包含假设 tube 的投影约束，因而包含整个假设 tube。
2. 新载体 `B∩{x:n·x∈Jτ}` 继续包含原 exact C；**它未必包含整个假设 tube**，因为 B 未扩张。

独立 checker 另算 `G+[-τ,τ]^3`，逐项报告其是否被原 B 包含。
这个布尔即使为false也不更改 B，不增加第四探针，不把负值隐藏。
最终报告始终 `native_BREP_error_bound_certified=false`。
新的载体不得被称作native误差shell、整个τ tube或实物公差包络。

## 5. 独立读回的方法与拒绝机制

独立 Line checker 由另一位作者实现，只使用标准库，不导入生产诊断或任何 producer/helper。
它收到从原独立 native reader 重新取得的完整 edge，以及原 carrier 和原 D。
生产端保存 claim JSON 后真正读回该文件，独立 checker 对读回 payload 进行验证。
完整原源、carrier、D和固定 n 都先与独立输入比较，不能只核对生产端自行重算的摘要。

独立算法枚举完整 I 的2个端点与 D 的8个角点，共16条记录。
即使 D 某轴零宽，也保留该二进制角点索引，不把角点去重后误称16个检查已执行。
每个点的3个坐标和 n·x 均用独立 Fraction 算式计算。
因为坐标与投影都是参数盒上的仿射函数，各坐标及投影的最小/最大值必在角点取得。
独立结果给出完整三维 G 和 J0，并与生产区间法逐项读回。

对于假设 tube，再枚举独立误差盒的8角点，得到2×8×8=128条记录。
独立三维 tube bbox 及 dot extrema 与生产端声明的 bbox/Jτ逐项比较。
漏τ的拒绝必须使用这些假设 tube 角点，不能用未加误差的 C 角点冒充。

固定5个实际负控在同一有限运行内执行，均保留实际变异payload、摘要、异常阶段和计数：

| 变异 | 要求的独立拒绝机制 |
| --- | --- |
| 将完整 t.first 改为0，local/global与self摘要及forward公式随之重算 | 原独立 reader 的完整 edge 等式；不能声称 scalar slab 察觉了缩域 |
| 将非零Vz改为0，local/global与self摘要及forward公式随之重算 | 原独立 reader 的完整 edge 等式；不能声称 nz=0 的投影察觉了此变异 |
| 将固定 n 改为(1,1,0) | 预注册固定法向检查 |
| 原 full_D 字段不变，仅 scalar支撑界遗漏 D 的上端贡献 | 独立16个完整端点/D角点的支撑值 |
| 原τ与L1 expansion字段不变，仅把加宽 slab 换成 exact slab | 独立128个假设tube角点的支撑值 |

缩域和Vz负控的self摘要更新，不允许仅凭“payload摘要没更新”就算独立拒绝成功。
异常类型或预算超限不能冒充指定拒绝阶段。
若完整通道确实成功，才额外执行一次删掉最后一个 source code 的原独立完整性负控；
没有完整通道证书时该控制标为未执行/不适用，不记为pass。

## 6. 原空间规则、完整域和独立通道回放

生产端的 `separated`、原 `channel_for`、Fraction区间基本函数按原函数完整复制并核对AST。
原判据仍是闭载体与开放通道之间的非严格边界比较 `<=` 或 `>=`，不加epsilon。
这些比较排除开放内部；所有闭 cell 边界、原根边界和先前cut plane仍保留为零体积载体。
不据此声称整个闭 cell 与材料不交，也不把未解决判据认作实际材料干涉。

独立通道核验导入的是已冻结的原 V6 独立 reader，而非任何生产函数。
它从绑定原 boundary 另建runtime。
新 slab 使用独立角点 checker 自己返回的 Jτ，不直接信任生产端 slab 对象。
三个单piece结果各自用原 independent `separator_holds` 核对；原 AABB失败必须复现。

只有 `G==B` 且 `B+τ slab` 实际分离，才可顺序处理该固定材料的全部523个原piece。
全部702个原carrier不删减不重排，其中其余701个完全不动，只有piece332增加一个约束。
另侧179个保留但不另开通道。
若通道全通过，原 `check_exclusion` 核对所有523个codes、channel footprint、whole外延、闭边界语义。
若遇到后续blocker，独立检查每个已有prefix code，并检查该blocker所有原注册轴向/非轴向判据均失败。
这样保存的是“一个固定通道的实际prefix/下一阻挡”，不是完整12通道结论。
后续Cylinder等新的失败也直接保留，不在本运行继续发明第二种约束。

## 7. 容量、累计账与执行边界

本诊断独立注册60秒、512MiB address-space/peak-RSS检查、64MiB单输入解码上限、4MiB输出上限。
它不运行native内核，也不计算Taylor角片，不创建新split，不运行新全帧。
原domain诊断顺序重读两份约65MB native报告实际为1.344秒、241.6MB peak RSS；
原单split探针739piece低子加其他固定工作总计0.793秒、174.0MB peak RSS。
本次两个完整native报告仍顺序读取，只保留选中材料后释放其余对象。
这提供有限运行的时间/容量依据，不承诺成功或把运行异常改判成通过。

固定几何预算上界：

| 项目 | 上界 | 原因 |
| --- | ---: | --- |
| 新split | 0 | 只读回已经保存的cut与低子 |
| 固定完整材料通道 | 1 | 资格条件为假时0 |
| producer piece测试 | 526 | 3个单piece + 至多523个原material piece |
| producer support判据 | 4208 | 每piece最多6轴向+2非轴向 |
| 原 independent separator调用 | 553 | 单piece最多6+8+8；完整prefix至多523+8 |
| 独立claim调用 | 6 | 原claim1 + 固定负控5 |
| 端点/tube采样记录 | 864 | 每调用最多16+128 |
| 新源验证工作的保守计费 | 50000 | 含比较、算术上界及另标来源字节的额外保守计费 |

负控提前拒绝会使实际执行较少，但不扩大注册域或预算。
源码验证包含预先明示的保守固定charge；它们是上界计费，不冒称每一短路分支实际求值数。
独立V2每完整调用的算术计费为3488，比较上界2500，合计5988，小于所注册6144。
六次调用的6144上界共36864。其 `source_binding_checks` 和 `source_serialization_bytes` 原标签独立保存，
本runner又把它们加入保守总扣账；序列化字节不是实际比较次数，报告明确标记这层额外overcharge。
原edge canonical JSON是1553字节，六次最多9318字节；原源binding调用按每次64个计有384个余量。
加生产端三次完整公式固定计费384、保存路径/低子读回448以及独立separator wrapper guard最多553，
静态合计上界47951，仍小于50000。没有为了接收新checker提高预算。
所有实际角点、分项原始计数、保守扣账以及失败前计数均保留。

已有累计账从原 V9 81split/171429piece/342440support开始，加入correlation、wire和已执行one-split成本探针，
本次起点固定为82split、174854 piece-like、366314 support-like。
本次piece测试、独立separator调用、实际vertex记录和validation比较继续扣入同一12M/12M预算。
既有诊断中不能直接归入separator计数的source construction成本，其时间、RSS和未计数属性仍在旧ledger中保留，
不称其为零成本或可直接复用的证明。
旧V6原全局4096split已另行实际用尽；新账不把跨阶段深度或split偷偷重置成旧V6资格。

资源门使用原定义：

```text
shared_unreclaimable = anon + shmem + max(kernel - slab_reclaimable, 0) + unevictable
startup shared_unreclaimable + registered RSS_limit <= 7301444403
startup disk_available >= 104857600 + maximum_output_bytes + 4194304
```

`memory.current`只另行观察；它包含可回收file cache，不替代shared门。
原resources函数完整复制并核对AST，不添加memory.current gate。
全输入/source/合同辅助文件在运行前后做完整hash读回，实际失败及退出、时间、RSS、stdout/stderr另行封存。

## 8. 不改变的结论

原V9 producer完成、独立worker完成、owned checker发生VmRSS退出采样失败的区别保留。
原first-u gate未被driver执行；保存的u0不能改成贡献条件通过。
本次没有UV代码，也不改变原V7/V9 first-u方法资格。
原完整16条件中的未执行/未通过项仍存在。
此前domain第一次真实绑定失败、correlation无改善、wire真实接触与未决、one-split两个pending均保留。

即使本次一个固定通道成功，也只是更强序列化源模型对一个已保存深度25子叶开放内部的有限结果。
它不证明全帧上界达到原阈值，不证明native语义、当前factory材料对应、完整连续G2、结构强度、电气或实物G3–G5。
实际报告可以否证这条改进路线，也可以精确指出下一阻挡；本轮不得自动展开新阶段。
