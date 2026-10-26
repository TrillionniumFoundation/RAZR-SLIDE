# Donor collector：显式 ADB server 端口修正

日期：2026-10-20。此批基于父任务提供的阶段二提交 `42679bebe1aa5af00bc3221cee2fa9d11391b811` 的源码副本实施；本地测试不代表新代码已提交，也不代表已在 Pocket4 执行。

## 问题与行为

此前入口只有 `--adb`，会默认访问 5037；已授权 donor 实际在专用 ADB server 5061 上，因此另一端口的空 inventory 不能推出 donor 不存在。

新增 `--adb-server-port`，默认 5037，接受 1–65535。所有 inventory、品牌判定、属性读取和结束 inventory 都经过同一入口，实际参数前缀固定为：

```text
<adb executable> -H 127.0.0.1 -P <selected port>
```

同时固定主机的原因是：ADB 即使给了 `-P`，在没有 `-H` 时仍可能使用 `ANDROID_ADB_SERVER_ADDRESS`。依据为 [AOSP commandline.cpp](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/client/commandline.cpp) 的主机/端口解析逻辑。

采集器不发 `start-server`、`kill-server`、`root`、设备写入或端口扫描命令。这里不承诺 ADB 客户端自身绝不自动启动服务；实物执行使用已经运行且匹配的 ADB server，前后 PID/监听端口由本轮原生证据另行核验。

## 新增的可复核信息

顶层 `adb_transport` 记录选定主机、端口、全局参数、请求的执行文件、可解析的文件路径及 SHA-256；文件无法解析/读取时不编造摘要。

每条 `command_records` 新增 `adb_global_args`。有效调用可由执行文件、全局参数、原有 `args` 组合复核。原 `args` 保留 v2 逻辑参数形式，serial 继续替换为 SHA-256；成功、非零返回和超时的 stdout/stderr 文本均保留。超时可能返回 bytes，转为 UTF-8 文本时不可解码字节用替代字符表示；未声称保存二进制逐字节原件。

起止 inventory 保留 transport ID，并增加 `device_inventory_after`。同一 serial 起止 ID 不同时，返回 `transport_changed_during_capture`、`software_identity_complete=false`，已有读数和命令记录保留。若旧 ADB inventory 没有 ID，一致性值保持 null，仍按原有 serial 规则记录软件身份；它不是“已验证同一 transport”的结论。

## 兼容与证据边界

报告继续使用 `razr-donor-readback-v2`。现有 `product_interfaces.readback_trace_consistent` 已在新成功报告上通过回归；该旧检查器验证逻辑 serial、属性及最后 inventory，不新增对 transport 元数据的独立强制验证。旧报告缺少新字段时，不回填或推断它曾使用 5037。

原有设计绑定未改：保留 Git commit、两份设计 JSON 的工作区和提交内 SHA、接口合同摘要以及采集前后一致性。CLI 返回 0 本身仍只代表软件身份完整且前后设计身份未变；不能单凭退出码推出绑定完整或输入等于提交。原生验收另核 `design_binding.complete`、`inputs_match_commit`、提交身份和 collector SHA。

物理板号、屏幕/COF、电芯标签、针脚和尺寸继续未知；物理完成与手机功能验证 flags 维持 false。此批没有加入 sysfs 模块，也没有把 aggregate 软件容量/profile 当成电芯规格。起止 transport ID 比较不证明期间 USB 或供电连续，更不证明整机运动中连续性。

## 验证与依赖

本地 Python 3.12.14，Git 可用，ADB 不在 PATH；没有连接或访问实物设备。原有 11 项测试加 6 项回归，共 **17/17 通过**，unittest 用时 **0.437 秒**，返回码 0。`--help` 返回 0，并显示新参数。

新增回归覆盖全部实际 subprocess 的 5061/loopback 前缀、默认 5037、起止 transport 变化、超时部分输出及脱敏、CLI 端口转交和非法端口不回退；成功路径还验证旧 v2 导入器接受新记录。测试中的设备/二进制和输出均为明确的 SYNTHETIC fixture。

```bash
python -m unittest discover -s integration/product-study-tests -p test_donor_readback.py -v
```

无新增第三方 Python 包。正式采集最小依赖为 Python、Git、指定的现有 ADB，以及同一 checkout 中的：

- `tools/read_donor.py`
- `integration/product_interfaces.py`
- `design/product_geometry.json`
- `design/product_interfaces.json`

从包含本次功能提交的真实 sparse checkout 根目录执行，输出使用尚不存在的新文件：

```bash
python3 tools/read_donor.py \
  --adb /home/alex/.local/opt/razr-adb-37/adb \
  --adb-server-port 5061 \
  --repo-root . \
  --output /tmp/razr-donor-port-followup-20261020.json
```

单台已授权 Motorola 可自动选择；多台时需明确 serial。没有实际 specimen 标签时不填占位 specimen。Pocket4 上的新入口、实际 server PID/port 稳定性、真实 Git/input 绑定和设备属性由父任务原生执行确认；本文件不预写成功。

## 交付身份

仅修改以下两份授权源码；共享 JSON、manifest 和旧证据均未修改。

| 文件 | SHA-256 |
|---|---|
| tools/read_donor.py | b2dada86400ec43ba1ace3a02b657fcf6790744656a4bfb8f322b4bcd091b351 |
| integration/product-study-tests/test_donor_readback.py | 98f64eab251ca6e8d13549edd6fb97ea01c6f707f4d4c41aa2dc65e47a9bd54d |


## 实际正式采集与导入

端口修复及测试适配已在 f4db100cb62c0ac492118bf605b0e9e7ac7cce32 发布。2026-10-20 的实际 17 条只读采集、部分身份导入和保留的失败见 [DONOR_IMPORT.md](hardware/DONOR_IMPORT.md) 及 [第三阶段总览](README.md)。当前仅确认型号，物理平台和全部端子尚未绑定。
