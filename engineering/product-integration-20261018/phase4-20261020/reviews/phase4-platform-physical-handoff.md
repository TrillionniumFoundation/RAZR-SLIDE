# Phase 4 平台与首批实物交接

**当前可用结论：已正式连接并记录同一台 XT2551-3；完整实物平台、新壳容量和功能样机尚未冻结。** 本页复核既有证据与 N=`9a8307fe4bd4163b53515698fb12cfc0a8cc27e7` 的设计范围，没有新增拆机、称重、容量或操作试验。以下路径均相对仓库根目录。

## 已有输入与剩余缺口

正式采集已绑定 `f4db100`、同一 specimen、设计输入及原始 stdout/stderr，不能再把旧默认 ADB 端口空记录写成“没有 donor”。当前正式身份采用 **model=XT2551-3**；boot SKU、软件屏幕尺寸及 main/flip 节点是已有软件观察。[1]

| 剩余项 | 必须补齐的内容 |
|---|---|
| **10 个身份字段** | region、主板修订、runtime panel ID、屏幕料号/修订、触控修订、A/B 电池标签、USB roles/version-rate。软件信息与实物标签分别记录。 |
| **7 类模块角色** | mainboard、display、touch、COF、pack_A、pack_B、USB_port_board。`part_inventory` 仍空；同一屏幕总成可以覆盖多角色，但须有照片/标签和相互关联。 |
| **12 条接口端子表** | `design/product_interfaces.json` 的 12 条 `actual_pinmap` 均未绑定；这是接口数，不是针数。板端、针号/方向、线束另一端及测量来源仍缺，已有软件枚举不能代填。 |

同型号中国 OEM 指南 **SSC8E69755-B p2** 已给出 **4700 mAh 典型、4540 mAh 额定**，无需再次把这两个值列为未知。但它未证明本台两块电芯的料号、外形、极耳、保护件或新壳容量。软件设计值 3430+1140=4570 mAh，与 OEM 额定差 30 mAh，原因未确认；aggregate profile 的 `3520MAH` 不是主电芯标签。NA XT2551-1/-2 的 3520/1180 服务件仅为区域候选，不能填入当前 A/B 实物字段。[1][2]

## 现在能输出什么，哪些结构尚不能放行

从 `design/product_geometry.json` 可导出**尺寸分配替身**：A 电池 64×40×2.75 mm（7040 mm³）；B 电芯与电子板各 12×68×4.4 mm（3590.4 mm³）；相机 10×10×6.1 mm。质量均未知，尚非质量替身，也未包括真实极耳/保护/膨胀/RF/散热。B 两条 12 mm 带已被分配，不能再当作端接空位；宽 12 mm 端接若两侧各留 .2 mm，需要 12.4 mm。[3]

现有 STEP 与分件顺序可用于尺寸替身、工艺报价、环/套/接头试片设计；**不能直接下成完整功能机构加工包**。当前 EP4 固定端接仍是 M2 ∅2 穿 ∅2.2、M1 ∅1 穿承台 ∅1.1／PCB ∅1.4，缺另一端螺纹、螺母或已定义铆接保持。新增保持件与工具空间必须入 CAD。薄件已有明确难点：底盖厚 .10、母套壁 .20、保持唇高 .10、内杆 ∅.40、KEY 薄臂 .25×.30 mm；颈 ∅.80／槽 .85 仅 .05 mm 总间隙，必须容纳加工偏差、毛刺和接合变形。材料、工艺能力和保持力仍无实测依据。[4]

## 最小实物取证包与依赖顺序

1. **同一 specimen 的模块包。** 保留已采集身份；补模块正反面/标签/连接器 pin-1 方向照片、总成关联，量外形与最高元件、COF/出线/极耳、质量和坐标基准。每项绑定 `part_id`、时间、原始附件 SHA、量具/校准和不确定度；OEM 规格同时记录适用 SKU/版本及“实物已匹配/未匹配”。
2. **实物几何与工艺先进入设计。** 用量测替换占位，重核同一版本三态和中间行程；确定电芯及原保护组件完整包络、膨胀依据后再评估 4700 目标。先为环/套/薄臂/螺钉接头选择材料、连接截面和公差，做接头首件尺寸、滑动阻力与保持力记录，再做整套无电件。尺寸替身可先行，质量和载荷不能猜。
3. **端子映射后才接真实电气。** 原保护、充电、温度/身份回线及原配屏触链保持完整；A 保护/充电共用线束引用同一证据，不另建裸电芯旁路。未知针脚保持未知；项目 `C01–C26` 仅是隔离连续性样片编号。先验证样片通断与端接保持，再按已确认的原机链路逐级上电，记录显示/触控/供电/USB 的原始结果。
4. **完整开合实测回写。** 同一图纸/CAD/端接版本记录操作力、松手保持、左右偏差、反程和连续性时间序列，再据实测载荷做限定结构重算。附原始 CSV、时间基准、仪器配置与输入 SHA；现有两 JSON 的导入绑定不能替代完整 CAD/EP4 源版本身份。

## 原件与源码出处

[1] `engineering/product-integration-20261018/phase3-20261020/hardware/DONOR_IMPORT.md`；原字节在 `engineering/product-integration-20261018/hardware/records/xt2551-3-20261020-f4db100-identity/`；软件模组原值在 `engineering/product-integration-20261018/phase2-20261019/hardware/pocket4-20261020/module-readback.json`。

[2] [联想中国原始指南 p2](https://www.lenovocare.com.cn/ideaservice/535125b81e2f46eabffa9c1568443961.pdf)；区域适用性和公开索引范围的本地复核件：`/workspace/scratch/5547df349f5a/razr_phase2_tools/oem-source-map.md` 与同名 JSON。

[3] `design/product_geometry.json`、`design/product_interfaces.json`、`integration/product_assembly.py`。矩形容量预算不是电芯实物尺寸或容量证明。

[4] `integration/product_routing_ep4.py:ep4_local_parts`；`integration/cam_coupling.py:templates`；`engineering/product-integration-20261018/phase3-20261020/assembly-followup-review.md` §6；`engineering/product-integration-20261018/physical-test-followon-20261019/captured_follower_assembly.py:source_geometry`。此前几何结果按原版本保留；本页不预写任何新样件、上电或制造通过。
