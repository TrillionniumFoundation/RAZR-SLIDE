# R5：官方原文接收与同样件现场交付接口

本轮实际取得一份以前未完整取得的官方原文：联想直接提供的 XT2551-3 快速入门指南，内部手册编号 `SSC8E69755-B`。收到 `2,237,155` 字节，SHA256 为 `8b0ad4c1bc676dc549de7f9bcd969d77b30603373fe8a151ca06eae6427464c9`。原文件完整读回、PDF 解析、文字抽取和第 2 页视觉读回一致；文件有 2 页。它解决了该快速指南的完整接收缺口，但它是消费级型号资料，不能补同一样件的 228 项工程事实。

原始接收记录见 `R5_OFFICIAL_PDF_RECEPTION.json`，适用性见 `R5_OFFICIAL_QUICK_GUIDE_APPLICABILITY.json`。原网址为 <https://www.lenovocare.com.cn/ideaservice/535125b81e2f46eabffa9c1568443961.pdf>。公开交付只保留文件身份、接收与适用性记录，不内嵌第三方整份 PDF、抽取全文或渲染图片。PDF 元数据、原目录日期和详情页日期各自保留，未将它们擅自归并成一个发布日期。

## 实际受理结果

新程序 `receive_evidence_r5.py` 对原文件做只读字节接收，然后调用**原字节未改的** R3 V2 受理验证器。它不会从文件名、型号网页或图片推断尺寸、引脚、材料、阈值或功能。

| 已执行输入 | 收到的文件 | 原 228 项结构上有值且引用成立 | review_ready_structure | G3／G4／G5 |
|---|---:|---:|---|---|
| 原空输入 | 0 | 0 | false | 全部 false |
| 新官方指南，声明为 model_literature | 1 | 0 | false | 全部 false |

15 个新入口边界对照实际完成：正常合成字节接收、错误 SHA、符号链接、父路径逃逸、绝对路径、缺少类别／采集者／时区、跨样件、重复证据 ID、重复原文件路径、JSON 重复键／非有限数，以及 CLI 重复选项／缩写。全部得到预期结果。对照是同作者的明确合成输入；它们不验证文件内容真实性，不是实物试验，也没有重新执行或改写原 R3 的 37 个历史控制。

## 现场交付包

`R5_FIELD_COLLECTION_PLAN.json` 逐项保留原合同全部 **228 个 requirement ID、描述和适用范围**，给出负责人、交付内容和验收条件，所有未测值仍是 null。原合同、原空 packet 和原 V2 验证器分别逐字节复制，并由 `R5_ORIGINAL_INPUT_IDENTITIES.json` 绑定；原 10／7／12 要求未改。

| 交付阶段 | 原件与事实 | 完成时应能核对的内容 |
|---|---|---|
| D0：样件身份 | 10 个身份字段与全机／标签原照片、原采集日志 | 同一 specimen_id；地区、主板／显示／触控 revision、原机 panel ID、两电池标签和 USB 角色／版本速率逐项有来源 |
| D1：实际原件 | 主板、display、touch、COF、pack_A、pack_B、USB_port_board，共 7 类、77 项事实 | 原 PN／revision／可见 lot 或 serial、未编辑照片、真实外包与禁入尺寸、不确定度、pin 1、装拆／尾出／配合方向、原机功能基线 |
| D2：OEM 互连 | 12 个接口，共 120 项事实，并交逐端子表 | 两端连接器 PN／revision／端子号、信号与方向、回流／屏蔽、同样件映射来源、原协议与基线、有来源的电气界限 |
| D3：选定器件与工艺 | OLED/COF、FPC、连接器、结构材料工艺，共 21 项 | 实际 PN／revision、完整叠层与公差、动态弯曲条件、材料属性与工艺／lot、连接器配合及电气额定来源 |

12 个接口是 `MAIN_DISPLAY`、`MAIN_TOUCH`、`A_PROTECTED_PACK`、`B_PROTECTED_PACK`、`A_CHARGE`、`B_CHARGE`、`USB_DATA_CROSS`、`USB_POWER`、`CAMERAS`、`RF_ANTENNA`、`AUDIO_SENSORS` 和 `MOTION_STATE`。每个接口都要逐端子来源，不能用一张系列框图代替。

所有尺寸记录至少绑定原始值、单位、不确定度及其类型、坐标系与基准、仪器 ID、校准原件和有效期。保留原始照片／日志；裁剪标注作为另一个派生件。实际集成部件可以共享一个真实 part_id，但各角色的事实要求仍分别保留。

当前结构的 FE／公差与 G3–G5 合同同时放在交付计划中，继续保留原来的空阈值和缺来源字段。当前 K1／K3 需要自己的几何、材料、载荷、接触、制造公差和版本绑定；旧数值合格不能自动移用。后续实物链仍按同候选、同 specimen、同 assembly_revision 的 G3 → G4 → G5 顺序执行，前一级真实通过必须先结束。缺测、失败、维修和换件各记独立事件；维修或换件改变装配 revision 后不能继承前一装配的通过链。

## 使用机器接口

1. 保存实际收到的原文件。复制 `R3_EMPTY_INTAKE_PACKET.json` 为工作 packet，填写已实测事实与对应来源；未取得的字段保持 null。
2. 在 `R5_EMPTY_EVIDENCE_INVENTORY.json` 的 `files` 数组加入已收到的文件元数据，使用相对原件目录路径、明确的类别、采集时间／人／方法／定位。`row_template` 只是格式提示，不能当证据。
3. 执行下面的只读接收。指定一个尚不存在的输出目录；输入原件保持不变。

```bash
python3 -B receive_evidence_r5.py \
  --inventory received-inventory.json \
  --packet received-packet.json \
  --evidence-root received-originals \
  --contract intake/R3_SAME_SPECIMEN_INTAKE_CONTRACT.json \
  --validator intake/verify_intake_r3_v2.py \
  --output-dir reception-001
```

输出是字节接收回执、保留原事实及事件的 packet，以及原 V2 结构受理结果。`review_ready_structure` 仅表示这些原字段、引用和声明的时序结构齐备；工具始终保持 `original_evidence_authenticity_verified=false` 和三个物理 pass 为 false。合成声明即使字节真实存在，也不会因此成为真实器件或实物通过证据。

## 原提交与其他来源的当前边界

本轮增加检查 R4 发布之后的新建／修改 uploaded 文件、原 bundle 的限定检索、GitHub 的 1 个 draft release（64 个资产元数据）和全部 210 个 Actions run 元数据。未找到原 a11 Git bundle 或以该 SHA 为 head 的 run；这不是对所有可能备份位置不存在的证明。原 a11 精确发布仍需要真正包含该对象的 bundle／原 Git 对象，既有推送授权继续有效。

iFixit 的公开 L2 页面实际返回 HTML，下载锚点指向登录；没有绕过登录。沿 [Motorola 官方维修资料入口](https://en-us.support.motorola.com/app/right-to-repair)到其分销商手册目录的普通 HTTP 读取返回 403，已保留该失败并停止。已公开的 NA 手册／BOM 仍不能直接证明 XT2551-3 同样件的元件或端子。

这一轮新增同样件测量为 0、合格绑定为 0、真实 G3／G4／G5 通过为 0，未发出任何设备命令、邮件或消息。完整组合用户指南、对应样件的维修／原厂工程资料和所有真实物理结果仍待原件交付。
