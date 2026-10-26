# XT2551-3：OEM 接口候选映射

2026-10-20。来源、URL、页码、检索词及访问范围见同名 JSON；本说明不构成实物针脚冻结。

## 中国型号依据

S_CN：联想官方将 XT2551-3 对应为 moto razr 60 Ultra；快速指南 SSC8E69755-B 第 2 页给出整机典型 4700 mAh、额定 4540 mAh。它未给出两电芯分配、尺寸、料号或拓扑。设备软件容量保留原值，不能替代上述定义。NFG_ATL_RS35NVT_3520MAH 来自 aggregate battery 的软件 profile；不是 main_battery 实物标签，不能据此冻结 RS35。

## 区域维修候选

S_BOM_NA 明列 XT2551-1（美加）及 XT2551-2（AT&T）；EU 原稿只作为区域候选。以下均未证明适配此台 XT2551-3。

| 链路 | 可核候选 |
|---|---|
| 主屏＋触控 | L3 p27 公开索引：连接器在 Main FPC，直接接屏总成；连接器位号、料号未知。p51/56 区分主屏 DSI0 与外屏 DSI1。 |
| 外屏 | SBOM：5D68C29811；板端连接器未知。运行时 DSI-1/2 不能直接等同原理图编号。 |
| flip 电池 | SBOM：SB18E50881，1180 mAh；L3 Table 1：J550／SCA8C71314，6 pin、0.35 mm；p73 索引归于 BATT_FLIP。逐针未核。 |
| base 电池 | SBOM：SB18E50882，3520 mAh；L2 p160 索引有 Base Battery BTB 和 Main FPC BTB，未取得其位号。 |
| USB 子板 | SBOM：5P68C29822；L3 Table 1：J500／SCA8E75511，24 pin Type-C，在子板。 |
| 相机连接器 | Table 1：J3150／SCA8C44152，40 pin；J3100、J3200／SCA8D57591，24 pin。p35/68 给出相机 REFDES 区间，尚未逐针核对。 |
| RF | SBOM：黑线 SC18E51407、白线 SC18E51408；上下天线板 5P68C29824／29825。Table 1：J9000／SCA8D38328；两端对应未知。 |
| 跨铰链 FPC | OEM 确有 Main FPC；两端位号、料号、逐针和动态弯曲条件未知。SM88E51128 是其 BTB 支架，不能当作 FPC 料号。 |

L3 前摄图页标 32M，SBOM 标 50M；另一后摄在 SBOM 写 Tele、L3 写 UW，必须保留差异。J6300 功能仍未知。

NA L3 仅直接读取公开预览 Table 1；p27/35/51/56/68/73 等为公开搜索索引摘录，未取得受登录限制的全文或核实原图针脚。EU 直接取回失败，未当作全文回读。主板版本、裸 OLED/COF、真件尺寸与端子仍待实物证据，全部制造、上电与几何完成结论保持 false。

