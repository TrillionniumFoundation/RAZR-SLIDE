# KEY 局部端帽研究脚本独立复核

复核对象：`/workspace/scratch/5547df349f5a/razr_key_local_study/key_endcap_local_study.py`。**最终冻结 SHA-256 为 `6c6b1fb9b5affd36a6d3d5848ff2dd20c0856409ad599019eabd64653eedaa90`（28912 字节）**。初次纯算版本 `63e296410beade074eea1b37ddf8b175d9164d2fa262ba3389db5e1c2273c76b` 的原记录保留；最终版重新求值所得近/远端余量与初次结果一致。这里没有执行 native CAD，也没有修改冻结 EP4 或整机源。

## 已核对的构造与运动关系

- `geometry_parameters()` 的两条外公切线使用 `n± = −0.15 t ± √(1−0.15²) N`，由 C′=(7.15,77.60)、R=.95 的圆经 1 mm 过渡到 E=C′+t、R=1.1 的圆，再连接原远端 D=(20,64.75)。两个切线与法向的内积残差均小于 1.04×10⁻¹⁴；两个圆处的半径符合参数。该构造保留连续材料与切向连续的边界，没有把完整 yoke 全局变窄。
- `clearance_cases()`、`pin_center()` 的四种 cam/output flank 组合与 `verify_cam_coupling.prototype()` 的 crosshead X、KEY Y 运动关系相符。镜像后使用左侧 X 符号、同一 KEY 相对 Y 位移，也相符。
- 名义 q∈[0,12]、两处实际槽隙组合下，销心沿槽近端最小余量为 **0.0806680122164867 mm**，远端为 **0.9999068277590055 mm**。半径 .05、距销心沿 N 方向 .55 的壁内 witness 的最小端余量为 **0.030668012216486698 mm**。这些是固定几何的解析边界，不包含加工误差、弹性、预载或摩擦。
- 旧槽、四个 arm/tab 盒体和母体的重建与 `cam_coupling.templates()` 一致。脚本准备执行旧工厂双向材料差、新件原 KEY/arm/tab 材料保留、远端接口双向差、近端新增/去除材料核算。缩短内槽会在原空腔中增加材料；不能把新件称为旧件的单纯减材。
- 从真实 CROSSHEAD 截取 z=1.0..1.8 的有限颈部及两法兰，再与独立圆柱构造双向比较，适合验证本局部捕获界面。q 两端的 ±.01 mm 轴向正控与统一 witness 方向一致。全 q 颈部扫掠和解析 witness 提供的范围，应与 q 两端实际轴向 Common 的有限核验分别陈述。

## 已发现并交回作者修正的问题

**导向块的单轴误拒绝。** 原先的 `new-slot-whole-q-Y-separation` 对 Y=62..64 的 guide 一定为 false：槽外轮廓最低 Y 为 63.65，包含 flank 偏移后的最低值为 63.58936322893345，小于 guide 的 64。这不能推出实体交叠，因为该低 Y 区域接近 X=20，而导向块 X=10.5..11.7。作者已改为恒 R1.1 槽外包络的完整 Y 平移包络并做 Common。其平行四边形加四条 capsule 的构造正确且保守；零 Common 可证明此范围的避让，正 Common 只表明该保守充分条件未获满足。解析交叉检查也显示：全程槽的 `signed_X+Y` 下界为 83.13372831032305，guide62 上界为 75.7。

**来源快照时机。** 已读更新版在导入前快照 integration Python，记录无法追溯至执行前的 late source，并使此类情况不能报 `source_bytes_unchanged=true`。挂载母体归档及 manifest 也有独立哈希。

**进程退出码。** 初版 `main()` 在 native report 完成但声明检查失败时仍返回 0。最终冻结版已改为返回 2，同时保留完整报告；源码已复核。这是执行语义修复，不是候选几何通过。

**完整实体检查。** 最终版新增左右完整 KEY（包含原母体与 arm/tab）的 signed-X 内缘 ≥6.2 检查，避免仅凭新槽外轮廓就声称中央 ±6 带有 .2 名义间距；并新增完整 KEY 与内槽 capsule 的 zero Common，防止原母体/臂在融合后封住内槽。两项均等待实际 native 结果。

## 与冻结 EP4 原生失败记录的对应

N=`9a8307fe4bd4163b53515698fb12cfc0a8cc27e7` 的 OPEN/STOW native 执行已回传以下真实结果；本复核没有在本地独立重算或回读这些实体：

| 状态 / 对象 | 观察 Common，mm³ | 本局部候选能否据此宣布解决 |
|---|---:|---|
| OPEN、STOW，有限 FPC / 每侧 KEY | 每侧 .08472548214283 | 仅在新完整 KEY 实际满足 signed-X 分离并完成对应核验后，才可给出该局部几何结论 |
| OPEN，B_inner_carrier_jaw / 每侧 KEY | 每侧 .04236274107142 | 同上；仍不能推及其余外部障碍 |
| STOW，FPC / OLED_GEOMETRIC_TRIAL | .7130456006201 | 此端帽改形不会修改 FPC/OLED，不能据此消除此项或称联合完成 |

原生原件为 `/home/qian-qi/.local/share/razr-slide-evidence/product-followup-20261020-phase4/open-stow-9a8307f/native/native-report.json`。计划归档路径为 `engineering/product-integration-20261018/phase4-20261020/native/open-stow/native-report.json.gz`，汇总为同批 `native-summary.json`；计划路径不替代原件。PREDOCK 原件另为该主机同目录下 `predock-9a8307f/native/native-report.json`，本复核尚未收到其最终结果，不预写其通过与否。以上基准均保持未改 KEY 的 EP4，不以局部候选覆盖原失败记录。

## 不能由此研究推出的结论

PAWL 验证仅针对 `cam.parent(side+'_PAWL')` 的历史 mounted 部件与完整 1.1 mm 上升包络。当前 endpoint/serviceable PAWL、操作 TAB、载荷、松手保持和复锁未覆盖。新槽全 q 外包络及原 arm/tab 的扫掠可覆盖这个有限历史范围，但不能升级为当前操作链验证。

本脚本没有把新 KEY 装入冻结 EP4 的完整外部障碍场；原本槽空腔中新增的闭帽材料需要独立整机检查。STEP 导出本身也不等于独立回读。局部壁厚 .525 mm 的强度、工艺公差、分体法兰装入与保持工艺均未验证。所有实物、整机、制造放行标记仍应为 false。

初次纯算数据见同目录 `key-local-independent-arithmetic-review.json`，最终脚本身份及复核见 `key-local-independent-final-review.json`。完整结构约束与逐函数出处见 `ep4-key-retained-material-review.md`。本批 EP4 原生 PREDOCK Common 尚未收到，本文未将假定交叠位置写成观测事实。
