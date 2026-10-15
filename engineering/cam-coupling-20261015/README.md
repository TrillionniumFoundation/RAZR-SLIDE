# 当前研究入口｜实体槽传动与伸缩随动销候选，完整解锁复锁仍未闭合

当前候选源码 `integration/cam_coupling.py`，独立原生重读 `integration/verify_cam_coupling.py`。
基于已合并固定接口 `f9091d28eda1ddbeed73d931e283a16aef7ac8d0`；证据在 `engineering/cam-coupling-20261015/`。
原 `mounted_mechanism.py`、直连失败、原始器件和全部真实输入空字段保持不变。

## 新增的真实研究实体

B 舱内长斜槽驱动 A 内横向随动件，第二条斜槽把横移转为原 KEY 的纵向移动；名义比为 12/79.75。
三个带底面和保持肩的嵌套套筒提供8.4mm相对总容量，补偿8.2mm法向就位。等量伸缩只是一条名义分配，
不是机械强制关系；非等量分配须满足各节止挡和总高度约束。上下随动头被槽板轴向捕获。

原 KEY 完整保留并与新连杆连成一个实体，没有缩放或切掉接触核心。输出连杆沿原 KEY 许可通道延伸，
在原根座之后转入新纵向导向。横向导向连接 A 框架，纵向导向连接可拆背板，B 槽板连接 B 自研壳体。
原框架/底板相撞和连接臂相撞的试稿保留，采用固定尺寸的通道与布置修正，没有随姿态自动切削。
新 A/B 壳体外包络不增大；壳体材料移除和新增均单独核算，不称为免费空间或 OEM 授权切削。

## 通过范围必须分开

槽销半径0.4mm，槽半径0.425mm。两级槽单独计算的输出允许带宽约0.12127354mm；
这是无预紧条件下的槽几何量，不是实测整机回差，也不是包含导向间隙、套筒偏心、挠曲和热变化的完整公差上限。
中心线回程可逆不等于负载反向后必然回到同一位置，末端接触/预紧/止挡和复锁仍未解决。

完整总成的名义检查以 PAWL 已被外部机构停在退让位置、STOP 具有原模型要求的回位力为边界条件。
本轮没有用这些边界条件冒充释放驱动机构。有限姿态与实体槽壁约束不能替代全程三维连续碰撞证明、
装配工艺、摩擦/卡滞/强度、伸缩件和捕获销的实际装配、或失效安全资格。
全部实际执行数量与CI身份以同目录 SUMMARY.json/HOSTED_CI.json 为准，不由套件数量推断。

下一步先做有实体约束的 PAWL 释放/保持/到位/复锁及反向过程，处理槽隙和端位回差，
再覆盖完整运动与装配、载荷、公差；同时放入真实主板、OLED/B平面储屏、端接/FPC、双电池与膨胀包络。
等外包络双舱、单约7英寸主屏、无独立外屏、A大电池和4700mAh整机目标不变。
`candidate_go=false`、`fixture_fabrication_go=false`、`manufacturing_go=false`。

## Evidence scope

`NATIVE_MANIFEST.json` and `geometry-manifest.json` bind the 19 original native
exports in `native-geometry.tar.gz`. The independent verifier recreates the
conditional 65-solid scene from these parts and the unchanged mounted originals.
`coupling-tests.json` is the 20-test local increment, not a complete 480-test run.
`rejected-development.tar.gz` and the raw logs retain initial topology, guide,
B-floor and old-root interference witnesses. Generated files do not edit their
historical parent sources.

The slot-only allowance omits guide play, telescope radial play, material
compliance, force, friction and thermal effects. No measured release force,
fatigue rating, real fixture, phone electronics or selected OLED/FPC/battery
is inferred from this nominal model. No powered/hardware/procurement action.

## PAWL 回位干涉修复

早期输出臂在PAWL已退让时不碰撞，但回到中途和啮合位置分别相交约0.48和0.726mm³/侧。
该原生负结果保留在 `REJECTED_RETURN_ARM.json`，旧源码与V4模型未覆盖。
新固定连杆横向区间由R侧14.2–14.8mm移至13.2–13.45mm（L侧镜像），避开原PAWL全行程X包络；
原KEY核心和PAWL都未切削。新增回归覆盖PAWL整个1.1mm返回包络，而不只是退让终点。
这段0.25×0.30mm截面的长臂没有刚度/强度和制造公差依据，不能据此放行实物。
当前21项新增局部测试通过；全量481项与V5原生报告以实际完成结果为准。
