# 自主干回路探测与新鲜度硬件 R4

新增可编辑硬件原理图、自己的引脚库及真实 KiCad 网表，共 **69组件、219端子**。自主 Schmitt RC 振荡器经独立缓冲/47k限流驱动专用干回路；47k签名电阻要求安装于B端。TLV3202 检查高相0.4–0.6倍电源及低相约0.099倍电源以下，两只SN74LVC1G74在相反边沿采样。TLV803EA29DBZ直接监视本地台架3.3V，非外部PGOOD旗标。

TPS3431 的 EN/SET1 硬接电源，CWD接10k选择170–230ms超时；WDO撤销时异步清两相样本及 service pending/armed。WDO自动释放不能恢复旧许可。人工RESET仅置pending；实际TPS WDI节点在1k串联电阻之后由独立反相器/另一个DFF观察，只有**新的实际WDI下降沿**能置armed。人工RESET、上游振荡时钟或旧高电平不能单独制造许可。最终输出同时要求两相有效、PGOOD/WDO健康与armed。

实际首版模型检出WDO自动释放与WDI卡高/低并存时的周期性重开。第二版64组件虽有故障锁存，独立审阅继续检出人工RESET可绕过持续WDI故障；其真实200针原生KiCad回执、完整源包、输出包及反例保留。当前69组件修复上述具体失效，不修改失败断言来取得通过。

最终 pocket4 **KiCad9.0.8** 原生网表、SVG、全严重级别ERC各退出0，219针逐一匹配、7个输入前后SHA一致、零豁免；Cloud与pocket4各27项行为模型断言退出0。`native_process_receipts.json`保存实际job身份、完整stdout/native退出码及逐块SHA传输；最终353,928字节输出包SHA为`4209ae23fff1b1065243cb65dfc19738a59caa9c6bcc535424152f6a5fa277e7`。原生SVG已用Inkscape实际渲染并复核纸面与门控区域；启动库警告保留，渲染退出0。

七份TI官方数据手册实际HTTP200、PDF头校验、逐份SHA及pdftotext退出0。原始厂家PDF在台架原始资料目录，仓库只保存URL、版本、自己的参数摘录及下载回执。参考链接与关键条件在`primary_sources.json`；每个引脚和元件值在`terminal_netlist.json`与可编辑源中可追溯。

这仍是**干回路研究台架电路**，没有实际装配或完整手机PCB，未连接真实电池、USB或主负回线。主负回线断开但干回路仍完整、近端等值签名桥、上窗比较器卡高、WDO本身卡高、末级DC许可线卡高以及刚采样后立即故障的反例均保留，27项通过不关闭这些实物/架构阻塞。

元件角点计算64组，条件窗口余量约0.223/0.272/0.244V，干回路短路电流条件上界74.47µA、1.1nF电容能量6.60nJ；它们是研究计算。TPS WDI漏电上限未列于手册，不能据100k下拉就宣布完整VOH负载保证；比较器最大迟滞、振荡周期、元件漏电、实际线缆寄生、采样setup/hold、低于supervisor POR的输出及真实回路故障能量尚未获控制或测量。**230ms不是整机安全能量阈值。**

`manufacturing_go=false`、`phone_complete_PCB=false`、`physical_qualification=false`。实际主回线诊断隔离/OFF漏电及焊死测试、独立末级切断、完整PCB与实物资格仍需继续完成。
