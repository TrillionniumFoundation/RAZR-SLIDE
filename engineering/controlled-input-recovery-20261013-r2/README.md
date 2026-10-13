# RAZR SLIDE：真实输入恢复第二轮

已取得三份 Motorola/Lenovo 原厂维修 PDF，并完成解析与关键页视觉核对：
XT2551-X Level 2 共 283 页、Level 3 NA 共 87 页、美国服务 BOM V1.9 共 2 页。
官方 Motorola 支持页指向 iFixit，iFixit 的 Motorola Repair Hub 说明其官方维修合作。
文档字节身份、版次与页号见本目录的 JSON；原始 PDF、抽取文本及页面图片均位于仓库外，
未重新分发。公开可访问维修资料没有提供改造整机制造许可。

Cloud 对四份 Motorola 源 PDF 的字节/页数/身份检查真实退出码为 0。
qian-qi 独立从官方维修合作方下载了三份维修 PDF，与 Cloud 的 SHA 完全一致。
第四份官方 RED 文件的 qian 直接下载遇到 HTTP 403；整组下载真实退出码 1 保留。
随后将 Cloud 已核验的第四份源文件复制到用户机器的独立原厂资料目录，
四文件逐份 SHA、PDF 原生解析均通过，真实退出码 0；第四份不冒称独立下载。
资料保存在 `/home/qian-qi/Documents/Codex/RAZR_SLIDE_R66/vendor_motorola/native_docs_20261013-r2`，
没有原厂 PDF 或页面图片进入 Git。

这次补回了真实电池维修标识和静态装配线索。美国 BOM 的两块电池为
SB18E50881 / 1180 mAh 与 SB18E50882 / 3520 mAh；合计 4700 mAh 是原机标称值，
不能当作本项目已经达到的电池容量。主 FPC 在原机与主屏装配关联，并贴附两电池；
原机的金属 BTB 压架有四颗固定螺钉与指定扭矩，说明端点所需空间和工艺超出
连接器配合高度。相关值仅适用于 OEM 原件，不移植为研究盖板的加工或压紧参数。

原机维修表给出 24、40、6 针连接器与 USB 子板标识，但没有证明其与 BM28 配对。
美国 BOM 只列 XT2551-1/-2；英国官方文件可核对 XT2551-6。
本项目实际 donor 的后缀、地域及主板版次尚未冻结，不跨区域替换零件。
官方 APAC 产品页给出 USB 2.0，只提供对标接口描述，不是本项目全行程 USB 资格。

Level 3 PDF 包含充电、显示和 USB 维修示意，但第 52 页明确关键 PMIC/CPU 电路需另行取得。
现已发现资料中的真实工程线索；完整原生 ECAD、受控装配 CAD、FPC 叠层和端子图仍未取得。
这些资料不能由低分辨率图片反推公差、连接器厂家型号或所有电源引脚。

本轮还检索可实际标识的模块 SKU 与其原始资料；结果见 `oled-*` 文件。
供应商层面的尺寸/端子矛盾和动态使用许可缺口须先解决，不能静默更正再进入生产 PCB。
两份模块 PDF 在 Cloud 均成功取得并核验。qian-qi 的整组下载真实超时退出码 124；
事后只读盘点实际发现 DFR1262 PDF 字节与 Cloud 完全一致，另一份模块 PDF 与整组
下载收据都不存在。因此没有将这次超时记成两份模块的远端下载通过。

最少请求内容见 `minimal-controlled-input-requests.json`。
联系状态为 `READY_NOT_SENT`，没有发送邮件、提交咨询、购买样品或接受 NDA。
现有固定要求保持两舱同尺寸、单块约 7 英寸 OLED、79.75 mm 上滑后 8.2 mm 法向就位，
A 舱大电池优先；`manufacturing_go=false`。

## 原始来源

- [Motorola 官方支持与 iFixit 路径](https://en-us.support.motorola.com/app/product_support/p/12208/motorola_razr_ultra_-_2025)
- [iFixit Motorola Repair Hub](https://www.ifixit.com/motorola)
- [XT2551-X Level 2 原厂维修手册](https://documents.cdn.ifixit.com/IxsugLCmhuNaPpYx.pdf)
- [XT2551-X Level 3 NA 原厂维修手册](https://documents.cdn.ifixit.com/6RFZBdGVwWbhvVhh.pdf)
- [XT2551 美国服务 BOM V1.9](https://documents.cdn.ifixit.com/ZKsjbwghQxtwgNBa.pdf)
- [Motorola APAC 对标机 USB 描述](https://en-apac.support.motorola.com/app/answers/detail/a_id/187134/~/specifications---motorola-razr-60-ultra)
- [Motorola 英国 XT2551-6 / MC442 型号身份](https://en-gb.support.motorola.com/app/answers/detail/a_id/185662)

本目录是输入恢复与审计证据，不是整机制造包。
