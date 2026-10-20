# EP4 中央 FPC 与 KEY 输出槽：改形前保留约束

仅依当前源码作结构和标量预审，尚未收到本轮 PREDOCK native Common，下面的接触位置为待匹配推断，不是新 CAD 碰撞结果。未改共享源码或运行 native 主机。输入 SHA 见 `ep4-key-scalar-review.json`。

## 1. 中央 12 mm 带邻近的是闭合槽端帽

`cam_coupling.py::templates` 第 125–131 行给出右侧输出槽：中心线端点 C=(6.5,78.25)、D=(20,64.75)，外 capsule 半径 1.1 mm、内槽半径 0.425 mm、槽片 Z=1.2…1.6 mm。左侧经 `handed(..., 'L')` 镜像。

因此右侧外材料最左缘是 **X=5.4 mm**，内槽最左缘是 **X=6.075 mm**。EP4 自由带宽 12 mm，固定 +X 宽度轴，低段 X=−6…6、Z=1.4…1.5。若 Common 落在这一闭合端，它属于输出槽的端帽材料，不能当成无功能余料。

若把全厚端帽沿 X=6.0 直切，该端点截面剩余的平面封闭壁仅 **0.075 mm**；若为带边增加 0.2 mm 侧向净距而清到 **X=6.2**，则已越过内槽最左缘 **0.125 mm**，会破坏该处的闭槽边界。这不是“仅 0.08 mm³”就可忽略的判断；局部 Common 体积不描述保持功能。

KEY 的名义位移为 q=12×slide/79.75，只有 Y 方向平移，所以 C 的世界 Y 从 78.25 变为 90.25。EP4 S 段在世界 Y=80…90 抬升；OPEN 时 S 高度归零。因此预期 STOW/OPEN 的低段仍可能碰闭合端，PREDOCK 需用本轮实际 Common 判定，不能继承旧 EP3 的 KEY 交叠结果。

## 2. 不能随槽片独立移动或切除的连接

| 结构 | 当前源码尺寸/约束 |
|---|---|
| 输出直臂 | X=10.8…11.4、Y=39…72.6、Z=1.2…1.6，截面 0.6×0.4 mm；它不在中央 X=±6 的低段内 |
| 横桥、立柱、上搭接片 | 横桥在 Y=39…39.6；立柱 X=13.2…13.45、Z=1.2…4.35；上片 X=13.2…13.45、Y=15.8…39.6、Z=4.05…4.35，其截面只有 0.25×0.30 mm |
| 直臂导向 | `housing_study` 第 219–228 行：固定在 A_BACK_PANEL 的 Y=56、62 两处；内侧面 X=10.75/11.45，底/顶面 Z=1.15/1.65；原直臂四面均只有 0.05 mm 名义间隙。整臂平移 X/Z 必须一起检查导向座 |
| 输出销轴向捕获 | `templates` 第 144 行的 follower：下法兰 Z=1.0…1.2、上法兰 Z=1.6…1.8，夹住 Z=1.2…1.6 槽片；销颈半径 0.4。改变槽片高度要同步核对法兰、销颈和分件装入 |
| 原 KEY 母体 | `templates` 第 157–160 行要求新延伸与原 KEY 有正体积连接；`verify_cam_coupling.verify` 第 175–192 行检查原 KEY 材料全部保留、附加输出臂不挡 PAWL 完整回位 |

`verify_cam_coupling.inspect_contacts` 还检查两个槽 flank 的接触，以及再越程 0.01 mm 必须产生阻塞。必须保留这些接触和捕获意义。单个参与体仍为一个 solid 并不能代替它们。

## 3. 一条可以有限评估的闭槽重构候选

原槽理想间隙产生 dx 半宽 0.025281432 mm、dq 半宽 0.060636771 mm；考虑两种 flank，C 沿槽能前移的 X 上限为 0.707040898 mm。只缩短 C 而保留外半径 1.1，仍欠 0.092959102 mm 才能取得带边 0.2 mm 净距。

可待 Common 确认后研究：把 C 改为 **(7.15,77.60)**，近端外半径 **0.95**，经精确 1 mm 槽向距离渐入原 **1.1** 半径长壁，D、内槽半径 0.425、槽片高度及远端直臂连接保留。近端外缘为 X=6.20，名义径向壁 0.525，最坏理想 flank 的沿槽端部余量约 **0.080668 mm**。不要全局把外半径缩成 0.95，以免额外削弱直臂连接。

### 精确外轮廓构造

设槽向单位向量 `t=(1,-1)/√2`，法向 `N=(1,1)/√2`，`E=C'+1*t=(7.857106781186548,76.89289321881345)`。前 1 mm 外体取圆盘 `D(C',0.95)` 与 `D(E,1.1)` 的凸包；它等价于 `0≤u≤1` 上圆盘 `D(C'+u*t, 0.95+0.15u)` 的并集。再与原半径 1.1 的 `capsule(E,D)` 联合，得到完整闭合外体。

凸包可明确构造而不依赖离散采样：令 `a=(1.1−0.95)/1=0.15`，两条外公切线的单位法向为 `n±=−a*t ± sqrt(1−a²)*N`；切点为 `p±=C'+0.95*n±`、`e±=E+1.1*n±`。用四边形 `p+,p−,e−,e+`、C' 的 R0.95 圆盘与 E 的 R1.1 圆盘联合后挤出 Z=1.2…1.6。再并入 `capsule(E,D,1.1,1.2,1.6)`，扣掉唯一且连续闭合的 `capsule(C',D,0.425,1.1,1.7)`。两个固定半径 capsule 的直接联合虽然可能连续，但不是上述线性半径渐入的精确构造。

前 1 mm 的每个圆盘最左 X 为 `6.20+u*(1/√2−0.15)`，随 u 递增；远段最左 X≥E_x−1.1=6.757106781。因而新输出槽外体对中央带边 X=6 的名义距离下界为 0.20 mm。这个结论只涉及重构的输出槽外体，原 KEY 母体和其他参与体仍须由 native 验证。

### 四种理想 flank 极值推导

令间隙 `c=0.425−0.4=0.025`，传动比 `k=12/79.75`，交叉头偏移 `dx=±c*sqrt(1+k²)`，KEY 偏移 `dq=dx±c*sqrt(2)`；取两种 cam flank 与两种输出槽 flank 的全部组合。右侧销心相对原 C 的坐标为 `(.75+q+dx, −.75−q−dq)`，其中 `0≤q≤12`。

沿槽投影为 `s=√2*(.75+q)+(dx+dq)/√2`；法向投影为 `(dx−dq)/√2=±0.025`。最小 s 出现在 q=0 和 dx、dq 同为负极值，为 **0.999906827758999 mm**。C' 比原 C 前移 `.65*√2=0.919238815542512 mm`，所以最小剩余投影为 **0.080668012216487 mm**；D 端不变，其最坏端部余量仍为 0.999906827758999 mm。

内槽扣除销半径 0.4 后的允许销心域，是同一 C'→D 线段的 R0.025 capsule。上述四种 flank 在全 q 区间均落在其直线段边界，且端部投影为正。这支持“理想间隙下销颈仍在闭槽内且两 flank 可接触”的标量判定；它不包含制造误差、弹性、预载、实际原 KEY 外障碍或 PAWL 行为。

这是有界候选参数，**尚未实施，尚无 native 或制造通过**。新外轮廓在旧外轮廓内，但内槽也缩短，新端帽会填入旧槽的一部分空域；最终 KEY 不能预设为纯减材，必须保留 added/removed 双向材料账。还要检查整个闭槽材料、原 KEY 包含关系、实际 flank 接触/过行程、PAWL 回位、各级法兰与接头装入、全运动和新外部 Common；实际材料、疲劳、加工与公差也未因此成立。

## 4. 改形记录的边界

现有 `product_split_assembly.split_scene` 只作保持父体材料的分件，KEY 未被切改；现有 EP4 驱动也明确不重算 external-to-external 矩阵。如果在其输出后另改 KEY，必须新增独立的修改材料账和受影响的机构验证，不能继续借用“父体材料全部保持”的旧说明，或把 candidate-to-external 全检当成新 KEY 与所有机构之间已检查。

## 当前出处

- `/workspace/scratch/5547df349f5a/razr_phase4_reference/integration/cam_coupling.py`：`templates`、`state`、`housing_study`，SHA256 `4a3bf1d2b86d31fa8e3d60d3412e15548bf42287ed95d756798f3d88c6c4e631`。
- `/workspace/scratch/5547df349f5a/razr_phase4_reference/integration/product_assembly.py`：`native_scene`、`product_templates`、`product_scene`。
- `/workspace/scratch/5547df349f5a/razr_phase4_reference/integration/product_split_assembly.py`：`partition`、`split_scene`。
- `/workspace/scratch/5547df349f5a/razr_phase4_src/integration/product_routing_ep4.py`：`FIXED_ROUTE`、`route_sections`、`ep4_local_parts`；读取时 SHA256 `f8286416e8d4f835b5a280f3c76e7dd69aaebda25ac2217f40f33e19e92251b8`。
- [90b09f5 verify_cam_coupling.py](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/integration/verify_cam_coupling.py)：`prototype`、`inspect_contacts`、`verify`。
- [90b09f5 verify_endpoint_joint_pawl.py](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/integration/verify_endpoint_joint_pawl.py)：`scene`、组合槽极限和闭合/释放阻塞检查。

## 本轮 native 对照

待 root 提供 PREDOCK 实际 Common 与部件局部 bounds 后追加；本节尚无结果。
