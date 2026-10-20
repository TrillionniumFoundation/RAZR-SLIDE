# Phase 3：真实 donor 导入与内部路径研究

日期：2026-10-20 UTC。工作属于 PR36 的产品集成分支；main 和 PR35 的研究结论保持各自提交范围。

## 已实际完成

- 正式采集器新增 `--adb-server-port`，全部 ADB 调用显式使用本机 `-H 127.0.0.1 -P <port>`，记录二进制哈希、起止 transport ID 和原始命令输出。
- `3e6864ccea6c03a651dd220a0c1510c2ea22dfec` 的 102 项产品集成检查发生 13 个旧测试适配接口错误。`f4db100cb62c0ac492118bf605b0e9e7ac7cce32` 只修复该共用模拟接口，实际重跑同一 102 项全部通过。两份原始结果均保留；本轮没有重新执行全套 1303 项。
- 在 Pocket4 的上述正式提交执行真实只读采集，17 条命令全部完成；设备仍为 XT2551-3，serial SHA256 与此前 USB/ADB 观察一致，transport ID 37 和已有服务进程起止一致。
- 使用现有导入器执行第一次真实部分 donor 身份导入，保留 5 份原始观察、导入清单、两份提交一致的设计输入和独立校验结果。当前接口配置已采用实际型号与证据引用；其余 10 个身份字段仍为空，7 类实物角色标签与 12 条物理端子链路仍未完成。
- 两次已发布 head 的 Actions 原始查询结果已保存。`42679be` 和 `f4db100` 均有 12 个零步骤任务，以及各自直接取得的付款／额度提示；没有成功执行的托管测试报告。

## 证据入口

| 结果 | 文件 |
|---|---|
| 真实采集及部分身份的适用范围 | [hardware/DONOR_IMPORT.md](hardware/DONOR_IMPORT.md) |
| 不可变实机身份记录 | [record.json](../hardware/records/xt2551-3-20261020-f4db100-identity/record.json) |
| 实际导入命令与结果 | [actual-donor-import-execution.json](hardware/actual-donor-import-execution.json) |
| 原件完整性、兼容性与未完成端子核对 | [actual-donor-binding-verification.json](hardware/actual-donor-binding-verification.json) |
| 102 项首次错误及修复范围 | [selection-and-repair.json](validation/selection-and-repair.json) |
| 当前正式采集提交的托管查询原件 | [f4db100-run39359899335.json](actions/f4db100-run39359899335.json) |
| 前一发布提交的托管查询原件 | [42679be-run39355931047.json](actions/42679be-run39355931047.json) |
| 现有分件总装、侧带与薄件制造审阅 | [assembly-followup-review.md](assembly-followup-review.md) |
| 固定单 U 族内部性独立必要条件 | [ep3-constraint-review.md](ep3-constraint-review.md) |
| 下一批需取得的具体实物输入 | [NEXT_PHYSICAL_INPUTS.md](NEXT_PHYSICAL_INPUTS.md) |

## 本轮路径研究

EP3 的配置、完整端接原生构造和三态检查入口已实现，7 项纯算术检查通过。参见 [EP3_ROUTING.md](EP3_ROUTING.md)。本源码提交阶段的原生执行尚未完成；三态结果另行归档后再更新本节。

旧 EP2 的原生失败不因新增候选而改变；新候选的夹持、紧固件长度、板端层位和材料长度都必须分别记录。项目参考尺寸、解析必要条件、原生实体运算、材料来源和实物制造属于不同证据。

## 验收状态

本轮已经取得真实软件身份和正式原件导入。没有取得实物主板／COF／电芯尺寸，没有制造或操作新的完整滑盖样机，也没有验证改装后的显示、触控、供电和运动中 USB 连续性。PR35 未增加 FE/QP 重算；材料、实际载荷和完整缓存身份仍缺失。

`candidate_go`、`fixture_fabrication_go`、`manufacturing_go`、`physical_phone_verified` 均保持 false。具体原因与剩余输入见各结果，不能用单项软件检查或研究 CAD 输出代替整机验收。
