# RAZR SLIDE：指定 OEM 路线的真实输入恢复 R3

新增取得的是 Motorola 官方公开软件源，不是重复 R2 的 503 页资料，也不是另选
DM/DFR 替代模组。12 份文件已按官方 Git blob SHA1 核对全部字节；本地提取真实退出码 0。
原始源码和供应商网页留在仓库外，仓库保留地址、pinned commit、哈希、提取器和审计结果。

已将原机主屏软件路线具体到 CSOT / NT37707、NT37707A / 697 / 1224×2992 / DSC command mode，
触控 overlay 为 Goodix GT9916P、SPI 最大频率配置 15 MHz；USB overlay 为 high-speed/eUSB2。
八个 697 配置文件中，LEAP selector 直接包含六个，另含 667/1080×2640 主屏配置。
六个 697 include 不是全部主屏选择，也没有证明任何一个实际安装。没有实体 donor 的 panel ID 或主板身份
回执，因此没有选择其中任何一个，也没有把文件名当作可订购生产模组料号。

四 lane、DSC 1.1、10 bpc、8 bpp、612×16 slice 是源文件配置值。
软件里的 67×164 整数尺寸不提供完整 touch/DDIC/COF/封边/FPC 的外形与公差。
主屏 1.8 V / 1.20–1.25 V / 3.0 V 和 load 字段是 regulator vote；不是厂家供电额定值、
实际电流、连接器针脚图或完整 PCB 网表。原机充电 overlay 的电池 ID map 与 R2 维修
BOM 的服务料号不同，尚不能解释为相同 pack 或软件错误；需真实 pack/板号及版本映射。

本轮沿实际厂家公开入口继续查下载。Goodix 文档中心的匿名 GET 对
`GT9916P`、`GT9916`、`9916` 均真实返回 `total=0`。
同接口正向对照 `GR551x` 返回 36 份文档，证明本次接口能返回公开文档；对照不属于目标器件。
页面存在通用 NDA 下载处理入口，未调用。Novatek 的公开 DDIC 产品入口未交付
NT37707/NT37707A 的 package/COF/电源完整资料。CSOT 的手机及折叠类页面、精确关键字
查询未交付本路线的受控模块图。十次 GitHub 路径/分支查询失败及 CSOT 对 `6.97`
搜索词的服务器验证拒绝均保留；后者没有误记成成功的零结果搜索。
这是限定公开入口的实际结果，不代表厂家内部或所有供应商没有这些资料。

未取得原生机械装配 CAD、完整生产 ECAD/FPC artwork、实际模组的动态卷曲许可或实物资格。
没有发送邮件、提交咨询、下单、接受 NDA、登录或改动手机。下一份最少输入请求已具体到
CSOT 697 / NT37707(A) / Goodix GT9916P，而非泛泛询问“柔性 OLED”。
两舱同尺寸、单约 7 英寸 OLED、B 上滑 79.75 mm 后法向就位 8.2 mm、A 优先大电池不变。
整机 4700 mAh 为工程目标，A 舱优先大电池，尚未转为已验证电池选型或供应能力。
`manufacturing_go=false`。

## 复核入口

```bash
python3 engineering/controlled-input-recovery-20261013-r3/extract_oem_software_inputs.py \
  --cache-root /workspace/scratch/522038b915ed/controlled-input-private-20261013-r3 \
  --report /tmp/razr-slide-r3-oem-software-inputs.json
```

源文件路径和 immutable URL 见 `official-oem-source-index.json`。缺失的真实厂商资料及
请求范围见 `targeted-controlled-input-request.json`；联系状态为 `READY_NOT_SENT`。

## 官方来源

- [Motorola kernel-display-devicetree pinned tree](https://github.com/MotorolaMobilityLLC/kernel-display-devicetree/tree/c9e8fc8fa4c31efb50e9f88e51ef255edfe0fb5b)
- [Motorola kernel-devicetree pinned tree](https://github.com/MotorolaMobilityLLC/kernel-devicetree/tree/2d6028662042733e2924ba2509c8714323754a3d)
- [Goodix 文档中心](https://www.goodix.com/en/document/center)
- [Goodix 触控产品入口](https://www.goodix.com/en/product/touch/touch_screen_controller)
- [Novatek Display Driver IC](https://www.novatek.com.tw/en-global/Product/product/Index/product2)
- [CSOT AMOLED 折叠类产品入口](https://www.tclcsot.com/products/325.html)
