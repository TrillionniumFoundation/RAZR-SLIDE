# R13：官方维修资料与器件身份的追加核对

本轮新增 **Motorola UK 官方分发路径、三份 EU/系列维修文档的真实索引地址，以及两个官方伙伴的显示总成身份线索**。完整 OEM PDF 实际取得数仍为 **0**；没有新增同样件原件、测量、选定 PN/revision 绑定或实物资格。

## 可核验的进展

[Motorola UK 官方入口](https://en-gb.support.motorola.com/app/right-to-repair)直接将维修文档链接到 [ReplaceBase 文档目录](https://www.replacebase.co.uk/motorola-guide)，并列出 Spares Nordics、MobiParts 等配件伙伴。新定位到以下制造商文档地址。版本按实际可见的文件名记录，未将搜索索引当作完整文件读回。

| 文档 | 已见标识 | 本次访问结论 |
| --- | --- | --- |
| [L2 系列维修手册](https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/XT2551-X_Moto_razr_60_ultra_razr_ultra_Service_and_Repair_Manual_V1.0.pdf) | V1.0；可见主板列表包含 -1/-2/-5/-6 | 定位到索引；未取得完整字节，未证明 -3 适用 |
| [EU L3 手册](https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/XT2551-X_Moto_razr_60_ultra_razr_ultra_Level_3_Service_Manual_for_EU_V1.0.pdf) | EU，V1.0 | 定位到索引；未取得完整字节或准确 variant 范围 |
| [EU 服务 BOM](https://www.replacebase.co.uk/media/wysiwyg/pdf/Razr-60-Ultra/Phone_Global_SBOM_Moto_razr_60_ultra_razr_ultra_EU_V1.9.pdf) | EU，V1.9 | 实际 GET 为 405、2531-byte Human Verification HTML，非 PDF |

EU BOM 响应的 SHA256 为 `2f086c4e79aa0382057aa19d7f953571738958d42d6bdfbc8b9250722e3a8054`。识别人机验证后停止该站自动下载，没有处理 CAPTCHA、修改访问方式或使用登录凭据。旧 iFixit L3 和 BOM 页面也明确要求账户才能读完整文档；本轮未重试旧 CDN 来规避该要求。原 R12 的三次 HTML 结果保持不变。

## 器件线索及适用性

[Spares 的 Scarab 总成](https://www.spares.se/product/motorola-razr-60-ultra-5g-lcd-display-original-scarab)明示 **XT2551-6 / SKU 5D68C30085**；[MobiParts 的同色服务总成](https://www.mobiparts.ro/spare-parts-motorola/lcd-display-module-for-motorola-razr-60-ultra-sub-inner-pantone-scarab)列出 **5D68C30088、5D68C29813**。这些不同编号没有被解释为等价、可替换或适用于历史 XT2551-3。服务总成名称也不提供裸 OLED、COF 或改造 FPC 的受控叠层。

旧 NA L3 的公开预览提供少量连接器服务编号及针数/间距；具体值及来源放在 `PART_IDENTITY_LEADS.json`。它们只供后续比对标签，未提供同样件的配对插头、端子方向、pinmap 或受控材料/工艺规格。LS Mtron 官方页面已取得 HTML 身份，但未取得明确的 GB35R 原厂受控 PDF；第三方目录数据未作为技术输入采纳。

## 未闭合项目与交接

完整的来源链、文档版本可见范围、实际响应校验分别保存在 `PRIMARY_SOURCE_INDEX.json`、`OEM_SOURCE_APPLICABILITY.json` 和 `ACCESS_READBACK.json`。本目录只含自写源码、少量必要事实、来源链接、HTTP 元数据和 SHA；完整网页/第三方文件正文不在公开清单内。

同样件的 10 个身份字段、7 个实体角色、12 个真实接口仍需原件。原 228 项要求没有因本轮公开资料检索而取得任何合格新增绑定。OLED/COF/FPC、连接器与材料工艺规格仍为 unknown，G3/G4/G5 与制造放行均为 false。确切缺口和允许的下一步在 `CURRENT_INPUT_DELTA.json`，没有代替用户联系供应商、下单、登录或执行设备命令。
