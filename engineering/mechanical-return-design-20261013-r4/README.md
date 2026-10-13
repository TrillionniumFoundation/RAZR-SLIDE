# RAZR SLIDE R4 — 基于厂商规格的独立盖紧固接口与回位弹簧约束

`manufacturing_go=false`，`fixture_fabrication_go=false`。本目录只派生 R3 研究台架，不是手机安装总成或合格制造图。两舱同尺寸、单块约 7 英寸柔性 OLED、B 上滑 79.75 mm 后法向就位 8.2 mm、A 优先大电池与系统合计 4700 mAh 目标均未改动。

## 实际查到的厂商资料

[NBK SNZS-M1-2](https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SNZS-M/SNZS-M1/SNZS-M1-2/) 的公开原厂表给出 M1×2、螺距 0.25 mm、头径 1.8 mm、头高 0.45 mm、SUSXM7 材料以及最大拧紧扭矩 0.02 N·m。该最大值不是本设计装配目标、预紧力或手机安全力限值。公差、指定螺纹等级、批次与可供货资格仍未知。此处螺钉 CAD 是自行构造的名义包络，没有冒称厂商原始 STEP。

[Lee Spring 2023 官方目录](https://www.leespring.com/sites/default/files/2023-03/lee-spring-catalog-us.pdf) 的 PDF 第 14 页（印刷页 12）给出 CBM010A 03 E：外径 0.81 mm、建议容纳孔 1.00 mm、自由长 3.00 mm、刚度 0.330 N/mm、实心高 1.194 mm；[厂商工程公差](https://www.leespring.com/engineering-notes-and-tolerances) 给出对应外径段 ±0.05 mm、刚度 ±10%、实心高上限 +5%。已对该原始 PDF 的表头、合并行与 N/mm 列作实际渲染视觉核验；未把 kg/mm 或 lb/in 当 N/mm。2019 与 2023 两份原始文件各自 SHA 及下载回执保留，原始厂商 PDF/网页快照在 Git 外。

## CAD 增量与边界

每侧两件 CAP 各增加两个独立圆形承台、连接到原 ROOT 的螺钉座、名义 M1 螺纹包络孔和盖通孔，并放置对应的 4 个螺钉头/杆包络实体。CAP 厚 0.30 mm、盖孔径 1.10 mm、座半径 0.70 mm、耳半径 1.00 mm、提议名义螺纹啮合长 1.70 mm 全部是研究尺寸。杆以名义大径包络建模；没有把一个光孔称为经过制造验证的螺纹，也没有证明拧紧力、拉脱强度或振动防松。

最初 x=-1.65 mm 紧凑座在 q=0 静态位置没有撞料；实际撤钥 q=1.15 mm 的 STOW 双侧有 ROOT/KEY 等碰撞，OPEN 在该位置清空，结果分别保留。第一轮 x=-2.35 mm 布置仍在 STOW 撤钥 q=0.70…1.40 mm 与第二层 KEY 连接片相撞，共 16 个真实失败配对。最终只把螺钉中心移到 x=-2.60 mm，使耳和螺钉头退出连接片的 x 区域；两个 q 中心仍为 -1.15 与 qleaf-0.10 mm。没有裁掉碰撞或把原 ROOT 当 OEM 可随意去料。

本增量使名义螺钉头在所试直线抬盖方向提供实体阻挡；两螺钉同时移除时的抬盖路径仍是保留反例。斜转、螺纹滑牙、头部破裂、预紧不足、共同 ROOT 失效及共用 KEY/cam 破裂仍未闭合。独立盖和螺钉数量不能证明独立失效域。

## 回位与有限力回缩没有伪造选型

R3 的 STOP 未抬起时顶部 r=1.80 mm，抬起 1.20 mm 后顶部 r=3.00 mm，现有盖下表面 r=3.02 mm。直接顶置直压弹簧的可用长因而从 1.22 mm 缩到 0.02 mm。CBM010A 03 E 的实心高名义 1.194 mm、上限 1.2537 mm；为容纳 1.20 mm 行程，低位轴向腔至少需 2.394/2.4537 mm，尚未计预压、导向与制造余量。因此这个有真实厂商数据的候选不能直接塞进现有盖腔。没有把“停止体放在零位”算成已安装回位簧，没有把不匹配的 stock spring 标为已选料。

薄 0.20 mm pin、0.32 mm slot 与 0.06 mm 径向自由度仍缺受控加工/GD&T、销料号、曲线及供应商能力证明。Lee 弹簧的公差不会被移植给 pin 或 cam。指定 OLED/FPC/BM28 的允许空程和受力没有受控证据，实际摩擦、断簧、断销、共同钥匙损坏与有限力回缩阈值仍为 `null`。回位簧的 catalog k 不能替代整机安全力上限。

## 实际执行

`initial-build-receipt.json` 与 `rejected-cap-withdraw-layout/` 保存首轮 620 位置、32,144 配对及 16 个真实干涉导致的 native 1，配套 8 个失败版本 STEP 均保留。`delta-receipt.json` 是最终几何参数修复的实际重算回执；source delta 只允许 x 中心值、诊断取样 q 和对应元数据改变。最初无缓存扫描实际退出 130，中断原因及源码/日志保存于 `rejected-redundant-static-scan/`。最终缓存的 hash 只用于选桶，必须两个保留参与体均通过真实 OCP `isSame`（包含 Location）才复用；未用 Python id、bbox 或相同体积当几何身份。执行期间 R3 所有受保护文件字节须保持不变。

`independent/verify_fastened_step.py` 不导入 builder，递归检查每个 STEP 的完整 payload，拒绝 free surface/wire/edge/vertex 与空 Compound，再独立按真实实体包络识别部件。新增盖、座、螺钉与实际导入运动实体的路径检查，实物资格与制造结论分开保存。`rejected-negative-control-assertion/` 另保存几何已无交叠但误要求 OPEN 在 STOW 取样座位置也应出现反例导致的 native 1。修正诊断器的端位期望没有改动实体，未把 OPEN 的真实清空结果重写成碰撞。最终数量、原生退出码与 SHA 以完整回执为准。

原始公开资料请求已实际查询；咨询、NDA、订单与采购提交数均为零。公开标称数据不能代替受控批次图纸、手机实际安装与完整 PCB，更不能代替捕获、回缩、双电池、USB 或 OLED 的实物资格。

## 最终冻结回执

最终 delta 实际原生退出 0：620 个原网格位置、32,144 个新增/修改配对，3,540 个真实 OCC common，其余为已验证实体的 AABB 零材料交叠证明及受控静态身份复用；8 个 STEP 重导出，新增体意外交叠 0，R3 文件字节不变。75.13 秒只是该 Cloud 执行耗时。

独立实际 STEP checker 原生退出 0，错误输出为空：8 份完整 STEP 共 188 个有效正体积 Solid、16 个静态两侧行、92 个退爪与 68 个正常撤钥位置，3,092 次真实 OCC common，新增体意外交叠 0，全部 11 个输入文件字节不变。8 个盖在所试 0.10 mm 直线抬起下均与已装名义螺钉头交叠；对应两螺钉移除后 8 个抬盖位置都清空。这只是几何留置及拆除反例，不是夹紧、斜转、强度或松脱实物资格。

R4 的 X230 同输入复核没有启动，不能把既有 R3 的双机结果写成 R4 已通过。原生 source/report/输入 SHA 与状态见 `delta-native-result.json`、`independent/native-result.json` 和 `final-state.json`。`final_manifest.json` 冻结本目录全部交付字节并排除 `__pycache__`。
