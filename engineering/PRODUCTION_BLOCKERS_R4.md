# RAZR SLIDE R4：原厂资料落实与实际修复

产品约束不变：同尺寸双舱、单块约7英寸OLED，B上移79.75mm后法向就位8.2mm，A优先大电池。4700mAh为整机未验证目标。厂家输入请求以production-inputs-20261013-r4/targeted-controlled-input-request.json为准；它纠正了R3错误的A容量字段，历史未删除。

| 本轮实改 | 真实执行与材料 | 尚缺的生产依据 |
|---|---|---|
| OLED准确资料 | 新取得Motorola环境报告与EPREL fiche，12页，真实SHA与提取退出0；实际读新天马22页规格，其Preliminary裸屏/502FOG/可靠性TBD不能充当完整模块 | 选定完整OLED模块的同版MCAD、FPC/COF、电气额定、动态移弯和平储许可仍未取得 |
| FPC原料与叠层 | 实取14个原厂输入，9PDF共52页；Hirose文件与历史同SHA。新增Würth静态UseA/ED铜、XML未用层计厚和公差冲突；找到Qnity AC181200RY/AC182500RY裸RA基材。Cloud/X230各13测试与实际筛查退出0，报告逐字节相同 | 裸基材不是成品FPC；项目UseB叠层、六路artwork、实际夹具/铜站位/弯扭与USB/电源资格未交付 |
| 自主干回路探测 | 新69组件/219针原理图含本地电压监测、双相采样、TPS3431超时与实际WDI节点授予边沿。修复自动重开及人工复位绕过；Cloud/pocket4各27，native9全严重级别ERC0且逐针一致；7TI PDF真实下载 | dry-loop不证明实际主负回线；近端等值桥、比较器/末级卡高及采样后故障仍保留。完整PCB、隔离、电源负载与实测时序/故障能量缺失 |
| 首切断真实PCB | 15件/30针/47段铜，pocket4 ERC0，main fresh DRC0/0/0；原生7层Gerber、钻孔、7SMD坐标和板体STEP。保留首轮37违规和缺ILM断网负控；8TI PDF真实校验 | 29×24mm单U_A1隔离台架参考板：缺完整手机供电/其它切断/充电/USB/负回线、完整器件MPN和DFM/实物资格。STEP只含板体，缺元件及via孔 |

四组数据目录分别为oled-controlled-search-20261013-r4、fpc-controlled-search-20261013-r4、proof-detector-design-20261013-r4、pcb-source-repair-20261013-r4。原厂原文留在工作树外；仓库收录原创设计、输入事实/版本/哈希与实际原生回执。

机械盖紧固已外移螺钉座并实际重算620位置、32,144配对、3,540次真实OCC，新增体干涉为0并导出8份STEP；原16处撤钥碰撞及错误诊断回执保留。增量、独立导入检查与失败布局在mechanical-return-design-20261013-r4，最终原生回执配套读取。NBK M1名义规格不能代替夹紧/拉脱/防松实测；Lee CBM010A03E的实际实心高度不容当前顶置空间，未选为回位簧。有限力阈值、回位、销/cam加工公差及完整手机安装仍未实物闭合。

`manufacturing_go=false`，`phone_complete_PCB=false`。公共原厂资料和研究台架导出不能替代捕获、限力回缩、双电池、USB与OLED实物资格；相应证据尚未取得。没有签NDA、发送厂商咨询或采购订单。
