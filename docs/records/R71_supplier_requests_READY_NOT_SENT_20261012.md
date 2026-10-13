# R71 供应商资料征集与交接清单｜READY / NOT SENT

**本文件未发送。** 没有代表用户签 NDA、采购样品、上传商业秘密，也没有取得真实供应商 OEM 资料。只有 13/13 类资料与必要独立许可实际到位，才可重新计算真实整机 CAD。不得用公开网页、目录占位体或本地合成签名顶替 OEM 原件。

## 官方联系方式和状态

- Hirose BM28 Header：<https://www.hirose.com/en/product/p/CL0673-5024-0-53>。
- Hirose BM28 Receptacle：<https://www.hirose.com/en/product/p/CL0673-5025-0-53>。
- 官网明确列出两款器件的原生 STEP、2D、规格书下载入口；但通过授权计算机对 Header **公开下载链接进行实际 GET 得到 HTTP 403**，没有取得 ZIP 原始字节。本项目仅有官网公开规格，不得记为已交付厂商 CAD。
- Hirose 官方 Contact Us 链接跳转到客户登录页面，网站说明询证需先注册账号。**本轮没有注册或提交任何问询。**
- 目标约 7 英寸 OLED 的准确厂商、型号、许可/采购/对接人仍未确定；不得将演示展品的 R3/卷绕寿命替换为目标模组数据。

## 建议发送给 Hirose 的英文问询（需由已获授权的用户账号自行发送）

**Subject: RAZR SLIDE internal static termination – BM28 mating pair revision, original CAD/footprint & sample engineering request**

Hello Hirose Engineering,

We are evaluating BM28B0.6-24DP/2-0.35V(53), CL0673-5024-0-53, and BM28B0.6-24DS/2-0.35V(53), CL0673-5025-0-53, as **static low-cycle internal terminations** in an experimental dual-chamber sliding device. The connector pair itself must not mate/unmate during the intended 300,000 device-motion cycles.

Please provide a verified revision-controlled package with the **original STEP files** for both mating parts, original 2D tolerance drawings, recommended SMT land pattern, mating and assembly keep-outs (including solder fillets and manufacturing access), minimum standoff, strain relief requirements, mechanical retention, and the applicable per-contact current derating / 20 Gbps signal-channel assumptions. Please clarify whether data download access requires registration and which terms permit engineering integration of the original CAD.

We have not validated the actual USB channel, battery-main-supply current or the 300,000-cycle dynamic FPC. We need the appropriate sales/engineering contact for legally authorized samples, licensing and a secure transfer of original files. We can exchange our own controlled interface files only under an agreed confidentiality arrangement.

Thank you.

## 结构/OLED/FPC/试验机构中文问询

主题：双等尺寸功能舱/单约7英寸柔性 AMOLED 滑盖项目——同修订 OEM CAD、动态 FPC、OLED 与台架原始证据询证

您好：

拟在双方接受的保密与资料使用许可框架下获取**准确型号与修订号**的数据，不要求未经授权的第三方模型。产品定义为：A/B 两个同外形完整功能舱、B 从后下层纵向上滑约79.75mm并在终点法向就位8.2mm、单块约7英寸柔性 OLED（无外屏）、A 优先大电池。4700mAh 仅产品目标，当前没有容量认证。

请按同一装配接口修订和统一的 4 个有序非共面基准点提供：A/B 可合法修改的成品结构 CAD（含公差）、主板/摄像头/电芯/BMS/天线/热源禁布体积；OLED 的完整 COF/FPC/封边与贴合模块三维外包络、中性层/动态 R/残余形变/展平力/疲劳判据；FPC 原始叠层与动态线宽、双轴服务环出线方向、两端真实夹持 CAD、失效判据与同一实物样件的至少 30 万次循环位移/载流/连续电阻原始记录（如厂商建议其他寿命目标，请单独注明）；机械失效常闭、载体卡死回缩、极限负载/冲击；双电池电源逆灌/电弧/PCB 单点旁路；USB 目标速率的 S 参数、眼图/误码率与 EMI/ESD 证据。

交接包须保留**原始字节**，含型号、批次、修订、原始 SHA256、发件人可独立核实的身份信息、原始许可授权以及材料站位原始时间序列。R71 可以使用贵方接受的独立、可审计签署/验真方式来映射文件来源，不要求贵方必须采用我方自定义 Ed25519 格式；正式渠道和许可需双方确认。

## 收件/动作规则

1. 先核验官方对接人与许可范围；不假造签名、不上传未经授权的第三方 OEM CAD。
2. 每一份资料必须从隔离收件箱保留完整原始文件，外部独立登记信任密钥、准确角色、料号、修订与许可字节哈希；再以 R70/R71 只读检查。
3. R71 对来源做的**密码学与文件级检查不等于** OEM 法律身份、CAD 几何、疲劳或机械/电气资格。需要独立人工许可核实和 R65/R68 材料站位跨姿态动态证据。
4. 整体 `manufacturing_go=false`。未经用户批准，本稿不能代发、不能接受网站注册条款或 NDA。
