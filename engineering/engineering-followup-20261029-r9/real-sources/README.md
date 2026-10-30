# R9：实际器件资料的取得范围与适用性

本轮实际检索取得了制造商维修资料的分发入口、维修手册及 BOM 的公开预览。
没有收到新的同样件原始照片、标签、测量或功能记录，也没有取得完整维修 PDF。
`R9_OEM_SOURCE_APPLICABILITY.json` 保留来源、版本、适用型号、实际获取限制和未绑定状态。

## 新找到的资料

| 资料 | 实际取得内容 | 能支持的结论 | 仍不能支持的结论 |
| --- | --- | --- | --- |
| [Motorola 官方维修入口](https://en-us.support.motorola.com/app/right-to-repair) | 官方分发渠道说明及合作方入口 | 可定位维修手册、零件和电路资料的正式渠道 | 具体样件、板卡版本或改装接线的确认 |
| [L2 维修资料预览](https://www.ifixit.com/Document/IxsugLCmhuNaPpYx/XT2551-X_%28Moto_razr_60_ultra_%26_razr_ultra%29_Service_and_Repair_Manual_V1.0r.pdf) | 版本 1.0r；公开索引含显示、FPC、PCB 和电池拆装章节 | 存在可进一步取得的工程资料线索 | 完整原件已取得、柔性互连完整叠层或允许弯曲半径已知 |
| [北美 L3 维修资料预览](https://nl.ifixit.com/Document/6RFZBdGVwWbhvVhh/XT2551-X_Moto-razr-60-ultra-razr-ultra_Level-3-Service-Manual-for-NA_V1.0r.pdf) | 版本 1.0r；公开预览含连接器服务标识及图纸目录 | 可供未来原标签核对的服务标识 | 历史 XT2551-3 的端子映射、电气额定值或配对连接器已确定 |
| [美国维修 BOM 预览](https://zh.ifixit.com/Document/ZKsjbwghQxtwgNBa/Phone_Global_SBOM_Moto-razr-60-ultra-razr-ultra_V1.9.pdf) | 版本 1.9；明确列出 XT2551-1、XT2551-2 | 北美型号的维修件候选标识 | 与现有 XT2551-3 样件、实际板卡 revision 或所选 OLED/COF 相同 |
| [联想中国支持索引](https://m.lenovocare.com.cn/ProductDownloadList.aspx?productid=1047) | XT2551-3 快速指南、用户指南和应用列表入口 | 对应型号的用户资料可定位 | 受控叠层、COF 引出结构或完整连接器 pinmap 已取得 |

公开下载入口重定向到登录的情况保留为未取得完整原件；直接获取目录返回 403
的尝试也保留原结果。未使用另一身份或越过访问限制。地区 BOM 不能依据同系列
名称自动绑定到历史样件。

## 原 10 / 7 / 12 合同保持不变

原合同是
[`R3_SAME_SPECIMEN_INTAKE_CONTRACT.json`](../../engineering-followup-20261028-r5/real-sources/intake/R3_SAME_SPECIMEN_INTAKE_CONTRACT.json)。
228 是待绑定事实的数量，不是要求 228 份独立文件；同一真实原件可以支持多个事实，
集成在同一器件上的角色也可以共用同一真实 part ID。

| 类别 | 原合同要求 |
| --- | --- |
| 10 项身份 | 地区、主板 revision、运行时 panel ID、显示模组料号和 revision、触控 revision、A/B 两个电池标签、USB 角色和版本/速率 |
| 7 个器件角色 | 主板、显示、触控、COF、A 电池、B 电池、USB 接口板；共 77 个器件字段 |
| 12 个实际接口 | MAIN_DISPLAY、MAIN_TOUCH、A_PROTECTED_PACK、B_PROTECTED_PACK、A_CHARGE、B_CHARGE、USB_DATA_CROSS、USB_POWER、CAMERAS、RF_ANTENNA、AUDIO_SENSORS、MOTION_STATE；共 120 个接口字段 |
| 选定件及 revision | 21 项；必须对应最终实际选用的 OLED/COF/FPC、连接器和其他材料/工艺版本 |

其中 207 项要求同一 specimen，另外 21 项要求实际选定的 PN/revision。本轮新绑定为 0。
每项测量仍需数值、单位、不确定度及其定义、坐标系和基准、仪器身份、校准证据及
有效期。原照片、标签、方向、端子来源和原机功能必须可追溯；型号网页不构成替代。

## 当前 FE 和 G3–G5 的具体阻塞

原合同仍有 154 项材料分配需要真实参数、13 个载荷工况需要来源。载荷覆盖左右
解锁、伸出、落座、实际保持/支撑后的无手扶 OPEN、拆除支撑/保持件、反向退出、
左右回锁、携带/跌落、紧固预载及温度/电池膨胀。现有空间占位体仍需换成实物几何。

当前 K1/K3 修改需要自己的网格和源绑定，并验证力与力矩平衡、能量一致性、完整
控制域接触、网格与载荷增量收敛、关联公差最坏情况和返回/回锁。原 N15 数值资格
不能替代这些物理输入和当前结构的重新分析。

既有显示参考件重检中的已知问题也继续保留：在该固定路径族下，原记录的长度缺口
为 22.088803 mm、相对 67 mm 试片的宽度超出为 4.94 mm。该记录并未选定实物模组，
也没有排除所有可能路径族；新找到的维修资料不能消去这项已知的不适配。
见 [`OLED_SOURCE_RECHECK.json`](../../engineering-integration-20261025/product/OLED_SOURCE_RECHECK.json)。

完整电气合同尚缺与所选 revision 对应的端子映射、配对连接器、实际互连叠层和
工艺来源。G3–G5 的数值限值、采样、校准、时间同步和计划版本仍需实际来源绑定。
原有 17 个运动阶段、原机电池/充电模式、原始时序与周期记录要求继续适用。

已存在的 E3 KiCad 原生检查继续有效于原研究布线范围：52 个端子、130 条走线、
26 个研究通道，已执行全严重度 DRC；其五个源码与 S4 的逐字节绑定已独立核查。
本轮没有重跑这项历史检查，它不授予 OEM 接线、ERC、电源/SI、完成叠层或动态
FPC 的资格。见 [`INDEPENDENT_REVIEW.json`](../../engineering-integration-20261026/ecad/e3-native/INDEPENDENT_REVIEW.json)。

真实验收仍要求同候选、同样件、同装配 revision，依次完成 G3 → G4 → G5。
本轮没有执行实物验收，没有新增任何一级 pass。缺测、真实失败、维修和换件保留为
不同事件；变化后的装配 revision 不能继承先前通过状态。
