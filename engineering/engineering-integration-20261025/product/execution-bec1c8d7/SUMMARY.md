# EP5 电气与 G3–G5 执行包

## 当前可引用结果

本包当前候选为 **bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb**（C2）。`current-c2/native-ecad/report.json` 是在该提交上实际运行完整 `tools/verify_ep5_ecad_native.py` 得到的回执：`passed=true`，入口退出码 0，执行前后 HEAD 一致，5 个受控源文件逐项与提交字节一致且执行中不变，原始 PCB / project 字节不变。

原生读取确认 52 个端子、130 段铜线和 2 个封装。完整构建身份为 `9.0.9-9.0.9~ubuntu24.04.1`，独立发布版本为 `9.0.9`。CLI 使用 `--severity-all --all-track-errors --exit-code-violations`；JSON 保留 error / warning / exclusion，`violations` 与 `unconnected_items` 均为 0，退出码 0。`schematic_parity` 空数组只表示本次未请求原理图一致性，不代表 ERC 已执行。

`current-c2/qualification/` 是同一 C2 的新 G3-v2 / G4 / G5 模板与输入现况。`current-c2/qualification-generation-receipt.json` 对 131 个绑定源文件和原生输入逐项核对提交字节，全部匹配、0 missing。**G4 与 G5 都是 unknown**；没有新物理观察、获批器件选型或制造放行。G3 的实际 BOM、材料、工艺、图纸及固件观察仍需现场原始证据。

## 历史结果的边界

`history/c1-qualification-r1/` 和对应生成回执只绑定 C1 **8fa8ae2bae5de8808ad8259e04434bdd18d47541**，是历史草案，不能作为当前 C2 资格。`toolchain-and-preflights/ep5-native-preflight-r1` 至 `r4` 是冻结 C2 前的工作区预执行；这些结果没有完整 candidate / source HEAD 闭合，不能替代 C2 完整入口。r1 保留旧读取器在空封装库上猜测 writer 失败的原始日志；r2 保留旧毫米枚举在 KiCad 9 不存在的原始日志；r3 / r4 保留直接原生读回与 DRC。r4 新增独立 release 字段以保持完整 build 身份和 CLI release 严格一致。

历史 `verify_native_mini.py` 原字节未改。两版 migration 和 unified diff 记录其 SHA256、当前继任读取器 SHA256，以及显式 native writer、毫米枚举和 release 字段等全部差异；仅归一化所列变化后，AST 与前驱相同。所有 stderr 均原样保留，包括多次 `LoadBoard` 的 wx duplicate-image-handler debug 行，没有通过过滤 stderr 或剔除 DRC 项产生零结果。

## 原生运行环境与恢复

KiCad 9.0.9 来自官方页面链接的 9.0 releases PPA，noble amd64 包版本为 `9.0.9~ubuntu24.04.1`，deb SHA256 为 `b7e6d33867631dc44385067b703b4c39eadede2037a260790b19495fe17e43f0`。本包保留 PPA 公钥、signed InRelease、Packages 及校验回执；公钥指纹为 `FDA854F61C4D0D9572BB95E5245D5502FAD7A805`。Ubuntu 基础依赖使用本机既有官方 APT 缓存的版本 / URL / SHA；已过期的 protobuf、libgit2、libssh2 下载身份改由新的 Ubuntu signed noble-updates/main 索引确认，保留其 Release 和索引 URL / SHA。两类来源明确记录，没有把缓存元数据描述为新取证的完整签名链。

`toolchain-and-preflights/environment-receipt.json` 列出全部 34 个包及实际运行二进制 SHA；`runtime-environment.json` 记录隔离运行所需的动态库、Python 与 KiCad stock/config 路径。安装通过 `dpkg-deb --extract` 在 `/tmp` 内完成，没有全局安装。`.deb` 与安装树二进制不装入此包；全部 `.deb` 原件仍保留在 `/tmp/razr-kicad9-isolated` 及其 `dependencies` 子目录，可按清单逐 SHA 核对后重新解包，或按清单 URL 下载并核 SHA。

为给后续几何计算恢复磁盘余量，唯一被回收的是 `/tmp/razr-kicad9-isolated/root` 安装树。回收前确认无运行进程映射该树，并重新校验 34 个包、全部已有小证据与 C2 wrapper 原始文件；回收释放约 360 MB。`toolchain-and-preflights/install-tree-reclamation.json` 记录精确字节及前后余量。签名资料、包、全部历史失败 / 成功回执均未删除。

## 验证包完整性

外部 `manifest.json` 给出 `execution.tar.gz` 的 SHA256、字节数，以及每一个 tar 文件成员的 SHA256 与长度。压缩包不含符号链接、绝对路径或 `..` 路径。归档成员中的回执保持原始内容；执行命令保留当时的绝对工作目录。当前 native 结论只覆盖 188 mm 自有连续性研究图稿的原生读取与报告 DRC，不覆盖 OEM 端子、USB 阻抗、供电额定、动态 FPC、供应商叠层、实机通电动作或寿命。
