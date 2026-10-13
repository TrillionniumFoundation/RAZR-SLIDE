# RAZR SLIDE 历史资料精确归档

本目录保存原资料的可逆字节表示，按 Library 文件身份和版本保留全部 728 项候选资料。相同字节块复用 SHA-256 对象；没有重新生成、修补或替换历史文件。

- 原始总量：3,552,594,718 字节；678 个不同的整文件 SHA-256。
- ZIP：121 个原条目，117 个不同内容；顶层与嵌套 ZIP 已逐内容读完并通过 CRC。
- 精确归档：20,270 个对象，1,006,089,117 字节；每个对象最多 1 MiB。
- 728 项原资料均已按顺序重建，整文件 SHA-256 和长度与下载原件一致。
- 690 项具有项目／版本名称；38 项通用名概念图、图表或相邻辅助资料保留为待确认归属候选。候选图不能作为工程证据。
- 原文件名、Library ID、版本号、长度、SHA-256、对象顺序均保存在 `manifest.json`；157 份 Markdown 可直接阅读于 `../docs/records/`。

## 浏览、复核和恢复

从仓库根目录运行（只依赖 Python 标准库）：

```sh
python3 archive/restore.py --list
python3 archive/restore.py --verify
python3 archive/restore.py --restore RAZR_SLIDE_R44_FPC_full_verified_20261013.zip --destination recovered
```

`--restore` 也接受精确 Library ID。恢复后的路径沿用原 Library 文件名；每个对象与整文件都会重新核验 SHA-256。`build_exact.py` 是本次生成工具，原输入清单和下载目录由执行者明确提供。

## 身份分叉与保留失败

同编号不意味着同一工程分支。所有不同字节的 R31/R39/R40/R41 版本分别保留；R50 和 R52 的三份导出各自保留原身份并共享完全相同的内容对象。`package_readme_manifest_coverage.json` 索引每个 ZIP 的主文档、证据清单与嵌套包身份，不能按编号大小替代工程分支比较。

78 条外部 SHA sidecar 声明中，76 条能匹配本次原件。以下两条历史声明未匹配任何原资料：

| 原声明文件 | 声明的 ZIP SHA-256 |
|---|---|
| `RAZR_SLIDE_R40_verified_engineering_package_20261011.sha256` | `1565b97bc4bc42fe24438be9c69b0ea7cf855bc9c5f1cb0e6f935a05fa9fc3dd` |
| `RAZR_SLIDE_R41_verified_engineering_package_20261011.sha256` | `980876aa266376bcea8220488702a2c5781b59cdc9c7589b6babd9bd0db132e8` |

原 ZIP、原 sidecar 和不一致结论均保留；不修改 sidecar 来制造一致。详见 `sidecar_sha256_validation.json`。下载时出现的三项截断已定向重试恢复，首次归档工具错误也已修复，原失败日志和最终收据位于 `receipts/`。

## 供应商材料与放行边界

按五个已确认 Hirose 原始 STEP／来源 ZIP／许可说明的 SHA-256 递归扫描，未在这些既有资料中发现受限制原件。连接架构复核确认 BM28 命名几何由项目源码生成独立矩形包络，没有发现需额外排除的供应商派生 3D 文件。限制指纹和排除台账位于 `exclusions.json`；本轮排除数为 0。独立下载的供应商原始 CAD 不属于本次可提交归档。

归档完整性、软件断言和 CAD CRC 都不构成真实机械、电气或 OLED 资格。所有历史结论按原状态保存，整机始终保持 `manufacturing_go=false`。
