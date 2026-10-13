# RAZR SLIDE：OLED 原厂与替代模组公开检索 R4

本轮新增取得并按字节校验两份官方 PDF，共 12 页；独立于 R2 已查的 503 页资料。
另实际打开并目视复核一份新的 22 页天马候选资料，发现其与销售页面的模块范围不匹配，
因此没有把它转成已批准图纸。原始 PDF、网页和页面图像留在仓库外；这里保存自有事实、
提取器、来源索引、下载失败与实际机器回执。没有发送咨询、接受 NDA、注册或下单。

| 新证据 | 核实内容 | 对工程的实际约束 |
| --- | --- | --- |
| Motorola 环境报告，April 2025，10 页 | p7 确认 EU 的 Replace Base、US 的 iFixit / MobileSentrix 自修合作；p9 的显示相对功耗比较使用 500 nit 条件 | 找到原厂承认的资料和备件渠道。13% 相对改善没有给出 OLED 的绝对额定电流，不能替代电源设计输入。 |
| EPREL 2250774 官方 fiche，2 页 | 模型 XT2551-6；p1 整机电池额定 4540 mAh，p2 指向 Replace Base 修理资料。实际下载 PDF 元数据生成于 2026-07-03 | 4540 额定值与项目 4700 mAh 总目标及旧 BOM 数值分别保留；不改写项目目标，不外推为新电池资格。 |
| CSOT 自发布公告，2025-07-10 | 内外屏由 CSOT 独供，内屏宣传有 50 µm UTG、6.96 英寸、1224×2992、LTPO 和无偏光片技术 | 50 µm 是玻璃层宣传数据，不能替代整个 OLED / 触控 / 胶层 / 支撑材料厚度及中性面。软件 697 和宣传 6.96 没有构成受控模组料号。 |
| Panox 新候选 TA067FM01 的 PDF，22 页 | 文件内部是 TA067FVMK01-08，2022-10-12 Ver1.0；封面选择 Preliminary；p4 描述仅 cell，不含 D-IC / POL；p5–12 是 502 端子 FOG 表；p17 可靠性为 TBD | 网站的 40-pin 完整模块与其公开 PDF 的 cell 范围不一致。图纸标有 Core Trade Secrets，缺少授权与最终模块版次映射，不导入生产 ECAD / MCAD。 |
| Samsung Display 官方 CES2025 公告 | 展示 5.1→6.7 英寸 Slidable Flex Vertical | 明确有符合相近形态的真实厂商方向；本次打开的资料没有交付可订购模块型号、完整图或动态资格报告。 |

FCC 检索另发现 IHDT56AU1 的 2025-08 XT2551 内照于 2026-02-04 公开，Part3
附件号 8545621；同 FCC ID 还包含 2026 年 XT2655。原附件与三个公共镜像的正常
匿名 GET 均被拒绝，照片没有实际取得，模组印字保持未知，不能把同 ID 最新附件混成 donor。

范围明确：双舱同尺寸、单块约 7 英寸柔性 OLED、79.75 mm 上滑及 8.2 mm 就位、
A 舱优先较大电池仍固定。没有用 7.8 英寸替代，也没有添加另一块显示屏。
新增厂商证据没有给出本项目移弯区域、滚动半径、卷曲方向、平面存储张力、封边/COF 禁弯区、
绝对电源额定值及完整原厂模组/FPC 的最终图。有限公开检索不证明资料在全球不存在。
受控资料与真实项目资格仍需取得；`manufacturing_go=false`。

复核命令（原始输入在仓库外；字节哈希不匹配会失败）：

```bash
python3 engineering/oled-controlled-search-20261013-r4/extract_new_official_pdfs.py \
  --cache-root /workspace/scratch/522038b915ed/controlled-input-private-20261013-r4 \
  --report /tmp/razr-slide-oled-new-official-facts-r4.json
```

实际运行出口码 0，两个原始 PDF 与主机 `main` 下载的哈希一致。来源和页码见
`source-index.json`，查询边界及失败分类见 `bounded-search-findings.json`。
