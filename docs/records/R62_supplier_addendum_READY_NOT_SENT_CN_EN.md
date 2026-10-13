# R62 原厂动态跨舱 FPC / OEM 受控原件补充询证

**READY — NOT SENT；供应商回复 0；不包含采购订单或制造授权。** 本文是 R58/R59/R60/R61 原双语 RFQ 的附加说明，不代替它列出的 12 类受控原始材料。仅附上本轮进一步发现的结构几何矛盾及新验收方式。**不能将研究网格、理想接头或虚构密钥视作厂家数据。**

## 中文供应商技术补充

请使用同一已签发的接口基线（但保留各零件实际各自的修订版本），提供完整 A/B 原生 CAD、A/B PCBA/电池/BMS/导轨与 OLED 禁入体积、准确 7 英寸 OLED 全封装及 COF/FPC/封边、Hirose BM28 header/mate 实体与焊盘、FPC 材料叠层/铜线中性面/双轴允许动态半径与扭转、30 万次目标工况下的完整在线导体测量（样本、失效定义由双方技术协议确定）、两端机械常闭、双电池主电源隔离故障和 USB 高速 SI/EMI 原始实测数据。请对每项提供供应商身份、版本/料号、文号、签发签名、字节级 SHA256、许可用途及**可修改区域和禁布边界**。

本轮新发现：过去三个独立网格路径的**起止点并不是同一对刚性连接器锚点**。固定 A 舱首端在三个状态的最大漂移 **0.200 mm**；以 `B_local = B_world − [0, s, q−8.2]` 逆变换以后，B 舱末端相对收纳基准最大漂移 **0.650 mm**。数值来自 R59 受控研究网格的离散“自由体素中心”，**不代表 OEM 连接器真实误差**。请厂家直接提供本项目真实 A、B 接点的三维配准坐标、安装正交基底和世界变换、至少 4 个同名非共面基准点及其原厂公差，以便正确进行实体连贯检查，而不是试图校正体素路径的幻觉端点。

R61 R0.4mm **仅研究用** C1 圆角测试，独立几何路由的长短差 **64.484956mm**，其测试家族的必要长度差下限 **61.780972mm**；不证明任意 3D 连续服务环不可实现。供应商需要给出**同一根 FPC 固定材料坐标**在收纳、全程滑行、换向、终点法向坐实、回程及长时收纳的连续位形、每点曲率与扭转、应力释放/储线机构，以及对整舱/OLED/PCBA 的原厂禁布体积的碰撞检验报告。

保留产品约束：双功能舱成品同外形、单块约7英寸柔性主屏（无独立背屏）、B舱向上滑79.75mm及法向坐实8.2mm、A舱优先较大电芯；4700mAh仍仅是目标。整段 USB 铜线**必须物理连续且保持在线**，不接受端点短暂接通、无线桥接或缓冲替代。

## English vendor addendum

**READY — NOT SENT.** Please respond to the existing 12-class controlled native-data RFQ with one coherent *assembly interface baseline*, preserving the distinct released revisions for individual A/B chassis, connector and display parts. Include signed issuer/part/document/revision identifiers, original bytes and SHA256, explicit licensed change and keep-out scopes, and four or more common named non-coplanar 3D registration fiducials with manufacturer-issued GD&T limits. Supply readable neutral STEP in addition to native proprietary CAD where necessary.

New R62 audit: previously selected independent R59 grid routes move their nominal A-side **voxel-center** start point by **0.200 mm**; the B endpoint after inverse rigid-pose mapping moves by **0.650 mm**. These are not physical connector anchors and should never be promoted to one installed cable. Provide real fixed attachment surfaces/positions and a material-coordinate-preserving dynamic FPC service loop, accounting for all forward/reverse Y=79.75 mm and Z=8.20 mm motion, bending/torsion/strain relief, protected storage volume and the actual OLED/flex/PCB/battery keep-outs.

Provide released FPC stackup, neutral axis, usable dynamic bend radius, fatigue test protocol and raw continuity/SI/EMI data, in addition to independent two-battery isolation and mechanical fail-closed evidence. Product is **NO-GO** until each independent real hardware gate has been approved. Signed SHA256 artifacts authenticate provenance only; they do not substitute for physical qualification. Supplier responses received: **zero**.
