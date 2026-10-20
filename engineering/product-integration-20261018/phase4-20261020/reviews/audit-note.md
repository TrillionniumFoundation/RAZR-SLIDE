# XT2551-3 平台、电池与第一批件：90b09f5 精炼复核

仅复核既有原件、固定版本源码与报告。本轮没有新实物观察、native CAD 重算或加工完成；真实 donor 记录仍是部分身份。最小证据修复另附补丁，不改真实记录。

## 已经有的输入不用重采

同一 serial SHA 的 XT2551-3 已在明确的 `127.0.0.1:5061` 正式采集，并绑定 f4db100 的 Git/设计输入。型号、连接和原始 stdout/stderr 已归档；`wm size=1224×2992`、双 DSI、内 goodix_ts/外 fts_ts、main/flip 电量节点也已取得。它们是软件枚举，不能替代屏幕/COF、板修订、连接器或电芯物理标签。[正式导入](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/engineering/product-integration-20261018/phase3-20261020/hardware/DONOR_IMPORT.md)

## 4700 mAh 尚不能冻结为滑盖布局容量的量化原因

| 依据 | 数值与限制 |
|---|---|
| 中国 OEM 手册 SSC8E69755-B p2，适用 XT2551-3 | 整机典型 4700、额定 4540 mAh；出处已明确，未给两电芯尺寸、极耳或新布局拓扑 |
| 本台软件原值 | main 3430000、flip 1140000 µAh，合计 4570 mAh，比 OEM 额定多 30；没有充放电容量实测。3520MAH 字符串来自 aggregate profile，并非 main 电芯标签 |
| NA SBOM v1.9，适用 XT2551-1/-2 | base SB18E50882 的容量描述 3520、flip SB18E50881 为 1180 mAh；尚未与本台部件匹配，不能写进实际 A/B 电芯字段 |
| 当前矩形分配 | A 64×40×2.75=7040 mm³；B 12×68×4.4=3590.4 mm³。区域 3520/1180 情景分别要求 500.0/328.654 mAh/cm³，尚未计极耳、保护和膨胀，也无标称电压；这是必要预算，不是可行性证明 |

现有 OEM 软件来源又有 main `SB18E07971`、flip `SB18D58447` 的 ID map，与 NA 服务件号不同；应分列软件映射、区域候选、实物标签，保留版本/SKU/来源及未匹配状态，不能相互代填。

已有 EP3 native 报告显示 A 载板侵入电池分配 **18 mm³**。同源几何交叠盒为 X=−6…6、Y=38…44、Z=4.50…4.75。若固定电池 Ymax=78，仅缩短矩形分配至 Ymin=44.2 来让出项目 0.2 mm 间隙，A 空间降至 **5948.8 mm³，减少 15.5%**。所以不能只从体积预算扣 18 mm³；应改载板/位置或重排矩形电芯，再验证全场景。

B 两条 12 mm 侧带已经分别给主板与电芯。当前 EP3 B 端接约 12×35×3.9 mm，高度已不同于旧 EP2；若想放进其中一条 12 mm 带，按两侧各 0.2 间隙要 12.4 mm，至少欠 0.4 mm，并须先迁移原占位。

## 第一批件可以具体准备到哪里

| 可立即给出的加工输入 | 当前不能当作什么 |
|---|---|
| 按上述尺寸出 A/B 电池、B 电子板占位块尺寸图；相机占位为 10×10×6.1 mm。选定普通模型材料和尺寸工艺后可做空间替身 | 真件外形、质量替身或电芯装入/容量证明；质量仍无依据 |
| 从现有 split/captured STEP 出装入顺序与接头局部图、询工艺能力；做具体环/套/端盖接头试片 | 可承载、可复锁的整套无电机构；当前接缝只是相触面，没有已定义的连接截面 |
| EP3 PCB/夹爪轮廓及孔位可作为试片图纸输入 | 已可采购装配的完整夹紧端接：M2 ∅2 穿 ∅2.2、M1 ∅1 穿承台 ∅1.1/PCB ∅1.4，均缺另一端螺纹、螺母或铆接保持；新增保持件必须进 CAD 重算 |

具体薄件风险已有尺寸：端盖厚 0.10 mm、母套壁 0.20 mm、唇高 0.10 mm、内杆 ∅0.40 mm；颈 ∅0.80 对槽 0.85 仅余 0.05 mm 总间隙。必须将加工偏差、毛刺和连接变形共同纳入这 0.05 mm 预算。没有材料/接头/工艺能力时，现有 STL 不能直接升级为功能件加工放行包。

## 还缺的标签与端子输入，以及可修代码

真实记录的 part_inventory 为空；缺的是主板修订、屏/触控/COF 标签或同一总成关联、A/B 电芯保护组件标签与尺寸、USB 板和目标连接器实体标记/方向/逐针。NA J550/SCA8C71314、J500/SCA8E75511 等只能留在区域候选表，不能填实际针脚。无需重新索要已经取得的 model、boot SKU 和软件容量。

本轮已复现并修复一个具体代码缺口：OEM 文档单独即可被算作 `physical_parts_with_original_labels`，甚至让完整合成 donor 通过 `actual_donor_selected` 验证。最小修复要求物理行至少有同 specimen 的实际标签/测量锚点，仍允许 OEM 规格及联合引用。原 16+新 6 共 **22 项通过**，仅局部 Python 合成测试；实际 XT2551-3 部分导入保持可用且冻结 false。

后续端子 schema 还有两项明确范围：允许归档同 specimen 的局部已测端子/原机 baseline，不先要求所有无关角色齐全；为有原始证据的 NC/预留/屏蔽端子增加 disposition，避免现有“所有 pin 必须 source→sink”迫使伪造连线。未知端子继续阻塞完整绑定。本轮未扩展该 schema。

## 可复核出处

- [中国 OEM 手册 p2](https://www.lenovocare.com.cn/ideaservice/535125b81e2f46eabffa9c1568443961.pdf)；[NA SBOM v1.9 公开预览](https://de.ifixit.com/Document/ZKsjbwghQxtwgNBa/Phone_Global_SBOM_Moto-razr-60-ultra-razr-ultra_V1.9.pdf)。没有取受限全文，也没有把 NA 适用性升级到 XT2551-3。
- [原始模块读取](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/engineering/product-integration-20261018/phase2-20261019/hardware/pocket4-20261020/module-readback.json)；[软件输入抽取及 SHA](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/engineering/controlled-input-recovery-20261013-r3/extracted-oem-software-inputs.json)。
- [分配几何](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/design/product_geometry.json)；[EP3 完整端接](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/integration/product_routing_ep3.py)；[已有原生交叠](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/engineering/product-integration-20261018/phase3-20261020/native-summary.json)。
- [既有制造/接头尺寸追溯](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/engineering/product-integration-20261018/phase3-20261020/assembly-followup-review.md)；[当前端子与身份验证](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/integration/product_interfaces.py)；[物理导入器](https://github.com/TrillionniumFoundation/RAZR-SLIDE/blob/90b09f5/engineering/product-integration-20261018/hardware/import_hardware_evidence.py)。
