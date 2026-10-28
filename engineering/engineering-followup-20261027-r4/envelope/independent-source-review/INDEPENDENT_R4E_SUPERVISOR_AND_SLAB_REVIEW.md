# R4E 监督器、完整边界 slab 证明与实际 V2/V3 记录的独立审阅

## 结论与范围

完整边界切片的数学论证在明确的紧集／完整边界包含前提下成立。凹体、内腔、多个连通分量、低维截面和非正交存储方向不会自行破坏该论证。此结论不是 native BREP 分类语义、编译内核误差或物理资格证明。

审阅发现了两个真实的参数绑定缺口，并由作者用新命名入口修复；旧源码和实际记录均保留。第一处是实际数学合同／输出目录没有与监督合同绑定。第二处是第一次修复仍允许 worker 的 argparse 参数缩写覆盖已检查值。新 canonical entry v3 对冻结的完整参数 schema 做唯一性和精确个数检查，并重建规范 argv。独立执行的四项针对性拒绝分别对应这两次修复；没有为入口修复重跑昂贵数学任务。

公差诊断还有一项模型表述歧义，已由新增 `R4E_DIAGNOSTIC_SCOPE_CORRECTION.md` 限定为共同的 L2 球模型。旧数值没有改变，也没有据此新增 L∞ 或 native 误差资格。

本审阅的实际数学结果范围为冻结的 V2 全部 16 份证书和 V3 当时的未完成快照。后续 V4 优化和其验证任务不在本报告的源码审计范围内，不由这里自动获得资格。

## 一、PID namespace、RSS 与退出竞态

原 `OwnedChildChannel` 不把 `Popen.pid` 直接当成当前 procfs 可见 PID。入口通过专用 ready/release 管道发送 nonce、源码摘要、命名空间 PID、procfs 可见 PID、PPID、NSpid 链、starttime 和 namespace inode。父端核对这些值属于自己启动的 Popen child；随后读 RSS 前后均重新核对相同身份。正常释放前已有一次真实内存采样。

如果 RSS 或 procfs 身份读取失败但原 Popen handle 仍显示 child 在运行，监督器产生监控失败并终止该 owned process group。如果原 Popen handle 已确认退出，才将该采样异常记为退出期间的观测；它没有填造一个 0 RSS。成功仍要求实际 exit 0、fresh entry receipt 的 completed、源及合同未变、owned descriptor 已关闭、无资源止停及无失败。

entry 的最终 `getrusage(RUSAGE_SELF).ru_maxrss * 1024` 检查提供整个该 Linux 进程的峰值 RSS。即使最后一次 procfs 采样撞上退出，也不能仅凭缺测跳过峰值门。异常终止而没有 entry receipt 会失败；被资源监督终止的进程也不会产生成功状态。

这是源码状态机审查和实际回执核对，不是对所有调度交错的形式验证。没有额外制造 RSS 故障或重跑历史控制；也不声称采样证明任意两个采样点之间共享 cgroup 内存、磁盘状态从未瞬态越界。

## 二、数值资源门与真实命令

以下纯数学值与原 V1 注册门相同：

| 项目 | 实际冻结值 |
|---|---:|
| wall | 600 s |
| worker RSS | 805,306,368 B，768 MiB |
| shared ceiling | 7,301,444,403 B |
| runtime disk floor | 104,857,600 B |
| maximum worker output | 41,943,040 B，40 MiB |
| metadata margin | 4,194,304 B |

启动磁盘准入仍要求 disk floor＋maximum output＋metadata margin；启动共享内存准入仍要求当前 shared＋RSS limit 不超过 shared ceiling。运行中观察 wall、disk、shared、实际 owned RSS／HWM 和注册输出目录字节数，退出后还有一次资源／输出观察。

监督器中的 `worker_started` 指 owned entry 已启动，不等于数学 payload 已运行。负控制中 entry 完成身份握手后拒绝参数，controller 正确记录非零退出且 completed=false；注册数学输出目录和 payload entry receipt 均不存在。

独立核对 V2/V3 controller 的完整实际 argv 后，supervision contract 路径及摘要、数学 contract 文件摘要、输出 resolved path、数学 worker 源摘要全部对应。因此新发现的旧入口缺口没有在这两条实际命令中触发。V2 实际输出为 1,733,330 B，entry 峰值 RSS 为 178,249,728 B。

## 三、两个参数漏洞及针对性修复

### F1：原入口未绑定实际合同和输出

监督器用 `worker_output_directory` 计量输出，而原 entry 原样透传 worker argv；`registered_math_contract_sha256` 没有实际核对。这允许错误的 CLI 指向另一个目录或另一份合同而仍观察原注册目录。

新 entry v2 先核对实际 `--contract` SHA 和 `--output` resolved path。两项真实负控制分别提供错误文件摘要、错误输出路径，均得到 supervisor exit 2、entry 非零、正确拒绝原因，无数学 payload 输出。两项都保留原资源数值。

### F2：第一次修复仍允许缩写覆盖

真实数学 worker 的 argparse 默认允许缩写。只检查完整 `--output` 不能防止后接 `--out other`，只检查完整 `--contract` 不能防止后接 `--contr other`。独立提取实际 worker 的 argparse 构造 AST 并只执行该 parser，真实确认两种后值覆盖；未运行数学 payload。

新 entry v3 要求参数总数等于冻结选项数的两倍；每个 option 必须是完整注册项、只出现一次且带明确 value；选项集合必须完整，然后重建 canonical argv 再做路径与摘要核对。原追加缩写反例与同 arity 重复选项各实际执行一次，均在 payload 前拒绝。两个版本的控制结果分开记录，未声称全部四项都在同一个版本上重跑。

## 四、紧截面论证为何涵盖凹体与内腔

令 S 是 R³ 中的紧集，P 是坐标平面 x_k=t。S∩P 是 P 内的紧集。它的相对边界包含于 S 的环境边界：若一个点是 S 的环境内部点，点周围的三维开球包含于 S，与 P 相交得到一个平面内开圆盘，故该点不可能是截面的相对边界。

非空紧截面的任一横向线性坐标极值必在相对边界。若极值点是平面内的内部点，沿该横向坐标再移动一点仍在截面内，与极值矛盾。截面相对内部为空时，所有点已属于相对边界。因此全截面的横向极值可由该平面上的完整环境边界支撑。

这一证明不使用凸性、连通性或朝向，也不将外表面和内腔面互相抵消。包围外壳、孔壁、多个分量的全部边界共同进入 carrier 集合。对任意紧集采用外盒可能更松，但不会因此漏掉材料。

## 五、slab、零体积载体与三轴交集

沿第 k 轴在所有边界盒端点和有限全局 pair domain 端点切分。开 slab 中任一截面遇到的边界盒必在 active 集合中。active 集合的横向包络因而外包整个材料截面；两个材料各自得到外包后取交仍为外包。若任一材料没有 active 边界盒，该材料在开 slab 中不可能有非空紧截面。

在 cut-plane 上的材料不能靠开 slab 来覆盖。必须把全部 cut-plane 连同有限 global transverse domain 作为闭合零体积载体保留。源码保留 cuts 和 global domain，并把这些载体明确标为集合表示的一部分。全局 domain 本身低维的早退分支还必须按其 `global_intersection_box_exact` 理解为保留的低维载体，不能把空 positive-cell 列表解释成“无接触”。这些有限平面的三维测度为零，所以可以只对正体积格盒求和；零体积不等于正间隙。

三个轴的构造各自包含同一实际交集，所以进一步相交仍保守。正体积三重交盒以唯一 X/Y/Z slab index 三元组标识，不同三元组在至少一个坐标的开区间上不重叠，因此内部两两不重叠，精确体积可相加。格盒的面和棱仍由零体积载体覆盖。

每个正格盒的外向三角面、相反边关联、Euler 恒等式和散度体积有明确检查。这证明精确盒载体的拓扑与有向体积，不证明其并集是一块原生 manifold solid，也不替代 OCCT Boolean。

## 六、全位移与完整曲面参数

对紧的位移集 D，S+D 紧，且 ∂(S+D)⊆∂S+D。边界点若表示为 s+d 且 s 是 S 的内点，平移后仍有一个三维开球落在 S+D 内，与边界性矛盾。因此把每个完整边界 carrier 盒与整个原始位移盒做区间相加足以外包 swept boundary。

源码读取全部原始 remaining displacement intervals，并在 V2 的 16 份实际证书中逐项与原 binding 对应。独立坐标盒可能扩大相关运动集合；扩大导致保守性变松，不构成用有限姿态代替全区间。

平面使用完整 UV 范围，并扩大到全部 pcurve 范围。圆和圆柱使用全周期 radial support，方向投影中的非正交分量照原 exact 值保留；平方根由整数平方不等式给出有向有理外界。圆柱轴向参数使用完整 V 区间。两极点、一次、非周期、非有理 BSpline 的被接受子类在实际 trim 两端计算完整 affine 延拓，未将 overshoot 截回 knot interval。所有 face、3D edge、vertex 都加入，不能用 seam 点或离散采样替代曲线。

这些是所定义 exact-real source model 的保守推导。原 native 闭壳旗标、valid guard 和重复提取不能证明容差接缝真正定义了同一个紧材料，也不能证明编译后二进制曲线求值／变换的统一误差界。因此 native boundary semantics、source-to-binary 对应、native continuous G2 和物理资格继续为 false。

## 七、公差模型的澄清

原 coarse 方法扩张方向支持 epsilon·||n||₂，适用于 L2 球扰动。slab 对每坐标扩张 epsilon，构成该球的立方体外包。两种体积上界取较小值可用于共同 L2 球模型。

若把结果解释为全部独立 XYZ±epsilon 的 L∞ 立方体扰动，则不成立；在 n=(1,1,0) 上，立方体支持为 2epsilon，大于球的 sqrt(2)epsilon。新增 scope correction 明确采用 L2 球并否认较大 L∞ 模型资格，旧源码、数字、失败均未改变。stored tolerance 是否真是 native 分类或物理变形误差半径仍未被证明。

## 八、实际结果与容量

V2 的全部 16 份 gzip 证书已读回身份、完整原材料／全位移 binding、每方向 face／edge／vertex 完整项集、支持聚合、原 exact float64 1e-7 判据、所选盒体三角边关联、Euler 及有向体积。结果保持 4 项 raw 条件通过、12 项失败、0 项诊断通过。

V3 收读快照仍 `execution_completed=false`，没有完成 16 帧。部分阶段中的一个 raw upper 数值不是完整已经封存的逐帧证书，不获得通过资格。原 V1 的粗界失败及补充数据失败、原 V2 的 12 项失败均未被重分类。

slab 每个 covering 注册最多 10,000,000 次 intersection 检查，并保留 600 s／768 MiB 等外部门。有限枚举上限不保证在资源门内完成；容量拒绝或进程超时属于真实未完成，不能通过丢弃盒、取少数采样或省略切面改写为 pass。

本审阅输出、四项小控制及现有证书读回均在 `independent-source-review`。原 runtime 独立审计和器件来源分支保持冻结。
