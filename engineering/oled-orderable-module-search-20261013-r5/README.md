# RAZR SLIDE：可交付 OLED 模组入口与新资料 R5

新增真取得 TDO **TA066FHV01-V2049A** 的 18 页模组资料。Cloud 与主机 main 独立匿名下载
获得同一份 2,982,185 字节 PDF；SHA256 为
`f5fb7cbfb229bd72d4df8e7f784d0da4514c75b045e90a5de295a45bf413d247`。
两机均真正执行提取器，退出码 0，并解析到 40 个唯一编号针脚。原始厂商资料在仓库外。

| 新候选 | 查到的实际输入 | 不能据此放行的具体原因 |
| --- | --- | --- |
| TDO TA066FHV01-V2049A，6.67 英寸 | 2026-03-26 Rev1.0；p4 无触控、RM692E5、标称 1080×2400 而实际显示 1080×2240；p5–6 模组端接；p17 外形与 FPC 尺寸 | 封面选择 Pre-Spec，客户签认空白；3 个电流仍 TBD；无触控却保留 TP 针脚；绘图针脚列空白；官网厚度 0.291 与 PDF 0.231 mm 范围未解释。 |
| Hicenda HAM0667-T，6.67 英寸 | 实际打开 39 页 PDF，2023-09-15 Ver1.0；VTDR6130、FT3658U、40 针接口；p32–34 外形与部分层厚 | 客户接受/受控图章未完成，厂商网页型号和接口文案矛盾；p39 装配禁弯扭，没有滚动许可；原生下载被拒/超时，未伪造字节哈希。 |

TDO 的 p17 标注 FPC 长 112.39 mm，局部元件最大 1.01 / 0.95 mm；可用于候选研究中的
固定尾部和元件避让，但完整原生 MCAD 未交付、叠层与移弯区未明确，不能代替现有 OEM 的
COF/FPC 或成为生产图。其看似修正的针脚表也不能作为 R2 DMKDO06501DNA 的勘误：
没有厂商提供两个料号/版本的等效关系。厂家新文章中的 90° / R6.8 mm 是静态形状宣传，
不能转成 79.75 mm 行程的动态卷曲许可。公共订货入口显示零库存、10–11 周，
没有询价、下单或收样；网页状态记录于 2026-10-13。

本轮真实检查 Samsung、BOE、EDO、Visionox、USMicro 的官方入口，并从 Motorola 新官方
EU right-to-repair 页面跟随维修文档链接。Samsung 跟随链接实际显示的是 Electronics DS
供应商会员入口，不误记为 OLED 受控资料门户；Visionox 返回 JS 挑战，不当成空目录；
USMicro 仅实际看到 77 个产品的第一页 20 项；OEM 链接返回 405，没有宣称取得另一版 EU L3。
逐项来源与观察见 `source-index.json` / `bounded-search-findings.json`。

解析器的两种失败反例及 main 缺少 fitz 的真实失败均保留。最终改用已存在的 Poppler
`-bbox` 和 Python 标准库，按源 PDF 文字位置关联表格单元，Cloud/main 取得相同提取结果。
没有通过页面像素推算机械尺寸。复核入口（SHA 不匹配即失败）：

```bash
python3 engineering/oled-orderable-module-search-20261013-r5/extract_tdo_module_inputs.py \
  --pdf /workspace/scratch/522038b915ed/controlled-input-private-20261013-r5/tdo-ta066fhv01.pdf \
  --report /tmp/razr-slide-oled-r5-facts.json
```

原约束与总电量目标不变：两舱同尺寸，单块约 7 英寸柔性 OLED，B 上滑 79.75 mm 后法向
就位 8.2 mm，A 优先较大电池，4700 mAh 为整机总目标。本轮未取得真实动态 OLED 资格。
有限公开检索不是全球无资料的证明；受控资料/供应商回复与真实样件未到。
`manufacturing_go=false`。

