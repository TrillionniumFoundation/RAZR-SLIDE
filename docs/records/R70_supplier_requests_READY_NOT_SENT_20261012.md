# R70 供应商询证文本｜READY / NOT SENT

**重要**：没有发出邮件、采购请求或 NDA。未收集任何受保护第三方设计，没有请求绕过知识产权许可。联系人必须通过独立官方渠道核实。

## 英文：发给 Hirose 官方连接器团队（拟稿）

Subject: Engineering data request – BM28B0.6-24DP/2-0.35V(53) and BM28B0.6-24DS/2-0.35V(53), static internal termination

Hello Hirose engineering team,

We are evaluating the above BM28 header/receptacle pair as a **static, low-cycle internal board-to-board termination** for an experimental two-chamber mobile design; not as a 300,000-cycle sliding contact. Before mechanical integration, please identify the current revision of the original manufacturer STEP/2D drawings, exact mated/PCB keep-out volumes, land patterns, tolerances, retention and mounting requirements, derating of signal/power contacts, and permitted use of the CAD in a derivative mechanical prototype.

Please confirm the applicable mating-cycle limit and whether the 20Gbps connector specification presumes a particular reference stackup/channel. We will not interpret the connector's published transmission-rate specification as a certified complete USB path or battery-main-supply qualification. Please identify the licensing/contact process for receiving verified files, samples and latest approved mechanical revisions. We can exchange controlled CAD only after an appropriate confidentiality and licensing arrangement is in place.

Thank you.

Official product pages: https://www.hirose.com/en/product/p/CL0673-5024-0-53 and https://www.hirose.com/en/product/p/CL0673-5025-0-53

## 中文：发给 A/B 结构 CAD / OLED / FPC 厂商（拟稿）

主题：约7英寸单屏双功能舱滑盖方案——同修订结构、电气与动态 FPC/OLED 原始资料及可验证样件咨询

您好：

我们研究的是两块同外形尺寸的独立功能舱，B 舱由后下层向上滑动约79.75mm，终点法向坐实约8.2mm；仅一块约7英寸柔性 AMOLED 主屏，不设背部外屏，A 舱优先放大电池。拟申请**经过许可的目标型号/准确版本**的研发/样件资料，不请求不受许可的第三方逆向 CAD。

请在正式 NDA 和使用授权范围内提供：

1. A、B 成品可修改 CAD、GD&T、主板/相机/双电芯/BMS/天线、热源及禁布保护体积；同一装配接口修订和4个非共面配准点。
2. 目标 OLED 模组含 COF/FPC/封边的完整外形、叠层中性面、动态曲率限制、长时间收纳残余形变、展平力随温度及循环变化曲线、完整寿命判据。
3. 动态 FPC 全叠层/铜层构造、容许弯/扭半径、两端实际夹持与出线方向、实际宽厚和最小服务环空间，**同一根样件**双轴循环至少30万次（如产品寿命协议另定请注明）两条连续电阻/时间序列、原始负载/温度与样件追踪。
4. 双终点捕获及失效常闭的弹簧/轴销/受载回缩/强制断电试验；两电池电气隔离含逆灌、热插拔电弧、短路及三类单点 PCB 旁路试验；USB 实际速率/通道的 TDR、S 参数、眼图/BER、EMI/ESD 数据。
5. 原始未重编码文件、型号批次与修订号、文件 SHA256、可通过独立可信渠道核验的签署身份和许可文件，以及固定 A 世界锚点/B 局部锚点和同一组有序材料站位的跨四姿态原始记录。

已知当前 R40 动态 FPC 代理在 193/193 位置与研究壳体发生正体积干涉；我们不会未经允许修改厂商原生禁布区来“修好”它。请确认适用装配基准和可供设计审阅的受控数据交换流程。IEC 62715-6-42:2026 仅用作展平力测量依据，不等于寿命合格证明。

## 接收和决策边界

13 类资料逐项独立计数；`0/13` 是当前真实状态。公开目录、网页、合成签名、内部 3D 代理、研究级 unittest 不是 OEM 原件。收件后先以 R68/R70 分离原件/信任/回执的只读流程进行真实性、版权授权、修订与锚点校核；再开展 FPC/OLED/机械/电源/USB 实物验收。**没有原始样品与独立专业签核，继续禁止制造放行。**
